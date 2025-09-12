-- 0001_init.sql
-- Base schema with org-scoped RLS and helper function

BEGIN;

-- Helper: get current org id from custom GUC set by the API per-request
CREATE OR REPLACE FUNCTION public.current_org_id() RETURNS text LANGUAGE plpgsql STABLE AS $$
DECLARE
  org text;
BEGIN
  BEGIN
    org := current_setting('app.current_org_id', true);
  EXCEPTION WHEN others THEN
    org := NULL;
  END;
  RETURN org;
END;
$$;

-- Jobs a foreman will see on Today
CREATE TABLE IF NOT EXISTS public.jobs (
  id            text PRIMARY KEY,
  org_id        text NOT NULL,
  name          text NOT NULL,
  profit_chip   text NOT NULL DEFAULT 'gray',
  updated_at    timestamptz NOT NULL DEFAULT now()
);

-- Materials per job
CREATE TABLE IF NOT EXISTS public.materials (
  id          text PRIMARY KEY,
  org_id      text NOT NULL,
  job_id      text NOT NULL REFERENCES public.jobs(id) ON DELETE CASCADE,
  sku         text NOT NULL,
  qty         integer NOT NULL,
  updated_at  timestamptz NOT NULL DEFAULT now()
);

-- Pins (staging/work/switch) per job
CREATE TABLE IF NOT EXISTS public.pins (
  id          text PRIMARY KEY,
  org_id      text NOT NULL,
  job_id      text NOT NULL REFERENCES public.jobs(id) ON DELETE CASCADE,
  kind        text NOT NULL CHECK (kind IN ('staging','work','switch')),
  lat         double precision NOT NULL,
  lng         double precision NOT NULL,
  updated_at  timestamptz NOT NULL DEFAULT now()
);

-- Photo checklist
CREATE TABLE IF NOT EXISTS public.checklist (
  id          text PRIMARY KEY,
  org_id      text NOT NULL,
  prompt      text NOT NULL,
  required    boolean NOT NULL DEFAULT true,
  updated_at  timestamptz NOT NULL DEFAULT now()
);

-- Timesheets (simplified)
CREATE TABLE IF NOT EXISTS public.timesheets (
  id          text PRIMARY KEY,
  org_id      text NOT NULL,
  job_id      text,
  submitted_by text,
  submitted_at timestamptz NOT NULL DEFAULT now(),
  payload     jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at  timestamptz NOT NULL DEFAULT now()
);

-- Closeouts (simplified)
CREATE TABLE IF NOT EXISTS public.closeouts (
  id          text PRIMARY KEY,
  org_id      text NOT NULL,
  job_id      text,
  pdf_key     text,
  approved    boolean NOT NULL DEFAULT false,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);

-- Enable RLS and add org_id policies
DO $$
DECLARE
  tbl text;
BEGIN
  FOR tbl IN SELECT unnest(ARRAY['jobs','materials','pins','checklist','timesheets','closeouts']) LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', tbl);
    EXECUTE format('DROP POLICY IF EXISTS rls_%I_select ON public.%I', tbl, tbl);
    EXECUTE format('DROP POLICY IF EXISTS rls_%I_write ON public.%I', tbl, tbl);
    EXECUTE format('CREATE POLICY rls_%I_select ON public.%I FOR SELECT USING (org_id = public.current_org_id())', tbl, tbl);
    EXECUTE format('CREATE POLICY rls_%I_write  ON public.%I FOR ALL    USING (org_id = public.current_org_id()) WITH CHECK (org_id = public.current_org_id())', tbl, tbl);
  END LOOP;
END $$;

COMMIT;
