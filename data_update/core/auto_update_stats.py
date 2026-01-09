import json
import os
import glob
import requests
from datetime import datetime

# ================= 配置設定 =================
# 1. Azure 伺服器設定
SERVER_URL = "https://msans-a2a2ckanfuh4dtdv.japaneast-01.azurewebsites.net/api/admin/update-json/website"
ADMIN_TOKEN = "msanmsan001"

# 2. 本地路徑設定 (假設腳本在 data_update/core/)
# 取得 main_scheduler.py 所在的 data_update 目錄
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 

# 指向 data_update/sync_output
SYNC_FOLDER = os.path.join(BASE_DIR, "sync_output")

# 指向專案根目錄下的 src/datas/website.json
LOCAL_WEBSITE_JSON = os.path.join(BASE_DIR, "..", "src", "datas", "website.json")
##若是未來爬蟲獨立出來，此路經需更改並另外建立website.json檔案

def get_latest_upsert_file():
    """尋找最新產生的 upsert_*.json"""
    files = glob.glob(os.path.join(SYNC_FOLDER, 'upsert_*.json'))
    if not files:
        return None
    return max(files, key=os.path.getctime)

def run_update():
    # A. 取得最新更新檔
    latest_file = get_latest_upsert_file()
    if not latest_file:
        print("[-] 找不到 upsert JSON 檔案，取消更新。")
        return

    print(f"[*] 處理今日更新檔案: {os.path.basename(latest_file)}")

    with open(latest_file, 'r', encoding='utf-8') as f:
        daily_items = json.load(f)

    # B. 統計篇數 (使用 link 去重)
    # stats 結構為 { "website_name": {set_of_links} }
    stats = {}
    for item in daily_items:
        site_name = item.get('website')
        link = item.get('link')
        if site_name and link:
            if site_name not in stats:
                stats[site_name] = set()
            stats[site_name].add(link)

    # C. 讀取本地 website.json 作為更新基底
    if not os.path.exists(LOCAL_WEBSITE_JSON):
        print(f"[-] 找不到本地 website.json: {LOCAL_WEBSITE_JSON}")
        return

    with open(LOCAL_WEBSITE_JSON, 'r', encoding='utf-8') as f:
        website_list = json.load(f)

    # 生成日期格式 (例如 2026-1-8)
    now = datetime.now()
    today_str = f"{now.year}-{now.month}-{now.day}"
    
    updated_any = False

    # D. 直接比對 website 名稱並更新內容
    for site_info in website_list:
        site_name = site_info.get('website')
        
        # 如果這個網站在今日更新清單中
        if site_name in stats:
            count = len(stats[site_name])
            if count > 0:
                site_info['update_date'] = today_str
                site_info['update_count'] = str(count)
                print(f"[+] 更新 {site_name}: {count} 篇 (日期: {today_str})")
                updated_any = True

    if not updated_any:
        print("[!] 今日無新文章對應到現有網站清單。")
        return

    # E. 發布到 Azure 伺服器
    print("[*] 正在同步資料到 Azure...")
    headers = {
        "Content-Type": "application/json",
        "X-Admin-Token": ADMIN_TOKEN
    }
    
    try:
        response = requests.post(SERVER_URL, json=website_list, headers=headers, timeout=30)
        if response.status_code == 200:
            print("[OK] Azure 上的公告資料已同步更新！")
            
            # 同步更新本地檔案，確保下次執行時基底是最新的
            with open(LOCAL_WEBSITE_JSON, 'w', encoding='utf-8') as f:
                json.dump(website_list, f, ensure_ascii=False, indent=4)
        else:
            print(f"[Fail] 上傳失敗 ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"[Error] 連線異常: {e}")

if __name__ == "__main__":
    run_update()