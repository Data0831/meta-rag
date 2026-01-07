"""
測試腳本：驗證表格切分是否能保持完整性（不在 row 中間切斷）
"""

from shared_splitter import UnifiedTokenSplitter


def generate_markdown_table(rows: int = 50, cols: int = 5) -> str:
    """生成 Markdown 表格"""
    # 表格標題
    headers = [f"欄位{i+1}" for i in range(cols)]
    header_row = "| " + " | ".join(headers) + " |"
    separator = "|" + "|".join(["---" for _ in range(cols)]) + "|"

    # 表格內容
    data_rows = []
    for i in range(rows):
        row_data = [
            f"資料{i+1}-{j+1}: 這是一些測試內容，包含中英文 Test Data"
            for j in range(cols)
        ]
        data_rows.append("| " + " | ".join(row_data) + " |")

    # 組合完整表格
    table = "\n".join([header_row, separator] + data_rows)
    return table


def generate_complex_table() -> str:
    """生成複雜的真實場景表格"""
    table = """
# Azure 服務更新列表

以下是最新的 Azure 服務更新資訊：

| 服務名稱 | 更新日期 | 更新類型 | 描述 | 影響範圍 | 狀態 |
|---------|---------|---------|------|---------|------|
| Azure Virtual Machines | 2024-01-15 | Feature | 新增 D-series v5 虛擬機器系列，提供更高的運算效能和記憶體容量。支援最新的 Intel Xeon 處理器。 | 全球所有區域 | 正式發布 |
| Azure SQL Database | 2024-01-14 | Performance | 優化查詢引擎，提升複雜查詢效能達 30%。新增智慧查詢處理功能。 | 所有定價層 | 正式發布 |
| Azure Kubernetes Service | 2024-01-13 | Security | 加強網路安全政策，支援 Azure Policy for AKS。新增 Pod Security Standards 整合。 | 所有 AKS 叢集 | 預覽版 |
| Azure Functions | 2024-01-12 | Feature | 支援 Python 3.11 執行環境，提升執行效能。新增更多內建綁定選項。 | 所有區域 | 正式發布 |
| Azure Cosmos DB | 2024-01-11 | Performance | 新增 serverless 模式的自動擴展功能，降低成本達 40%。優化分區策略建議工具。 | NoSQL API | 正式發布 |
| Azure Monitor | 2024-01-10 | Feature | 新增 Application Insights 的分散式追蹤視覺化工具。支援更細緻的效能分析。 | 所有訂閱 | 預覽版 |
| Azure Storage | 2024-01-09 | Feature | Blob Storage 新增不可變儲存體政策，符合法規遵循需求。支援 WORM (Write Once Read Many) 模式。 | 所有儲存體帳戶 | 正式發布 |
| Azure DevOps | 2024-01-08 | Feature | Pipeline 新增 YAML 範本市集，提供預建的 CI/CD 範本。加速開發流程。 | 所有專案 | 正式發布 |
| Azure AI Services | 2024-01-07 | Feature | Computer Vision API 新增物件偵測 v4.0，準確度提升 25%。支援更多物件類別。 | 所有區域 | 預覽版 |
| Azure App Service | 2024-01-06 | Performance | Linux App Service 啟動時間優化，冷啟動時間減少 50%。改善容器映像快取機制。 | Linux 方案 | 正式發布 |
| Azure Virtual Network | 2024-01-05 | Security | 新增 DDoS Protection 進階功能，提供即時攻擊分析和自動緩解。 | 標準層以上 | 正式發布 |
| Azure Synapse Analytics | 2024-01-04 | Feature | 新增 Spark 3.4 支援，提升大數據處理效能。整合更多機器學習函式庫。 | 所有工作區 | 預覽版 |
| Azure Key Vault | 2024-01-03 | Security | 支援 HSM 支援的金鑰輪替自動化。加強金鑰管理安全性。 | Premium 層 | 正式發布 |
| Azure Logic Apps | 2024-01-02 | Feature | 新增 500+ 個連接器，支援更多第三方服務整合。簡化工作流程建立。 | 所有方案 | 正式發布 |
| Azure Container Registry | 2024-01-01 | Feature | 支援 OCI Artifacts，可儲存 Helm charts、CNAB bundles 等。擴展儲存體類型。 | 所有層級 | 正式發布 |
| Azure Front Door | 2023-12-31 | Performance | 全球 CDN 節點擴充至 150+ 個位置，降低延遲達 35%。優化路由演算法。 | 所有設定檔 | 正式發布 |
| Azure Cognitive Search | 2023-12-30 | Feature | 新增向量搜尋功能，支援語意搜尋和 AI 增強查詢。整合 OpenAI embeddings。 | 標準層以上 | 預覽版 |
| Azure Data Factory | 2023-12-29 | Feature | 新增 Mapping Data Flow 的偵錯模式改進，加速開發除錯流程。 | 所有訂閱 | 正式發布 |
| Azure Backup | 2023-12-28 | Feature | 支援 Azure VM 的應用程式一致性備份，確保資料完整性。新增多區域備份選項。 | 所有區域 | 正式發布 |
| Azure Sentinel | 2023-12-27 | Security | 新增 SOAR (Security Orchestration, Automation and Response) 劇本範本。加速事件回應。 | 所有工作區 | 正式發布 |

## 重要注意事項

上述更新可能需要您調整現有的設定或程式碼。建議在生產環境部署前，先在測試環境中驗證。
"""
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

        # 檢查是否有不完整的表格行（以 | 開頭但不以 | 結尾）
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

        # 檢查是否在表格中間切斷（前一個 chunk 以表格行結尾，但沒有結束標記）
        if idx > 0:
            prev_chunk = chunks[idx - 1]
            prev_lines = prev_chunk.strip().split("\n")
            if prev_lines:
                last_line = prev_lines[-1].strip()
                first_line = lines[0].strip() if lines else ""

                # 如果前一段最後一行是表格行，且當前段第一行也是表格行
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


def test_table_splitting():
    """測試表格切分"""
    print("=" * 100)
    print("🧪 Markdown 表格切分完整性測試")
    print("=" * 100)

    # 測試案例 1: 小型表格
    print("\n" + "=" * 100)
    print("📝 測試案例 1: 小型表格 (10 rows)")
    print("=" * 100)

    small_table = generate_markdown_table(rows=10, cols=5)
    splitter = UnifiedTokenSplitter(chunk_size=500, overlap=50, debug=False)

    print(f"\n原始表格長度: {len(small_table)} 字元")
    print(f"Token 數: {splitter.count_tokens(small_table)}")

    chunks = splitter.split_text_optimized(small_table)
    print(f"\n切分結果: {len(chunks)} 段")

    integrity = check_table_integrity(chunks)
    print_integrity_report(integrity)

    # 測試案例 2: 中型表格
    print("\n" + "=" * 100)
    print("📝 測試案例 2: 中型表格 (50 rows)")
    print("=" * 100)

    medium_table = generate_markdown_table(rows=50, cols=5)
    splitter = UnifiedTokenSplitter(chunk_size=1000, overlap=100, debug=False)

    print(f"\n原始表格長度: {len(medium_table)} 字元")
    print(f"Token 數: {splitter.count_tokens(medium_table)}")

    chunks = splitter.split_text_optimized(medium_table)
    print(f"\n切分結果: {len(chunks)} 段")

    integrity = check_table_integrity(chunks)
    print_integrity_report(integrity)

    # 顯示切分範例
    if len(chunks) > 1:
        print("\n📋 切分範例 (前兩段的交界處):")
        print("\n--- Chunk 1 結尾 ---")
        print(chunks[0].split("\n")[-3:])
        print("\n--- Chunk 2 開頭 ---")
        print(chunks[1].split("\n")[:3])

    # 測試案例 3: 真實場景表格
    print("\n" + "=" * 100)
    print("📝 測試案例 3: 真實場景複雜表格 (Azure 更新列表)")
    print("=" * 100)

    complex_table = generate_complex_table()
    splitter = UnifiedTokenSplitter(chunk_size=1500, overlap=300, debug=False)

    print(f"\n原始文本長度: {len(complex_table)} 字元")
    print(f"Token 數: {splitter.count_tokens(complex_table)}")

    chunks = splitter.split_text_optimized(complex_table)
    print(f"\n切分結果: {len(chunks)} 段")

    integrity = check_table_integrity(chunks)
    print_integrity_report(integrity)

    # 顯示每一段的內容摘要
    print("\n📊 各段內容摘要:")
    for idx, chunk in enumerate(chunks):
        lines = chunk.split("\n")
        table_rows = [
            l for l in lines if l.strip().startswith("|") and l.strip().endswith("|")
        ]
        print(f"\n  Chunk {idx + 1}:")
        print(f"    - 總行數: {len(lines)}")
        print(f"    - 表格行數: {len(table_rows)}")
        print(f"    - Token 數: {splitter.count_tokens(chunk)}")
        if table_rows:
            print(f"    - 第一個表格行: {table_rows[0][:80]}...")
            print(f"    - 最後一個表格行: {table_rows[-1][:80]}...")


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
            for item in integrity["broken_rows"][:5]:  # 只顯示前 5 個
                print(
                    f"   - Chunk {item['chunk_idx']}, Line {item['line_num']}: {item['content']}"
                )

        if integrity["incomplete_tables"]:
            print(f"\n⚠️  發現 {len(integrity['incomplete_tables'])} 個不完整的表格:")
            for item in integrity["incomplete_tables"]:
                print(f"   - Chunk {item['chunk_idx']}: {item['reason']}")

        if integrity["warnings"]:
            print(f"\n⚠️  發現 {len(integrity['warnings'])} 個警告:")
            for item in integrity["warnings"][:5]:  # 只顯示前 5 個
                print(f"   - Chunk {item['chunk_idx']}: {item['message']}")
                print(f"     前段最後: {item['prev_line']}")
                print(f"     當前開頭: {item['curr_line']}")


if __name__ == "__main__":
    test_table_splitting()

    print("\n" + "=" * 100)
    print("✅ 測試完成")
    print("=" * 100)
