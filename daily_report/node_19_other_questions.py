"""
node_19_other_questions.py - 19.是否有其他問題
=================================================
報表項目 (項次 14):
  1. 進入此節點之數量
  2. 客戶停留時間
  3. 客戶沒有其他問題的筆數
  4. 客戶有其他信用卡問題的筆數
  5. 客戶有銀行 / 其他類型問題的筆數
  6. 客戶選擇轉接專員的筆數 (新增)

對應 n8n 節點 (v0.0.1):
  路徑 A: 客戶接收 SMS 後  → Message → other_send_question → return_other_question
  路徑 B: 客戶不接收 SMS    → other_question → return_other_question
  共同接續: save_message1 → receive_other_question → save_other_question
            → other_question_classifier (5 類)

  other_question_classifier 五個分支:
    0 crediction → other_query → query → save_query → intent_identification
                  (客戶說出新的信用卡相關問題, 回到主流程辨識)
    1 transfer   → response_to_human1 (轉接專員)
    2 yes        → wait_intent (客戶說有問題但沒講內容, 請其再說一次)
    3 no         → end_call    (沒有其他問題, 結束服務)
    4 other      → retuen_mean → return_end (語意不明)
"""

from utils import (
    get_run_data,
    get_node_output,
    get_node_execution_time,
    node_was_executed,
    calc_node_duration_seconds,
)


def _classifier_label(run_data: dict) -> str | None:
    """
    透過 other_question_classifier 後續節點是否觸發，推斷分類結果。
    回傳: 'crediction' / 'transfer' / 'yes' / 'no' / 'other' / None
    """
    if not node_was_executed(run_data, "other_question_classifier"):
        return None
    if node_was_executed(run_data, "other_query"):
        return "crediction"
    if node_was_executed(run_data, "response_to_human1"):
        return "transfer"
    if node_was_executed(run_data, "wait_intent"):
        return "yes"
    if node_was_executed(run_data, "end_call"):
        return "no"
    if node_was_executed(run_data, "retuen_mean"):
        return "other"
    return "unknown"


def extract(execution: dict) -> dict | None:
    """
    從單一 execution 提取「19.是否有其他問題」數據。
    走到 return_other_question (無論是 other_question 或 other_send_question) 即計入。
    """
    run_data = get_run_data(execution)

    triggered_after_sms = node_was_executed(run_data, "other_send_question")
    triggered_after_reject = node_was_executed(run_data, "other_question")
    entered = (
        triggered_after_sms
        or triggered_after_reject
        or node_was_executed(run_data, "return_other_question")
        or node_was_executed(run_data, "receive_other_question")
    )
    if not entered:
        return None

    # session / customer
    webhook = get_node_output(run_data, "receive_message_API")
    body = webhook.get("body", {}) if webhook else {}

    # 客戶停留時間: return_other_question → receive_other_question
    stay_duration_sec = calc_node_duration_seconds(
        run_data, "return_other_question", "receive_other_question"
    )

    # 客戶回覆內容
    customer_reply = None
    recv = get_node_output(run_data, "receive_other_question")
    if recv:
        customer_reply = recv.get("body", {}).get("text")

    response_label = _classifier_label(run_data)

    return {
        "node": "19.是否有其他問題",
        "entered": True,
        "session_id": body.get("sessionID"),
        "customer_id": body.get("customerID"),
        "triggered_from_sms": triggered_after_sms,
        "triggered_from_reject": triggered_after_reject,
        "response_type": response_label,
        "customer_reply": customer_reply,
        "stay_duration_sec": stay_duration_sec,
        "execution_time_ms": get_node_execution_time(run_data, "other_question_classifier"),
    }


def aggregate(records: list[dict]) -> dict:
    """彙總多筆 execution 的「19.是否有其他問題」數據。"""
    valid = [r for r in records if r is not None]

    no_other = sum(1 for r in valid if r.get("response_type") == "no")
    has_card = sum(1 for r in valid if r.get("response_type") == "crediction")
    has_yes = sum(1 for r in valid if r.get("response_type") == "yes")
    transfer = sum(1 for r in valid if r.get("response_type") == "transfer")
    other = sum(1 for r in valid if r.get("response_type") == "other")

    stay_records = [r for r in valid if r.get("stay_duration_sec") is not None]
    avg_stay = None
    if stay_records:
        avg_stay = round(
            sum(r["stay_duration_sec"] for r in stay_records) / len(stay_records),
            3,
        )

    response_dist = {
        "no (沒有其他問題)": no_other,
        "crediction (信用卡問題)": has_card,
        "yes (有問題但未具體說明)": has_yes,
        "transfer (要求轉接專員)": transfer,
        "other (語意不明)": other,
    }

    return {
        "report_item": "19.是否有其他問題",
        "total_count": len(valid),
        "no_other_question_count": no_other,
        "has_card_question_count": has_card,
        "has_unspecified_yes_count": has_yes,
        "transfer_human_count": transfer,
        "ambiguous_other_count": other,
        "avg_stay_duration_sec": avg_stay,
        "response_distribution": response_dist,
    }
