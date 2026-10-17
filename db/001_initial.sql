-- Reference schema. The API/worker bootstrap tables with SQLAlchemy create_all.
CREATE TABLE searches (
  id uuid PRIMARY KEY,
  query text NOT NULL,
  location text NOT NULL,
  status varchar(32) NOT NULL DEFAULT 'queued',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE leads (
  id uuid PRIMARY KEY,
  search_id uuid NOT NULL REFERENCES searches(id) ON DELETE CASCADE,
  company text NOT NULL,
  website text,
  stage varchar(32) NOT NULL DEFAULT 'discovered',
  created_at timestamptz NOT NULL DEFAULT now()
);

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
