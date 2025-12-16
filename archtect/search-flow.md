graph TD
    User["User Query: '2025年4月價格相關'"] --> LLM[LLM Query Parser]
    
    LLM -->|Filters: month: '2025-04'| SearchArgs
    LLM -->|Fuzzy Query: '價格'| SearchArgs
    LLM -->|Semantic Query: 'Pricing adjustment'| SearchArgs
    
    subgraph Parallel Execution
        SearchArgs -->|Filters + Keyword| SQLite[SQLite FTS5 Search]
        SearchArgs -->|Filters + Vector| Qdrant[Qdrant Hybrid Search]
    end
    
    SQLite --> ResultA[List A: UUIDs]
    Qdrant --> ResultB[List B: UUIDs]
    
    ResultA & ResultB --> Merger[RRF Fusion & Re-ranking]
    
    Merger --> Final[Final Context]
