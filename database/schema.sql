-- Schema for Microsoft Announcement Hybrid Search System
-- SQLite + FTS5 Full-Text Search

-- ============================================
-- Main Table: announcements
-- ============================================
CREATE TABLE IF NOT EXISTS announcements (
    uuid TEXT PRIMARY KEY NOT NULL,
    month TEXT NOT NULL,                    -- Format: YYYY-MM
    title TEXT NOT NULL,
    content TEXT NOT NULL,                  -- Original content
    category TEXT,                          -- Enum: Pricing, Security, Feature Update, Compliance, Retirement, General
    products TEXT,                          -- JSON array of product names
    impact_level TEXT,                      -- Enum: High, Medium, Low
    date_effective TEXT,                    -- ISO format: YYYY-MM-DD
    metadata_json TEXT                      -- Full metadata dump (Pydantic JSON)
);

-- ============================================
-- FTS5 Virtual Table for Full-Text Search
-- ============================================
CREATE VIRTUAL TABLE IF NOT EXISTS announcements_fts USING fts5(
    title,
    content,
    content=announcements,                  -- Link to source table
    content_rowid=rowid,                    -- Use rowid for linking
    tokenize='porter unicode61'             -- Porter stemming + Unicode support
);

-- ============================================
-- Triggers: Keep FTS5 in Sync with Main Table
-- ============================================

-- Trigger: After INSERT
CREATE TRIGGER IF NOT EXISTS announcements_ai AFTER INSERT ON announcements BEGIN
    INSERT INTO announcements_fts(rowid, title, content)
    VALUES (new.rowid, new.title, new.content);
END;

-- Trigger: After DELETE
CREATE TRIGGER IF NOT EXISTS announcements_ad AFTER DELETE ON announcements BEGIN
    INSERT INTO announcements_fts(announcements_fts, rowid, title, content)
    VALUES('delete', old.rowid, old.title, old.content);
END;

-- Trigger: After UPDATE
CREATE TRIGGER IF NOT EXISTS announcements_au AFTER UPDATE ON announcements BEGIN
    INSERT INTO announcements_fts(announcements_fts, rowid, title, content)
    VALUES('delete', old.rowid, old.title, old.content);
    INSERT INTO announcements_fts(rowid, title, content)
    VALUES (new.rowid, new.title, new.content);
END;

-- ============================================
-- Indexes for Filtering Performance
-- ============================================
CREATE INDEX IF NOT EXISTS idx_announcements_month ON announcements(month);
CREATE INDEX IF NOT EXISTS idx_announcements_category ON announcements(category);
CREATE INDEX IF NOT EXISTS idx_announcements_impact_level ON announcements(impact_level);
CREATE INDEX IF NOT EXISTS idx_announcements_date_effective ON announcements(date_effective);

-- ============================================
-- Usage Notes
-- ============================================
-- FTS5 Search Query Example:
--   SELECT * FROM announcements
--   JOIN announcements_fts ON announcements.rowid = announcements_fts.rowid
--   WHERE announcements_fts MATCH 'security AND azure'
--   ORDER BY rank;
--
-- Hybrid Filtering Example:
--   SELECT * FROM announcements
--   JOIN announcements_fts ON announcements.rowid = announcements_fts.rowid
--   WHERE announcements_fts MATCH 'pricing'
--     AND category = 'Pricing'
--     AND impact_level = 'High'
--   ORDER BY rank
--   LIMIT 20;
--
-- Snippet Generation:
--   SELECT uuid, title, snippet(announcements_fts, -1, '<b>', '</b>', '...', 64) as snippet
--   FROM announcements
--   JOIN announcements_fts ON announcements.rowid = announcements_fts.rowid
--   WHERE announcements_fts MATCH 'azure'
--   ORDER BY rank;
