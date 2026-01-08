erDiagram
    AnnouncementDoc {
        string id PK "唯一識別碼 (MD5)"
        string link "原始連結"
        string year_month "過濾鍵 (YYYY-MM)"
        string title "公告標題"
        string cleaned_content "優化後的搜尋內文"
        string website "來源類別"
        int token "對應 Token 數"
        string update_time "最後更新時間"
    }

    SearchIntent {
        string keyword_query "關鍵字檢索詞 (FTS)"
        string semantic_query "語意檢索詞 (Vector)"
        string_list year_month "時間範圍過濾"
        string_list websites "站點來源過濾"
        string_list must_have_keywords "強制匹配詞"
        string_list sub_queries "並行搜尋子查詢"
        float recommended_semantic_ratio "建議向量權重"
        int limit "結果數量限制"
    }