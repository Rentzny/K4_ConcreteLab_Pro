-- ConcreteLab Pro v8.0: self-service registration without manual admin approval.
-- RUN ONCE (safe to rerun) after schema_v55.sql AND schema_v60.sql.
-- This does NOT disable Supabase Auth email confirmation.
-- This does NOT elevate any user to administrator or unlock private projects.
-- Existing pending and suspended users are deliberately NOT activated.
-- Back up the database before changes, especially on a production project.
BEGIN;
DO $precheck$
BEGIN
  IF to_regclass('public.k4_profiles') IS NULL OR
     to_regclass('public.k4_public_settings') IS NULL OR
     NOT EXISTS (
       SELECT 1 FROM information_schema.columns
       WHERE table_schema='public' AND table_name='k4_profiles'
         AND column_name='account_status'
     ) THEN
    RAISE EXCEPTION 'Install schema v5.5 and v6.0 before schema_v80.sql';
  END IF;
END $precheck$;
-- v6 default pending; v8 new profiles are ACTIVE by default.
-- v5.5 auth.users AFTER INSERT trigger inserts no account_status column, so
-- this default takes effect automatically for newly registered users.
ALTER TABLE public.k4_profiles
  ALTER COLUMN account_status SET DEFAULT 'active';
-- Preserve global_role default 'user' and all RLS policies from v6.
-- Do not UPDATE previously pending/suspended accounts.
COMMIT;
