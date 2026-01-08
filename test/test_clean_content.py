import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data_update.parser import DataParser


def print_separator():
    print("\n" + "=" * 80 + "\n")


def test_case(name: str, input_text: str, expected_keywords: list = None):
    print(f"Test Case: {name}")
    print("-" * 80)
    print("Input:")
    print(input_text)
    print("\n" + "-" * 40)

    parser = DataParser([], "")
    result = parser.clean_content(input_text)

    print("Output:")
    print(result)
    print("-" * 40)
    print(f"Length: {len(input_text)} -> {len(result)}")

    if expected_keywords:
        print("\nExpected keywords present:")
        for keyword in expected_keywords:
            status = "✓" if keyword in result else "✗"
            print(f"  {status} '{keyword}'")

    print_separator()
    return result


def main():
    print("=" * 80)
    print("Clean Content Function Test Suite")
    print("=" * 80)

    test_case(
        "1. Basic Markdown Headers",
        """# 主標題
## 次標題
### 三級標題

這是內容段落。""",
        expected_keywords=["主標題", "次標題", "三級標題", "內容段落"]
    )

    test_case(
        "2. Bold and Italic Text",
        """這是 **粗體文字** 和 *斜體文字*。
還有 __另一種粗體__ 和 _另一種斜體_。
甚至 ***粗斜體*** 也要處理。""",
        expected_keywords=["粗體文字", "斜體文字", "另一種粗體", "另一種斜體", "粗斜體"]
    )

    test_case(
        "3. Inline Code and Code Blocks",
        """使用 `pip install package` 來安裝套件。

```python
def hello():
    print("Hello World")
```

這是後續說明。""",
        expected_keywords=["pip install package", "def hello", "print", "Hello World", "後續說明"]
    )

    test_case(
        "4. Links and URLs",
        """請參考 [Microsoft 文件](https://docs.microsoft.com) 取得更多資訊。
直接連結：https://example.com/page
另一個連結 https://test.com 在句中。""",
        expected_keywords=["Microsoft 文件", "參考", "取得更多資訊"]
    )

    test_case(
        "5. Images",
        """說明文字開始。
![替代文字](https://example.com/image.png)
![另一張圖](image.jpg)
說明文字結束。""",
        expected_keywords=["說明文字開始", "說明文字結束"]
    )

    test_case(
        "6. Tables",
        """功能比較表：

| 功能 | 版本 A | 版本 B |
|------|--------|--------|
| 功能1 | 支援 | 不支援 |
| 功能2 | 部分支援 | 完整支援 |

以上是表格內容。""",
        expected_keywords=["功能", "版本 A", "版本 B", "功能1", "支援", "不支援", "功能2"]
    )

    test_case(
        "7. Horizontal Lines",
        """第一段內容。

---

第二段內容。

***

第三段內容。""",
        expected_keywords=["第一段內容", "第二段內容", "第三段內容"]
    )

    test_case(
        "8. Metadata Fields (Project Specific)",
        """* **日期**：2024-01-15
* **工作區**：Microsoft 365
* **受影響的群體**：所有使用者

這是實際內容開始。""",
        expected_keywords=["實際內容開始"]
    )

    test_case(
        "9. Template Headers (Project Specific)",
        """#### 現已推出
新功能已經發布。

#### 即將到來的事項
即將推出的功能。

##### 提醒
請注意這個變更。""",
        expected_keywords=["新功能已經發布", "即將推出的功能", "請注意這個變更"]
    )

    test_case(
        "10. Complex Real-World Example",
        """# Microsoft 365 訊息中心更新

* **日期**：2024-01-06
* **工作區**：Teams
* **受影響的群體**：管理員

## 摘要

Microsoft Teams 將推出 **新的會議功能**，包括：

1. 即時字幕改進
2. 背景模糊增強
3. 支援 `@mention` 通知

### 現已推出

您可以在 [管理中心](https://admin.microsoft.com) 啟用此功能。

詳細技術規格：

| 項目 | 規格 |
|------|------|
| 最大參與者 | 1000 人 |
| 錄影時長 | 4 小時 |

### 後續步驟

請執行以下命令：

```powershell
Set-TeamsMeetingPolicy -AllowTranscription $true
```

更多資訊請參考：https://docs.microsoft.com/teams

---

![功能截圖](https://example.com/screenshot.png)

#### 提醒

記得通知使用者。""",
        expected_keywords=[
            "Microsoft 365 訊息中心更新",
            "Teams",
            "新的會議功能",
            "即時字幕改進",
            "背景模糊增強",
            "@mention",
            "管理中心",
            "最大參與者",
            "1000 人",
            "Set-TeamsMeetingPolicy",
            "記得通知使用者"
        ]
    )

    test_case(
        "11. Newline and Whitespace Handling",
        """段落一


段落二



段落三

      多餘空白      測試

段落四""",
        expected_keywords=["段落一", "段落二", "段落三", "多餘空白", "測試", "段落四"]
    )

    test_case(
        "12. Mixed Chinese and English with Technical Terms",
        """使用 **Power BI** 進行資料分析。

支援的檔案格式：
- Excel (.xlsx)
- CSV (.csv)
- JSON

連接字串範例：`Server=myserver;Database=mydb`

詳見文件：https://powerbi.microsoft.com/documentation""",
        expected_keywords=["Power BI", "資料分析", "Excel", "CSV", "JSON", "Server=myserver"]
    )

    print("\n" + "=" * 80)
    print("All tests completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
