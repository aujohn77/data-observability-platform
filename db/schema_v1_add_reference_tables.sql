BEGIN;

-- ----------------------------
-- DQ check definitions (truth)
-- ----------------------------
CREATE TABLE IF NOT EXISTS ops_dq_check_definition (
  check_name      text PRIMARY KEY,                  -- stable identifier (snake_case)
  description     text NOT NULL,
  category        text NOT NULL CHECK (category IN ('freshness','completeness','validity','consistency')),
  severity        text NOT NULL CHECK (severity IN ('low','medium','high','critical')),
  default_threshold numeric,                          -- meaning depends on check_name (documented in description)
  is_enabled      boolean NOT NULL DEFAULT true,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ops_dq_check_def_category
  ON ops_dq_check_definition (category);

CREATE INDEX IF NOT EXISTS idx_ops_dq_check_def_enabled
  ON ops_dq_check_definition (is_enabled);


-- ----------------------------
-- Anomaly types (truth)
-- ----------------------------
CREATE TABLE IF NOT EXISTS ops_anomaly_type (
  anomaly_type   text PRIMARY KEY,                   -- stable identifier
  description    text NOT NULL,
  default_severity text NOT NULL CHECK (default_severity IN ('low','medium','high','critical')),
  is_enabled     boolean NOT NULL DEFAULT true,
  created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ops_anomaly_type_enabled
  ON ops_anomaly_type (is_enabled);

COMMIT;
