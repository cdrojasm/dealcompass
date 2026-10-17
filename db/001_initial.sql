-- Reference schema. The API/worker bootstrap tables with SQLAlchemy create_all.
CREATE TABLE icps (
  id uuid PRIMARY KEY,
  name text NOT NULL,
  industry text NOT NULL DEFAULT '',
  company_size text NOT NULL DEFAULT '',
  target_roles text NOT NULL DEFAULT '',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE searches (
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
CREATE INDEX ix_searches_icp_id ON searches (icp_id);

CREATE TABLE leads (
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
CREATE INDEX ix_leads_search_id ON leads (search_id);
CREATE INDEX ix_leads_icp_id ON leads (icp_id);

CREATE TABLE jobs (
  id uuid PRIMARY KEY,
  kind varchar(64) NOT NULL,
  payload json NOT NULL DEFAULT '{}',
  status varchar(32) NOT NULL DEFAULT 'pending',
  attempts integer NOT NULL DEFAULT 0,
  error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz
);
CREATE INDEX ix_jobs_status_created_at ON jobs (status, created_at);
