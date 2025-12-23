import json
import os

# --- 使用者設定 ---
# 輸入的 JSON 檔案名稱
INPUT_JSON_FILE = "data/m365_roadmap_flat.json"
# 輸出的 JSON 檔案名稱
OUTPUT_JSON_FILE = "data/test.json"
# ------------------


def process_json():
    # 檢查檔案是否存在
    if not os.path.exists(INPUT_JSON_FILE):
        print(f"錯誤: 找不到輸入檔案 '{INPUT_JSON_FILE}'")
        return

    try:
        print(f"正在讀取 {INPUT_JSON_FILE} ...")
        with open(INPUT_JSON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            print("錯誤: JSON 內容不是一個 list")
            return

        processed_count = 0
        for item in data:
            if isinstance(item, dict) and "content" in item:
                content_val = item["content"]
                # 檢查 content 是否為 list，且內容為字串
                if isinstance(content_val, list):
                    # 將 list 中的所有 string 串接起來
                    # 使用 empty string join，如果需要換行可以用 "\n".join()
                    # 根據需求 "concate 所有"，這裡直接串接
                    concatenated_content = "".join([str(s) for s in content_val])
                    item["content"] = concatenated_content
                    processed_count += 1
                elif isinstance(content_val, str):
                    # 已經是字串則不處理
                    pass

        print(f"處理完成，共修改了 {processed_count} 筆資料。")
        print(f"正在寫入 {OUTPUT_JSON_FILE} ...")

        with open(OUTPUT_JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print("成功！")

    except json.JSONDecodeError:
        print(f"錯誤: '{INPUT_JSON_FILE}' 不是有效的 JSON 格式")
    except Exception as e:
        print(f"發生未預期的錯誤: {e}")


if __name__ == "__main__":
    process_json()
