"""
測試腳本：比較原版與表格感知版的切分效果
"""

import sys
import os

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

from core.shared_splitter import UnifiedTokenSplitter


def generate_markdown_table(rows: int = 50, cols: int = 5) -> str:
    """生成 Markdown 表格"""
    headers = [f"欄位{i+1}" for i in range(cols)]
    header_row = "| " + " | ".join(headers) + " |"
    separator = "|" + "|".join(["---" for _ in range(cols)]) + "|"

    data_rows = []
    for i in range(rows):
        row_data = [
            f"資料{i+1}-{j+1}: 這是一些測試內容，包含中英文 Test Data"
            for j in range(cols)
        ]
        data_rows.append("| " + " | ".join(row_data) + " |")

    table = "\n".join([header_row, separator] + data_rows)
    return table


def check_table_integrity(chunks: list[str]) -> dict:
    """檢查切分後的表格完整性"""
    results = {
        "total_chunks": len(chunks),
        "broken_rows": [],
        "incomplete_tables": [],
        "warnings": [],
    }

    for idx, chunk in enumerate(chunks):
        lines = chunk.split("\n")

        # 檢查是否有不完整的表格行
        for line_num, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("|") and not stripped.endswith("|"):
                results["broken_rows"].append(
                    {"chunk_idx": idx, "line_num": line_num, "content": line[:100]}
                )

        # 檢查表格是否有標題但沒有分隔線
        has_header = False
        has_separator = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("|") and stripped.endswith("|"):
                if "---" in stripped:
                    has_separator = True
                elif not has_separator and "|" in stripped:
                    has_header = True

        if has_header and not has_separator:
            results["incomplete_tables"].append(
                {"chunk_idx": idx, "reason": "有表格標題但缺少分隔線"}
            )

        # 檢查是否在表格中間切斷
        if idx > 0:
            prev_chunk = chunks[idx - 1]
            prev_lines = prev_chunk.strip().split("\n")
            if prev_lines:
                last_line = prev_lines[-1].strip()
                first_line = lines[0].strip() if lines else ""

                if (
                    last_line.startswith("|")
                    and last_line.endswith("|")
                    and first_line.startswith("|")
                    and first_line.endswith("|")
                    and "---" not in last_line
                    and "---" not in first_line
                ):
                    results["warnings"].append(
                        {
                            "chunk_idx": idx,
                            "message": "可能在表格中間切斷",
                            "prev_line": last_line[:80],
                            "curr_line": first_line[:80],
                        }
                    )

    return results


def print_integrity_report(integrity: dict):
    """輸出完整性檢查報告"""
    print("\n" + "─" * 100)
    print("🔍 完整性檢查報告")
    print("─" * 100)

    if (
        not integrity["broken_rows"]
        and not integrity["incomplete_tables"]
        and not integrity["warnings"]
    ):
        print("✅ 完美！沒有發現任何問題")
        print("   - 所有表格行都完整")
        print("   - 沒有在 row 中間切斷")
        print("   - 表格結構完整")
    else:
        if integrity["broken_rows"]:
            print(f"\n❌ 發現 {len(integrity['broken_rows'])} 個破損的表格行:")
            for item in integrity["broken_rows"][:5]:
                print(
                    f"   - Chunk {item['chunk_idx']}, Line {item['line_num']}: {item['content']}"
                )

        if integrity["incomplete_tables"]:
            print(f"\n⚠️  發現 {len(integrity['incomplete_tables'])} 個不完整的表格:")
            for item in integrity["incomplete_tables"]:
                print(f"   - Chunk {item['chunk_idx']}: {item['reason']}")

        if integrity["warnings"]:
            print(f"\n⚠️  發現 {len(integrity['warnings'])} 個警告:")
            for item in integrity["warnings"][:5]:
                print(f"   - Chunk {item['chunk_idx']}: {item['message']}")


def test_comparison():
    """比較原版與表格感知版"""
    print("=" * 100)
    print("🧪 表格切分對比測試：原版 vs 表格感知版")
    print("=" * 100)

    # 測試中型表格
    print("\n" + "=" * 100)
    print("📝 測試案例: 中型表格 (50 rows, 5 cols)")
    print("=" * 100)

    table = generate_markdown_table(rows=50, cols=5)
    splitter = UnifiedTokenSplitter(
        chunk_size=1000, overlap=100, debug=False, table_aware=True
    )

    print(f"\n原始表格長度: {len(table)} 字元")
    print(f"Token 數: {splitter.count_tokens(table)}")

    # 測試原版
    print("\n" + "=" * 100)
    print("📊 原版 split_text_optimized")
    print("=" * 100)
    chunks_original = splitter.split_text_optimized(table)
    print(f"切分結果: {len(chunks_original)} 段")
    integrity_original = check_table_integrity(chunks_original)
    print_integrity_report(integrity_original)

    if len(chunks_original) > 1:
        print("\n📋 切分範例 (Chunk 1 結尾 → Chunk 2 開頭):")
        print("\n--- Chunk 1 最後 3 行 ---")
        for line in chunks_original[0].split("\n")[-3:]:
            print(f"  {line[:100]}")
        print("\n--- Chunk 2 前 3 行 ---")
        for line in chunks_original[1].split("\n")[:3]:
            print(f"  {line[:100]}")

    # 測試表格感知版
    print("\n" + "=" * 100)
    print("📊 表格感知版 split_text_table_aware")
    print("=" * 100)
    chunks_table_aware = splitter.split_text_table_aware(table)
    print(f"切分結果: {len(chunks_table_aware)} 段")
    integrity_table_aware = check_table_integrity(chunks_table_aware)
    print_integrity_report(integrity_table_aware)

    if len(chunks_table_aware) > 1:
        print("\n📋 切分範例 (Chunk 1 結尾 → Chunk 2 開頭):")
        print("\n--- Chunk 1 最後 3 行 ---")
        for line in chunks_table_aware[0].split("\n")[-3:]:
            print(f"  {line[:100]}")
        print("\n--- Chunk 2 前 3 行 ---")
        for line in chunks_table_aware[1].split("\n")[:3]:
            print(f"  {line[:100]}")

    # 對比總結
    print("\n" + "=" * 100)
    print("📊 對比總結")
    print("=" * 100)

    print(f"\n原版:")
    print(f"  - 切分段數: {len(chunks_original)}")
    print(f"  - 破損行數: {len(integrity_original['broken_rows'])}")
    print(f"  - 不完整表格: {len(integrity_original['incomplete_tables'])}")
    print(f"  - 警告數: {len(integrity_original['warnings'])}")

    print(f"\n表格感知版:")
    print(f"  - 切分段數: {len(chunks_table_aware)}")
    print(f"  - 破損行數: {len(integrity_table_aware['broken_rows'])}")
    print(f"  - 不完整表格: {len(integrity_table_aware['incomplete_tables'])}")
    print(f"  - 警告數: {len(integrity_table_aware['warnings'])}")

    # 判斷改進效果
    if len(integrity_table_aware["broken_rows"]) < len(
        integrity_original["broken_rows"]
    ) or len(integrity_table_aware["warnings"]) < len(integrity_original["warnings"]):
        print("\n✅ 表格感知版有明顯改進！")
    elif (
        len(integrity_table_aware["broken_rows"]) == 0
        and len(integrity_table_aware["warnings"]) == 0
    ):
        print("\n✅ 表格感知版完美處理表格切分！")
    else:
        print("\n⚠️  兩個版本效果相近")


if __name__ == "__main__":
    test_comparison()

    print("\n" + "=" * 100)
    print("✅ 測試完成")
    print("=" * 100)
