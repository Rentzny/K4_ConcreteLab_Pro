-- ConcreteLab Pro v5.5 / schema cloud Supabase.
-- Jalankan SEKALI pada SQL Editor proyek Supabase baru, setelah backup.
-- Hanya anon/publishable key boleh dipakai aplikasi: JANGAN pakai service_role.
-- RLS dibatasi per identitas auth.uid() dan keanggotaan proyek.
BEGIN;
SET LOCAL search_path TO public, extensions;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS public.k4_profiles (
  user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email text NOT NULL DEFAULT '',
  display_name text NOT NULL DEFAULT '',
  global_role text NOT NULL DEFAULT 'user' CHECK (global_role IN ('user','admin')),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION public.k4_on_new_user() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
  INSERT INTO public.k4_profiles(user_id,email,display_name)
  VALUES (NEW.id,coalesce(NEW.email,''),left(coalesce(NEW.raw_user_meta_data->>'name', ''),100))
  ON CONFLICT (user_id) DO NOTHING;
  RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS k4_new_auth_user ON auth.users;
CREATE TRIGGER k4_new_auth_user AFTER INSERT ON auth.users
FOR EACH ROW EXECUTE FUNCTION public.k4_on_new_user();
INSERT INTO public.k4_profiles(user_id,email)
SELECT id,coalesce(email,'') FROM auth.users ON CONFLICT (user_id) DO NOTHING;

CREATE OR REPLACE FUNCTION public.k4_is_admin() RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
  SELECT EXISTS(SELECT 1 FROM public.k4_profiles p
    WHERE p.user_id=auth.uid() AND p.global_role='admin');
$$;

CREATE TABLE IF NOT EXISTS public.k4_projects (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id uuid NOT NULL REFERENCES auth.users(id),
  name text NOT NULL CHECK (char_length(btrim(name)) BETWEEN 2 AND 120),
  code text NOT NULL DEFAULT '' CHECK (char_length(code)<=45),
  description text NOT NULL DEFAULT '' CHECK (char_length(description)<=1500),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS k4_projects_owner_idx ON public.k4_projects(owner_id);

CREATE TABLE IF NOT EXISTS public.k4_project_members (
  project_id uuid NOT NULL REFERENCES public.k4_projects(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  project_role text NOT NULL CHECK (project_role IN ('viewer','technician','supervisor')),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(project_id,user_id)
);
CREATE INDEX IF NOT EXISTS k4_members_user_idx ON public.k4_project_members(user_id);

CREATE OR REPLACE FUNCTION public.k4_can_view(p_project uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
  SELECT auth.uid() IS NOT NULL AND (
    public.k4_is_admin() OR
    EXISTS(SELECT 1 FROM public.k4_projects p WHERE p.id=p_project AND p.owner_id=auth.uid()) OR
    EXISTS(SELECT 1 FROM public.k4_project_members m WHERE m.project_id=p_project AND m.user_id=auth.uid())
  );
$$;
CREATE OR REPLACE FUNCTION public.k4_can_edit(p_project uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
  SELECT auth.uid() IS NOT NULL AND (
    public.k4_is_admin() OR
    EXISTS(SELECT 1 FROM public.k4_projects p WHERE p.id=p_project AND p.owner_id=auth.uid()) OR
    EXISTS(SELECT 1 FROM public.k4_project_members m WHERE m.project_id=p_project AND m.user_id=auth.uid()
       AND m.project_role IN ('technician','supervisor'))
  );
$$;
CREATE OR REPLACE FUNCTION public.k4_can_review(p_project uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
  SELECT auth.uid() IS NOT NULL AND (
    public.k4_is_admin() OR
    EXISTS(SELECT 1 FROM public.k4_projects p WHERE p.id=p_project AND p.owner_id=auth.uid()) OR
    EXISTS(SELECT 1 FROM public.k4_project_members m WHERE m.project_id=p_project AND m.user_id=auth.uid()
       AND m.project_role='supervisor')
  );
$$;

CREATE TABLE IF NOT EXISTS public.k4_snapshots (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES public.k4_projects(id) ON DELETE CASCADE,
  author_id uuid NOT NULL REFERENCES auth.users(id),
  csv_text text NOT NULL CHECK (octet_length(csv_text) BETWEEN 10 AND 10485760),
  csv_sha256 text GENERATED ALWAYS AS (encode(digest(convert_to(csv_text,'UTF8'),'sha256'),'hex')) STORED,
  target_mpa numeric NOT NULL CHECK (target_mpa>0 AND target_mpa<=150),
  note text NOT NULL DEFAULT '' CHECK (char_length(note)<=500),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS k4_snapshots_project_idx ON public.k4_snapshots(project_id,created_at DESC);

CREATE TABLE IF NOT EXISTS public.k4_reports (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES public.k4_projects(id) ON DELETE CASCADE,
  snapshot_id uuid NOT NULL REFERENCES public.k4_snapshots(id),
  author_id uuid NOT NULL REFERENCES auth.users(id),
  revision integer NOT NULL CHECK(revision>0),
  status text NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','submitted','needs_revision','approved','rejected')),
  reviewer_id uuid REFERENCES auth.users(id),
  review_note text NOT NULL DEFAULT '' CHECK(char_length(review_note)<=1500),
  public_token text UNIQUE,
  created_at timestamptz NOT NULL DEFAULT now(),
  reviewed_at timestamptz,
  UNIQUE (project_id,revision),
  CONSTRAINT approved_token CHECK (status='approved' OR public_token IS NULL)
);
CREATE INDEX IF NOT EXISTS k4_reports_project_idx ON public.k4_reports(project_id,created_at DESC);

CREATE TABLE IF NOT EXISTS public.k4_audit_events (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id uuid NOT NULL REFERENCES public.k4_projects(id) ON DELETE CASCADE,
  actor_id uuid,
  event text NOT NULL,
  entity_id uuid,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS k4_audit_project_idx ON public.k4_audit_events(project_id,created_at DESC);

ALTER TABLE public.k4_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.k4_projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.k4_project_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.k4_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.k4_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.k4_audit_events ENABLE ROW LEVEL SECURITY;

-- Prinsip least privilege: revoke operasi sensitif, grant hanya yang diperlukan.
REVOKE ALL ON public.k4_profiles,public.k4_projects,public.k4_project_members,
  public.k4_snapshots,public.k4_reports,public.k4_audit_events FROM anon,authenticated;
GRANT SELECT ON public.k4_profiles TO authenticated;
GRANT UPDATE (display_name) ON public.k4_profiles TO authenticated;
GRANT SELECT,INSERT,DELETE ON public.k4_projects TO authenticated;
GRANT UPDATE (name,code,description) ON public.k4_projects TO authenticated;
GRANT SELECT,INSERT,UPDATE,DELETE ON public.k4_project_members TO authenticated;
GRANT SELECT,INSERT ON public.k4_snapshots TO authenticated;
GRANT SELECT ON public.k4_reports, public.k4_audit_events TO authenticated;

DROP POLICY IF EXISTS k4_profile_select ON public.k4_profiles;
CREATE POLICY k4_profile_select ON public.k4_profiles FOR SELECT TO authenticated
USING (user_id=auth.uid() OR public.k4_is_admin());
DROP POLICY IF EXISTS k4_profile_edit ON public.k4_profiles;
CREATE POLICY k4_profile_edit ON public.k4_profiles FOR UPDATE TO authenticated
USING (user_id=auth.uid()) WITH CHECK (user_id=auth.uid());

DROP POLICY IF EXISTS k4_project_select ON public.k4_projects;
CREATE POLICY k4_project_select ON public.k4_projects FOR SELECT TO authenticated
USING (public.k4_can_view(id));
DROP POLICY IF EXISTS k4_project_insert ON public.k4_projects;
CREATE POLICY k4_project_insert ON public.k4_projects FOR INSERT TO authenticated
WITH CHECK (owner_id=auth.uid());
DROP POLICY IF EXISTS k4_project_update ON public.k4_projects;
CREATE POLICY k4_project_update ON public.k4_projects FOR UPDATE TO authenticated
USING (owner_id=auth.uid() OR public.k4_is_admin())
WITH CHECK (owner_id=auth.uid() OR public.k4_is_admin());
DROP POLICY IF EXISTS k4_project_delete ON public.k4_projects;
CREATE POLICY k4_project_delete ON public.k4_projects FOR DELETE TO authenticated
USING (owner_id=auth.uid() OR public.k4_is_admin());

DROP POLICY IF EXISTS k4_members_select ON public.k4_project_members;
CREATE POLICY k4_members_select ON public.k4_project_members FOR SELECT TO authenticated
USING (public.k4_can_view(project_id));
DROP POLICY IF EXISTS k4_members_insert ON public.k4_project_members;
CREATE POLICY k4_members_insert ON public.k4_project_members FOR INSERT TO authenticated
WITH CHECK (public.k4_can_review(project_id));
DROP POLICY IF EXISTS k4_members_update ON public.k4_project_members;
CREATE POLICY k4_members_update ON public.k4_project_members FOR UPDATE TO authenticated
USING (public.k4_can_review(project_id)) WITH CHECK (public.k4_can_review(project_id));
DROP POLICY IF EXISTS k4_members_delete ON public.k4_project_members;
CREATE POLICY k4_members_delete ON public.k4_project_members FOR DELETE TO authenticated
USING (public.k4_can_review(project_id));

DROP POLICY IF EXISTS k4_snapshots_select ON public.k4_snapshots;
CREATE POLICY k4_snapshots_select ON public.k4_snapshots FOR SELECT TO authenticated
USING (public.k4_can_view(project_id));
DROP POLICY IF EXISTS k4_snapshots_insert ON public.k4_snapshots;
CREATE POLICY k4_snapshots_insert ON public.k4_snapshots FOR INSERT TO authenticated
WITH CHECK (author_id=auth.uid() AND public.k4_can_edit(project_id));
DROP POLICY IF EXISTS k4_reports_select ON public.k4_reports;
CREATE POLICY k4_reports_select ON public.k4_reports FOR SELECT TO authenticated
USING (public.k4_can_view(project_id));
DROP POLICY IF EXISTS k4_audit_select ON public.k4_audit_events;
CREATE POLICY k4_audit_select ON public.k4_audit_events FOR SELECT TO authenticated
USING (public.k4_can_review(project_id));

-- Snapshot dan laporan tidak boleh direvisi diam-diam: buat versi baru.
-- RPC status check: user harus punya edit, reviewer bukan author yang sama.
CREATE OR REPLACE FUNCTION public.k4_create_report(p_project uuid,p_snapshot uuid)
RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE rid uuid; rev integer;
BEGIN
 IF NOT public.k4_can_edit(p_project) THEN RAISE EXCEPTION 'Tidak berhak membuat laporan'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.k4_snapshots s WHERE s.id=p_snapshot AND s.project_id=p_project)
 THEN RAISE EXCEPTION 'Snapshot tidak cocok'; END IF;
 PERFORM 1 FROM public.k4_projects p WHERE p.id=p_project FOR UPDATE;
 SELECT coalesce(max(r.revision),0)+1 INTO rev FROM public.k4_reports r WHERE r.project_id=p_project;
 INSERT INTO public.k4_reports(project_id,snapshot_id,author_id,revision)
 VALUES(p_project,p_snapshot,auth.uid(),rev) RETURNING id INTO rid;
 RETURN rid;
END $$;
CREATE OR REPLACE FUNCTION public.k4_submit_report(p_report uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE r public.k4_reports%ROWTYPE;
BEGIN
 SELECT * INTO r FROM public.k4_reports WHERE id=p_report FOR UPDATE;
 IF NOT FOUND OR r.author_id<>auth.uid() OR r.status NOT IN ('draft','needs_revision')
 THEN RAISE EXCEPTION 'Laporan tidak dapat diajukan'; END IF;
 UPDATE public.k4_reports SET status='submitted',review_note='',reviewer_id=null,reviewed_at=null,
    public_token=null WHERE id=p_report;
END $$;
CREATE OR REPLACE FUNCTION public.k4_review_report(p_report uuid,p_decision text,p_note text DEFAULT '')
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE r public.k4_reports%ROWTYPE; token text;
BEGIN
 SELECT * INTO r FROM public.k4_reports WHERE id=p_report FOR UPDATE;
 IF NOT FOUND OR NOT public.k4_can_review(r.project_id) OR r.author_id=auth.uid()
 OR r.status<>'submitted' OR p_decision NOT IN ('approved','needs_revision','rejected')
 THEN RAISE EXCEPTION 'Review tidak diizinkan'; END IF;
 IF p_decision<>'approved' AND char_length(btrim(p_note))<3
 THEN RAISE EXCEPTION 'Alasan revisi/penolakan wajib diisi'; END IF;
 IF char_length(coalesce(p_note,''))>1500 THEN RAISE EXCEPTION 'Catatan terlalu panjang'; END IF;
 token := CASE WHEN p_decision='approved' THEN encode(gen_random_bytes(24),'hex') ELSE NULL END;
 UPDATE public.k4_reports SET status=p_decision,review_note=coalesce(p_note,''),
   reviewer_id=auth.uid(),reviewed_at=now(),public_token=token WHERE id=p_report;
 RETURN token;
END $$;

CREATE OR REPLACE FUNCTION public.k4_admin_set_role(p_user uuid,p_role text)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
BEGIN
 IF NOT public.k4_is_admin() OR p_role NOT IN ('user','admin') OR p_user=auth.uid()
 THEN RAISE EXCEPTION 'Perubahan peran tidak diizinkan'; END IF;
 UPDATE public.k4_profiles SET global_role=p_role WHERE user_id=p_user;
 IF NOT FOUND THEN RAISE EXCEPTION 'Pengguna tidak ditemukan'; END IF;
END $$;

-- Endpoint publik dengan data TERBATAS; hanya laporan yang berstatus approved.
CREATE OR REPLACE FUNCTION public.k4_verify_report(p_token text)
RETURNS TABLE(report_id uuid, report_revision integer, project_code text,
              approved_at timestamptz, csv_fingerprint text, status text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path='' AS $$
 SELECT r.id,r.revision,p.code,r.reviewed_at,s.csv_sha256,r.status
 FROM public.k4_reports r
 JOIN public.k4_projects p ON p.id=r.project_id
 JOIN public.k4_snapshots s ON s.id=r.snapshot_id
 WHERE r.public_token=p_token AND r.status='approved'
 AND p_token IS NOT NULL AND char_length(p_token)=48 LIMIT 1;
$$;

-- Trigger audit otomatis: tidak mengandalkan kejujuran client.
CREATE OR REPLACE FUNCTION public.k4_audit_trigger() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE pid uuid; eventname text; entity uuid;
BEGIN
 pid:=coalesce(NEW.project_id,OLD.project_id);
 entity:=coalesce(NEW.id,OLD.id);
 eventname:=TG_TABLE_NAME || ':' || lower(TG_OP);
 IF TG_TABLE_NAME='k4_reports' AND TG_OP='UPDATE' THEN
   eventname:='report_status:'||NEW.status;
 END IF;
 INSERT INTO public.k4_audit_events(project_id,actor_id,event,entity_id)
 VALUES(pid,auth.uid(),eventname,entity);
 RETURN coalesce(NEW,OLD);
END $$;
DROP TRIGGER IF EXISTS k4_audit_snapshot ON public.k4_snapshots;
CREATE TRIGGER k4_audit_snapshot AFTER INSERT ON public.k4_snapshots
FOR EACH ROW EXECUTE FUNCTION public.k4_audit_trigger();
DROP TRIGGER IF EXISTS k4_audit_report ON public.k4_reports;
CREATE TRIGGER k4_audit_report AFTER INSERT OR UPDATE ON public.k4_reports
FOR EACH ROW EXECUTE FUNCTION public.k4_audit_trigger();

-- GRANT RPC; built-in postgres function privileges can default to PUBLIC, revoke explicitly.
REVOKE ALL ON FUNCTION public.k4_on_new_user() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.k4_audit_trigger() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.k4_is_admin(),public.k4_can_view(uuid),public.k4_can_edit(uuid),public.k4_can_review(uuid),
 public.k4_create_report(uuid,uuid),public.k4_submit_report(uuid),
 public.k4_review_report(uuid,text,text),public.k4_admin_set_role(uuid,text),public.k4_verify_report(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.k4_is_admin(),public.k4_can_view(uuid),public.k4_can_edit(uuid),public.k4_can_review(uuid),
 public.k4_create_report(uuid,uuid),public.k4_submit_report(uuid),
 public.k4_review_report(uuid,text,text),public.k4_admin_set_role(uuid,text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.k4_verify_report(text) TO anon,authenticated;
COMMIT;

-- PROMOSI ADMIN PERTAMA (jalankan sendiri sesudah akun signup; JANGAN masukkan email di Git):
-- UPDATE public.k4_profiles SET global_role='admin'
-- WHERE user_id=(SELECT id FROM auth.users WHERE email='EMAIL_ADMIN_ANDA');
