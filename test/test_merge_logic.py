from src.services.search_service import SearchService
from src.agents.srhSumAgent import SrhSumAgent


def test_merging_logic():
    print("=== 開始測試合併邏輯 ===\n")

    # 1. 模擬 SearchService 的單次搜尋合併
    ss = SearchService()
    round1_raw_hits = [
        {
            "id": "id1",
            "link": "https://example.com/page1",
            "content": "這是區塊1",
            "_rankingScore": 0.9,
        },
        {
            "id": "id2",
            "link": "https://example.com/page1",
            "content": "這是區塊2",
            "_rankingScore": 0.8,
        },
        {
            "id": "id3",
            "link": "https://example.com/page2",
            "content": "這是另一個網頁",
            "_rankingScore": 0.7,
        },
    ]

    print("[測試 1] SearchService 單次合併")
    ss_merged = ss._merge_duplicate_links(round1_raw_hits)
    print(f"原始筆數: {len(round1_raw_hits)} -> 合併後筆數: {len(ss_merged)}")
    for doc in ss_merged:
        print(
            f" - Link: {doc['link']}, IDs: {doc['all_ids']}, Content Length: {len(doc['content'])}"
        )

    assert len(ss_merged) == 2, "應該合併為兩筆結果"
    assert (
        "id1" in ss_merged[0]["all_ids"] and "id2" in ss_merged[0]["all_ids"]
    ), "ID 應該被合併到列表中"
    print("OK: SearchService 合併成功\n")

    # 2. 模擬 SrhSumAgent 的跨回合合併
    agent = SrhSumAgent()
    collected_results = {}
    all_seen_ids = set()

    print("[測試 2] SrhSumAgent 跨回合合併 (Round 1)")
    agent._add_results(collected_results, all_seen_ids, ss_merged)
    print(f"Round 1 後收集數量: {len(collected_results)}")

    # 模擬第二輪搜尋抓到了同網址的新 ID (例如 id4)
    round2_results = [
        {
            "id": "id4",
            "link": "https://example.com/page1",
            "content": "這是區塊4 (新發現)",
            "_rankingScore": 0.95,
            "all_ids": ["id4"],
        }
    ]

    print("[測試 3] SrhSumAgent 跨回合合併 (Round 2)")
    agent._add_results(collected_results, all_seen_ids, round2_results)

    # 最終驗證
    final_docs = list(collected_results.values())
    print(f"最終收集總筆數: {len(final_docs)}")

    target_doc = next(d for d in final_docs if d["link"] == "https://example.com/page1")
    print(f"網址1的最終 ID 列表: {target_doc['all_ids']}")
    print(f"網址1的最終內容:\n{target_doc['content']}")
    print(f"已記錄的所有 ID (用於 exclude): {all_seen_ids}")

    assert len(final_docs) == 2, "最終網址數量應該仍為 2"
    assert "id4" in target_doc["all_ids"], "新 ID 應該被加入列表"
    assert "---" in target_doc["content"], "內容應該被分隔符拼接"
    assert (
        "id1" in all_seen_ids and "id4" in all_seen_ids
    ), "所有 ID 都應該被追蹤以供去重"

    print("\n=== 測試全部通過！去重與合併邏輯正確運作 ===")


if __name__ == "__main__":
    try:
        test_merging_logic()
    except Exception as e:
        print(f"測試失敗: {e}")
        import traceback

        traceback.print_exc()
