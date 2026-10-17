-- Migration 002: ICP entity and enriched Search / Lead columns matching the UI domain

CREATE TABLE IF NOT EXISTS icps (
  id uuid PRIMARY KEY,
  name text NOT NULL,
  industry text NOT NULL DEFAULT '',
  company_size text NOT NULL DEFAULT '',
  target_roles text NOT NULL DEFAULT '',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS searches (
  id uuid PRIMARY KEY,
  icp_id uuid REFERENCES icps(id) ON DELETE SET NULL,
  query text NOT NULL,
  location text NOT NULL,
  status varchar(32) NOT NULL DEFAULT 'queued',
  leads_found integer NOT NULL DEFAULT 0,
  contacted integer NOT NULL DEFAULT 0,
  rejected integer NOT NULL DEFAULT 0,
  fresh_leads integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE searches
  ADD COLUMN IF NOT EXISTS icp_id uuid REFERENCES icps(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS leads_found integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS contacted integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS rejected integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS fresh_leads integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS ix_searches_icp_id ON searches (icp_id);

CREATE TABLE IF NOT EXISTS leads (
  id uuid PRIMARY KEY,
  search_id uuid NOT NULL REFERENCES searches(id) ON DELETE CASCADE,
  icp_id uuid REFERENCES icps(id) ON DELETE SET NULL,
  name text NOT NULL DEFAULT '',
  role text NOT NULL DEFAULT '',
  company text NOT NULL,
  website text,
  industry text NOT NULL DEFAULT '',
  company_size text NOT NULL DEFAULT '',
  location text NOT NULL DEFAULT '',
  score integer NOT NULL DEFAULT 0,
  stage varchar(32) NOT NULL DEFAULT 'discovered',
  email text,
  linkedin text,
  last_activity_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE leads
  ADD COLUMN IF NOT EXISTS icp_id uuid REFERENCES icps(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS name text NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS role text NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS industry text NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS company_size text NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS location text NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS score integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS email text,
  ADD COLUMN IF NOT EXISTS linkedin text,
  ADD COLUMN IF NOT EXISTS last_activity_at timestamptz;

CREATE INDEX IF NOT EXISTS ix_leads_search_id ON leads (search_id);
CREATE INDEX IF NOT EXISTS ix_leads_icp_id ON leads (icp_id);

CREATE TABLE IF NOT EXISTS jobs (
  id uuid PRIMARY KEY,
  kind varchar(64) NOT NULL,
  payload json NOT NULL DEFAULT '{}',
  status varchar(32) NOT NULL DEFAULT 'pending',
  attempts integer NOT NULL DEFAULT 0,
  error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz
);

CREATE INDEX IF NOT EXISTS ix_jobs_status_created_at ON jobs (status, created_at);
