# 1. 使用 Python 3.12 官方輕量化版本
FROM python:3.12-slim

# 2. 設定環境變數，確保日誌能即時輸出，且不產生編譯檔
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# 3. 安裝系統必備組件 (編譯套件與 Playwright 所需)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 4. 設定容器內的工作目錄
WORKDIR /app

# 5. 先複製相依套件清單並安裝 (利用快取機制優化重複構建速度)
# 注意：這裡請確保你的 requirements.txt 已經是 UTF-8 編碼
COPY data_update/requirements.txt ./data_update/requirements.txt

# 6. 安裝 Python 套件
# 由於包含 torch 與 sentence-transformers，這步會花比較多時間
RUN pip install --no-cache-dir -r data_update/requirements.txt

# 7. 安裝 Playwright 瀏覽器及其必要的系統依賴 (爬蟲需要)
RUN playwright install --with-deps chromium

# 8. 複製整個專案目錄到容器中
COPY . .

# 9. 關鍵：設定工作路徑到 data_update
# 這樣 main_scheduler.py 才能正確載入同級目錄下的 crawlers 與 core 模組
WORKDIR /app/data_update

# 10. 啟動主排程程式
CMD ["python", "main_scheduler.py"]