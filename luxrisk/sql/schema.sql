PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS collection (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    mode TEXT NOT NULL CHECK (mode IN ('demo','live')),
    collected_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('success','failed')),
    note TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS raw_response (
    run_id INTEGER NOT NULL REFERENCES collection(run_id),
    country TEXT NOT NULL,
    indicator TEXT NOT NULL,
    url TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    payload BLOB NOT NULL,
    definition_json TEXT NOT NULL,
    PRIMARY KEY (run_id, country, indicator)
);
CREATE TABLE IF NOT EXISTS observation (
    run_id INTEGER NOT NULL,
    country TEXT NOT NULL,
    indicator TEXT NOT NULL,
    period TEXT NOT NULL,
    value REAL,
    status TEXT NOT NULL,
    PRIMARY KEY (run_id, country, indicator, period),
    FOREIGN KEY (run_id, country, indicator) REFERENCES raw_response(run_id, country, indicator)
);
CREATE INDEX IF NOT EXISTS series_lookup ON observation(country, indicator, run_id);
CREATE VIEW IF NOT EXISTS latest_series AS
SELECT r.country, r.indicator, c.mode, MAX(r.run_id) AS run_id
FROM raw_response r JOIN collection c USING(run_id)
WHERE c.status = 'success'
GROUP BY r.country, r.indicator, c.mode;
