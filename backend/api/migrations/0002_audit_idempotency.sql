-- 0002_audit_idempotency.sql
-- Adds audit_log and idempotency_keys tables with RLS by org_id

BEGIN;

CREATE TABLE IF NOT EXISTS public.audit_log (
  id           text PRIMARY KEY,
  org_id       text NOT NULL,
  user_sub     text,
  action       text NOT NULL,
  details      jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.idempotency_keys (
  id            text PRIMARY KEY,
  org_id        text NOT NULL,
  endpoint      text NOT NULL,
  request_hash  text,
  response      jsonb,
  status        text NOT NULL DEFAULT 'succeeded',
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);

-- Enable RLS and add policies
ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.idempotency_keys ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS rls_audit_log_select ON public.audit_log;
DROP POLICY IF EXISTS rls_audit_log_write ON public.audit_log;
CREATE POLICY rls_audit_log_select ON public.audit_log FOR SELECT USING (org_id = public.current_org_id());
CREATE POLICY rls_audit_log_write  ON public.audit_log FOR ALL    USING (org_id = public.current_org_id()) WITH CHECK (org_id = public.current_org_id());

DROP POLICY IF EXISTS rls_idem_select ON public.idempotency_keys;
DROP POLICY IF EXISTS rls_idem_write ON public.idempotency_keys;
CREATE POLICY rls_idem_select ON public.idempotency_keys FOR SELECT USING (org_id = public.current_org_id());
CREATE POLICY rls_idem_write  ON public.idempotency_keys FOR ALL    USING (org_id = public.current_org_id()) WITH CHECK (org_id = public.current_org_id());

COMMIT;
