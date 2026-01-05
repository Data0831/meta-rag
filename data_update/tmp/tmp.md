1. 任務重述
針對您的需求，我整理目前的理解如下：

資料特性：data.json 是「每日增量」，大約 100 筆資料。
ID 機制：
id
 = hash(link + title + content)。這意味著只要內容變動，ID 就會變。
環境限制：虛擬機記憶體 3GB，向量計算（Embedding）主要在本地 GPU 完成後上傳，或是每日增量時在虛擬機跑（100 筆左右）。
現有機制：已有 remove.json 處理刪除，且 
add_new_documents
 會先查 ID 是否存在，不存在才計算向量。