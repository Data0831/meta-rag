erDiagram
    announcements {
        TEXT id PK
        TEXT month
        TEXT title
        TEXT content
        TEXT category
        TEXT products
        TEXT impact_level
        TEXT date_effective
        TEXT metadata_json
    }

    announcements_fts {
        TEXT title
        TEXT content
        INTEGER content_rowid FK "Links to announcements.rowid"
    }

    announcements ||--|| announcements_fts : "indexes (1:1)"
