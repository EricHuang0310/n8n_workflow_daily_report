"""
exception_transfer_agent.py - 例外1: 客戶直接說明轉專員
=========================================================
報表項目 (例外情境 項次 1):
  1. 第一次說明轉專員的筆數
  2. 第二次說明轉專員並轉接的筆數
  3. 客戶ID

對應 n8n 節點判斷邏輯:
  - intent_identification 辨識出「轉接專員」相關意圖
  - 若走了 negative_response → repeat_query_response 路徑 (第一次提醒)
  - 若走了 negative_response_to_human 路徑 (第二次 → 轉接)

  另外也對應 negative_count_router:
    - repeat_query (messagesCount == 1) → 第一次
    - to_human (messagesCount >= 2)     → 第二次轉人工
"""

from utils import (
    get_run_data,
    get_node_output,
    node_was_executed,
)

# 與「轉接專員」相關的意圖關鍵字
TRANSFER_KEYWORDS = ["轉接", "專員", "真人", "客服人員", "轉人工"]


def _intent_is_transfer(intents: list[str]) -> bool:
    """判斷意圖列表中是否含有轉接專員相關意圖。"""
    for intent in intents:
        for kw in TRANSFER_KEYWORDS:
            if kw in intent:
                return True
    return False


def extract(execution: dict) -> dict | None:
    """
    從單一 execution 提取「例外1: 客戶直接說明轉專員」數據。
    """
    run_data = get_run_data(execution)

    # 方法1: 檢查 negative_count_router 是否被執行 (客戶否定確認後的計數路由)
    went_negative_first = node_was_executed(run_data, "negative_response")
    went_negative_to_human = node_was_executed(run_data, "negative_response_to_human")

    # 方法2: 檢查 error_to_human 節點 (節點 ERROR 走轉人工)
    went_error_to_human = node_was_executed(run_data, "error_to_human")

    # 方法3: 檢查意圖是否為「轉接專員」
    intent_output = get_node_output(run_data, "intent_identification")
    intents = []
    if intent_output:
        intents = [
            item.get("intent", "")
            for item in intent_output.get("output", [])
        ]
    is_transfer_intent = _intent_is_transfer(intents)

    # 若都不符合，非此例外情境
    if not went_negative_first and not went_negative_to_human and not is_transfer_intent:
        return None

    # 取得客戶 ID
    extract_output = get_node_output(run_data, "extract_intent")
    customer_id = extract_output.get("customerID") if extract_output else None
    session_id = extract_output.get("sessionID") if extract_output else None

    return {
        "exception": "客戶直接說明轉專員",
        "session_id": session_id,
        "customer_id": customer_id,
        "is_transfer_intent": is_transfer_intent,
        "intents": intents,
        "first_time_redirect": went_negative_first and not went_negative_to_human,
        "second_time_transferred": went_negative_to_human,
    }


def aggregate(records: list[dict]) -> dict:
    """彙總多筆 execution 的「例外1: 客戶直接說明轉專員」數據。"""
    valid = [r for r in records if r is not None]

    first_time = sum(1 for r in valid if r.get("first_time_redirect"))
    second_time = sum(1 for r in valid if r.get("second_time_transferred"))
    transfer_intents = sum(1 for r in valid if r.get("is_transfer_intent"))
    customer_ids = sorted(set(
        r["customer_id"] for r in valid if r.get("customer_id")
    ))

    return {
        "report_item": "例外1.客戶直接說明轉專員",
        "total_occurrences": len(valid),
        "first_time_redirect_count": first_time,
        "second_time_transfer_count": second_time,
        "transfer_intent_detected_count": transfer_intents,
        "customer_ids": customer_ids,
    }
