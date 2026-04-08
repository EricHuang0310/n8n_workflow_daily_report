"""
exception_misunderstanding.py - 例外2: 機器人問題理解錯誤
============================================================
報表項目 (例外情境 項次 2):
  1. 第一次理解錯誤的筆數
  2. 連續兩次理解錯誤並轉接的筆數
  3. 客戶ID
  4. 錯誤的知識點或意圖

對應 n8n 節點:
  - ambiguity_router → negative 路徑 → save_negative_count → get_negative_count → negative_count_router
  - negative_count_router:
    - repeat_query (count==1): 第一次錯誤 → 請客戶重新說明
    - to_human (count>=2):     連續兩次 → 轉接專員
  - 另外 other_count_router 也類似:
    - repeat_query (count==1): 第一次 → 重新播放意圖
    - to_human (count>=2):     第二次 → 轉接專員
"""

from utils import (
    get_run_data,
    get_node_output,
    node_was_executed,
)


def extract(execution: dict) -> dict | None:
    """
    從單一 execution 提取「例外2: 機器人問題理解錯誤」數據。
    """
    run_data = get_run_data(execution)

    # 檢查是否走了 negative 路徑
    has_negative = node_was_executed(run_data, "save_negative_count")
    has_other = node_was_executed(run_data, "save_other_count")

    if not has_negative and not has_other:
        return None

    # negative 路徑分析
    neg_first_time = node_was_executed(run_data, "negative_response")
    neg_to_human = node_was_executed(run_data, "negative_response_to_human")

    # other 路徑分析
    other_replay = node_was_executed(run_data, "other_response")
    other_to_human = node_was_executed(run_data, "other_response_to_human")

    # 取得被誤判的意圖
    extract_output = get_node_output(run_data, "extract_intent")
    wrong_intents = extract_output.get("intent", []) if extract_output else []
    customer_id = extract_output.get("customerID") if extract_output else None
    session_id = extract_output.get("sessionID") if extract_output else None

    # 取得 negative_count
    neg_count_output = get_node_output(run_data, "get_negative_count")
    neg_count = neg_count_output.get("messagesCount") if neg_count_output else None

    # 取得 other_count
    other_count_output = get_node_output(run_data, "get_other_count")
    other_count = other_count_output.get("messagesCount") if other_count_output else None

    return {
        "exception": "機器人問題理解錯誤",
        "session_id": session_id,
        "customer_id": customer_id,
        "wrong_intents": wrong_intents,
        # negative 路徑
        "has_negative_response": has_negative,
        "negative_first_time_retry": neg_first_time and not neg_to_human,
        "negative_second_time_transfer": neg_to_human,
        "negative_count": neg_count,
        # other 路徑
        "has_other_response": has_other,
        "other_replay": other_replay and not other_to_human,
        "other_to_human": other_to_human,
        "other_count": other_count,
    }


def aggregate(records: list[dict]) -> dict:
    """彙總多筆 execution 的「例外2: 機器人問題理解錯誤」數據。"""
    valid = [r for r in records if r is not None]

    neg_first = sum(1 for r in valid if r.get("negative_first_time_retry"))
    neg_transfer = sum(1 for r in valid if r.get("negative_second_time_transfer"))
    other_first = sum(1 for r in valid if r.get("other_replay"))
    other_transfer = sum(1 for r in valid if r.get("other_to_human"))

    customer_ids = sorted(set(
        r["customer_id"] for r in valid if r.get("customer_id")
    ))

    # 統計錯誤的意圖
    wrong_intent_dist = {}
    for r in valid:
        for intent in r.get("wrong_intents", []):
            wrong_intent_dist[intent] = wrong_intent_dist.get(intent, 0) + 1

    return {
        "report_item": "例外2.機器人問題理解錯誤",
        "total_occurrences": len(valid),
        "negative_first_time_retry_count": neg_first,
        "negative_second_time_transfer_count": neg_transfer,
        "other_first_time_replay_count": other_first,
        "other_second_time_transfer_count": other_transfer,
        "wrong_intent_distribution": wrong_intent_dist,
        "customer_ids": customer_ids,
    }
