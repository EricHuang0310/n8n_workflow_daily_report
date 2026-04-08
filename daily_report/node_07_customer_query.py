"""
node_07_customer_query.py - 7.說出問題
==========================================
報表項目 (項次 3):
  1. 進入此節點之數量
  2. 客戶停留時間
  3. 客戶口述的問題
  4. 客戶ID (用於24小時再進線追蹤)

對應 n8n 節點: receive_message_API
"""

from utils import (
    get_run_data,
    get_node_output,
    get_node_execution_time,
    node_was_executed,
    calc_node_duration_seconds,
)


def extract(execution: dict) -> dict | None:
    """
    從單一 execution 提取「7.說出問題」節點數據。
    回傳 dict 或 None (若此節點未被觸發)。
    """
    run_data = get_run_data(execution)

    if not node_was_executed(run_data, "receive_message_API"):
        return None

    webhook_output = get_node_output(run_data, "receive_message_API")
    if not webhook_output:
        return None

    body = webhook_output.get("body", {})

    # 停留時間: 從 receive_message_API 到 intent_identification (客戶在此節點的逗留)
    stay_duration_sec = calc_node_duration_seconds(
        run_data, "receive_message_API", "intent_identification"
    )

    return {
        "node": "7.說出問題",
        "entered": True,
        "customer_text": body.get("text"),
        "customer_id": body.get("customerID"),
        "session_id": body.get("sessionID"),
        "stay_duration_sec": stay_duration_sec,
        "execution_time_ms": get_node_execution_time(run_data, "receive_message_API"),
    }


def aggregate(records: list[dict]) -> dict:
    """
    彙總多筆 execution 的「7.說出問題」數據為日報表。
    """
    valid = [r for r in records if r is not None]

    customer_queries = []
    customer_ids = set()
    total_stay_sec = 0.0
    stay_count = 0

    for r in valid:
        if r.get("customer_text"):
            customer_queries.append({
                "session_id": r["session_id"],
                "customer_id": r["customer_id"],
                "text": r["customer_text"],
            })
        if r.get("customer_id"):
            customer_ids.add(r["customer_id"])
        if r.get("stay_duration_sec") is not None:
            total_stay_sec += r["stay_duration_sec"]
            stay_count += 1

    return {
        "report_item": "7.說出問題",
        "total_count": len(valid),
        "avg_stay_duration_sec": round(total_stay_sec / stay_count, 3) if stay_count else None,
        "unique_customer_count": len(customer_ids),
        "customer_queries": customer_queries,
        "customer_ids": sorted(customer_ids),
    }
