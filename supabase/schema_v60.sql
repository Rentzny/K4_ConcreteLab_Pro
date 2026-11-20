-- ConcreteLab Pro v6.0 / Migration from schema_v55.sql.
-- REQUIRED: run schema_v55.sql first (if fresh installation), then this migration.
-- Run in YOUR Supabase SQL Editor as project owner. Backup DB first.
-- Never commit passwords / secret keys. Do not enable raw table writes for anonymous users.
BEGIN;
SET LOCAL search_path TO public, extensions;

-- Older registered accounts are grandfathered ACTIVE ONCE ONLY when adding column.
-- New auth.users entries after this migration are PENDING by default.
DO $mig$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_schema='public' AND table_name='k4_profiles'
                   AND column_name='account_status') THEN
    ALTER TABLE public.k4_profiles ADD COLUMN account_status text NOT NULL DEFAULT 'pending'
       CHECK (account_status IN ('pending','active','suspended'));
    UPDATE public.k4_profiles SET account_status='active';
  END IF;
END $mig$;

CREATE TABLE IF NOT EXISTS public.k4_public_settings (
 feature_key text PRIMARY KEY,
 enabled boolean NOT NULL,
 updated_by uuid REFERENCES auth.users(id),
 updated_at timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT k4_public_setting_key CHECK (feature_key IN (
  'upload_csv','edit_csv','summary','statistics','quality','visuals','simulation',
  'comparison','audit','exports','archive','tracking','method','registration_enabled'))
);
-- Public flags are NOT credentials. Anonymous visitors need to read them; no public writes.
INSERT INTO public.k4_public_settings (feature_key,enabled)
SELECT f.key,TRUE FROM (VALUES
 ('upload_csv'),('edit_csv'),('summary'),('statistics'),('quality'),('visuals'),
 ('simulation'),('comparison'),('audit'),('exports'),('archive'),('tracking'),
 ('method'),('registration_enabled')
) AS f(key) ON CONFLICT (feature_key) DO NOTHING;
ALTER TABLE public.k4_public_settings ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.k4_public_settings FROM PUBLIC,anon,authenticated;
GRANT SELECT (feature_key,enabled) ON public.k4_public_settings TO anon,authenticated;
DROP POLICY IF EXISTS k4_public_settings_read ON public.k4_public_settings;
CREATE POLICY k4_public_settings_read ON public.k4_public_settings FOR SELECT
 TO anon,authenticated USING (true);

-- Admin status requires valid signed-in account AND active state.
CREATE OR REPLACE FUNCTION public.k4_account_active() RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
 SELECT auth.uid() IS NOT NULL AND EXISTS (
   SELECT 1 FROM public.k4_profiles
   WHERE user_id=auth.uid() AND account_status='active');
$$;
CREATE OR REPLACE FUNCTION public.k4_is_admin() RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
 SELECT public.k4_account_active() AND EXISTS (
   SELECT 1 FROM public.k4_profiles
   WHERE user_id=auth.uid() AND global_role='admin');
$$;
-- Restore v5.5 RLS helper behavior, but now require account approval.
CREATE OR REPLACE FUNCTION public.k4_can_view(p_project uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
 SELECT public.k4_account_active() AND (
   public.k4_is_admin() OR
   EXISTS(SELECT 1 FROM public.k4_projects p WHERE p.id=p_project AND p.owner_id=auth.uid()) OR
   EXISTS(SELECT 1 FROM public.k4_project_members m WHERE m.project_id=p_project AND m.user_id=auth.uid())
 );
$$;
CREATE OR REPLACE FUNCTION public.k4_can_edit(p_project uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
 SELECT public.k4_account_active() AND (
   public.k4_is_admin() OR
   EXISTS(SELECT 1 FROM public.k4_projects p WHERE p.id=p_project AND p.owner_id=auth.uid()) OR
   EXISTS(SELECT 1 FROM public.k4_project_members m WHERE m.project_id=p_project AND m.user_id=auth.uid()
     AND m.project_role IN ('technician','supervisor'))
 );
$$;
CREATE OR REPLACE FUNCTION public.k4_can_review(p_project uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
 SELECT public.k4_account_active() AND (
   public.k4_is_admin() OR
   EXISTS(SELECT 1 FROM public.k4_projects p WHERE p.id=p_project AND p.owner_id=auth.uid()) OR
   EXISTS(SELECT 1 FROM public.k4_project_members m WHERE m.project_id=p_project AND m.user_id=auth.uid()
     AND m.project_role='supervisor')
 );
$$;

-- Existing profile SELECT RLS from v5.5 exposes own row or admin only.
-- Account status is read-only for normal users (UPDATE display_name only).
DROP POLICY IF EXISTS k4_project_insert ON public.k4_projects;
CREATE POLICY k4_project_insert ON public.k4_projects FOR INSERT TO authenticated
 WITH CHECK (owner_id=auth.uid() AND public.k4_account_active());
DROP POLICY IF EXISTS k4_project_update ON public.k4_projects;
CREATE POLICY k4_project_update ON public.k4_projects FOR UPDATE TO authenticated
 USING (public.k4_account_active() AND (owner_id=auth.uid() OR public.k4_is_admin()))
 WITH CHECK (public.k4_account_active() AND (owner_id=auth.uid() OR public.k4_is_admin()));
DROP POLICY IF EXISTS k4_project_delete ON public.k4_projects;
CREATE POLICY k4_project_delete ON public.k4_projects FOR DELETE TO authenticated
 USING (public.k4_account_active() AND (owner_id=auth.uid() OR public.k4_is_admin()));

CREATE TABLE IF NOT EXISTS public.k4_admin_events (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 actor_id uuid NOT NULL REFERENCES auth.users(id),
 subject text NOT NULL,
 action text NOT NULL,
 detail text NOT NULL DEFAULT '',
 created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.k4_admin_events ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.k4_admin_events FROM PUBLIC,anon,authenticated;
GRANT SELECT ON public.k4_admin_events TO authenticated;
DROP POLICY IF EXISTS k4_admin_events_read ON public.k4_admin_events;
CREATE POLICY k4_admin_events_read ON public.k4_admin_events FOR SELECT TO authenticated
 USING (public.k4_is_admin());

-- Whitelist feature_key from table and require admin at RPC boundary.
CREATE OR REPLACE FUNCTION public.k4_admin_set_public_setting(p_feature text,p_enabled boolean)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
 IF NOT public.k4_is_admin() OR p_feature IS NULL OR p_enabled IS NULL THEN
   RAISE EXCEPTION 'Administrator aktif diperlukan'; END IF;
 UPDATE public.k4_public_settings SET enabled=p_enabled,updated_by=auth.uid(),updated_at=now()
   WHERE feature_key=p_feature;
 IF NOT FOUND THEN RAISE EXCEPTION 'Nama fitur tidak dikenal'; END IF;
 INSERT INTO public.k4_admin_events(actor_id,subject,action,detail)
 VALUES (auth.uid(),p_feature,'guest_feature_changed',p_enabled::text);
END $$;

-- Atomic update of all analytics flags from one form submission.
CREATE OR REPLACE FUNCTION public.k4_admin_set_guest_features(p_values jsonb)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
 IF NOT public.k4_is_admin() OR p_values IS NULL OR jsonb_typeof(p_values) <> 'object'
    OR (SELECT count(*) FROM jsonb_each(p_values)) <> 13 THEN
    RAISE EXCEPTION 'Payload admin tidak sah'; END IF;
 IF EXISTS (SELECT 1 FROM jsonb_each(p_values) q
    LEFT JOIN public.k4_public_settings s ON s.feature_key=q.key
    WHERE s.feature_key IS NULL OR q.key='registration_enabled' OR jsonb_typeof(q.value)<>'boolean')
 THEN RAISE EXCEPTION 'Nama fitur/status tidak sah'; END IF;
 UPDATE public.k4_public_settings SET enabled=(p_values->>feature_key)::boolean,
    updated_by=auth.uid(),updated_at=now()
 WHERE feature_key <> 'registration_enabled';
 INSERT INTO public.k4_admin_events(actor_id,subject,action,detail)
 VALUES(auth.uid(),'all_public_analytics','guest_bulk_update','13 flags');
END $$;

CREATE OR REPLACE FUNCTION public.k4_admin_guest_preset(p_preset text)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE f text;
BEGIN
 IF NOT public.k4_is_admin() OR p_preset NOT IN ('all_analytics','basic_only','closed') THEN
   RAISE EXCEPTION 'Preset tidak diizinkan'; END IF;
 UPDATE public.k4_public_settings
  SET enabled=CASE WHEN p_preset='all_analytics' THEN TRUE
                   WHEN p_preset='basic_only' THEN feature_key IN ('upload_csv','summary','statistics','visuals','method')
                   ELSE FALSE END,
      updated_by=auth.uid(),updated_at=now()
  WHERE feature_key <> 'registration_enabled';
 INSERT INTO public.k4_admin_events(actor_id,subject,action,detail)
 VALUES (auth.uid(),'all_public_analytics','guest_preset',p_preset);
END $$;

CREATE OR REPLACE FUNCTION public.k4_admin_set_account_status(p_user uuid,p_status text)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
 IF NOT public.k4_is_admin() OR p_status NOT IN ('pending','active','suspended')
    OR p_user=auth.uid() THEN
   RAISE EXCEPTION 'Perubahan status akun tidak diizinkan'; END IF;
 UPDATE public.k4_profiles SET account_status=p_status WHERE user_id=p_user;
 IF NOT FOUND THEN RAISE EXCEPTION 'Pengguna tidak ditemukan'; END IF;
 INSERT INTO public.k4_admin_events(actor_id,subject,action,detail)
 VALUES (auth.uid(),p_user::text,'account_status_changed',p_status);
END $$;

-- Keep v5.5 role RPC but add audit and active-admin requirement via k4_is_admin().
CREATE OR REPLACE FUNCTION public.k4_admin_set_role(p_user uuid,p_role text)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
BEGIN
 IF NOT public.k4_is_admin() OR p_role NOT IN ('user','admin') OR p_user=auth.uid()
 THEN RAISE EXCEPTION 'Perubahan peran tidak diizinkan'; END IF;
 UPDATE public.k4_profiles SET global_role=p_role WHERE user_id=p_user;
 IF NOT FOUND THEN RAISE EXCEPTION 'Pengguna tidak ditemukan'; END IF;
 INSERT INTO public.k4_admin_events(actor_id,subject,action,detail)
 VALUES (auth.uid(),p_user::text,'global_role_changed',p_role);
END $$;

-- Existing SECURITY DEFINER report submit RPC requires explicit active author check.
CREATE OR REPLACE FUNCTION public.k4_submit_report(p_report uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE r public.k4_reports%ROWTYPE;
BEGIN
 SELECT * INTO r FROM public.k4_reports WHERE id=p_report FOR UPDATE;
 IF NOT public.k4_account_active() OR NOT FOUND OR r.author_id<>auth.uid()
    OR r.status NOT IN ('draft','needs_revision')
 THEN RAISE EXCEPTION 'Laporan tidak dapat diajukan'; END IF;
 UPDATE public.k4_reports SET status='submitted',review_note='',reviewer_id=null,
   reviewed_at=null,public_token=null WHERE id=p_report;
END $$;

-- Fail closed if function SQL privileges were auto-granted by existing defaults.
REVOKE ALL ON FUNCTION public.k4_account_active() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.k4_admin_set_public_setting(text,boolean) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.k4_admin_guest_preset(text) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.k4_admin_set_guest_features(jsonb) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.k4_admin_set_account_status(uuid,text) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.k4_admin_set_role(uuid,text) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.k4_account_active() TO authenticated;
GRANT EXECUTE ON FUNCTION public.k4_admin_set_public_setting(text,boolean),
 public.k4_admin_guest_preset(text),public.k4_admin_set_guest_features(jsonb),public.k4_admin_set_account_status(uuid,text),
 public.k4_admin_set_role(uuid,text) TO authenticated;
COMMIT;

-- IMPORTANT ADMIN BOOTSTRAP: First register via Akun, then SQL Editor only:
-- UPDATE public.k4_profiles SET global_role='admin', account_status='active'
-- WHERE user_id=(SELECT id FROM auth.users WHERE email='YOUR_OWN_ADMIN_EMAIL');
-- Verify exactly ONE known email before applying. Never put credentials in Git.
-- Admin-created Supabase Auth accounts/invites require server-side privileged key;
-- use Supabase Dashboard > Authentication > Users > Invite User instead.
