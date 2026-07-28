"""
node_18_sms_send.py - 18.說答案後發送訊息(SMS)
=================================================
報表項目 (項次 13):
  1. 進入此節點之數量
  2. 客戶停留時間
  3. 客戶選擇接收訊息的筆數
  4. 客戶選擇不接收訊息的筆數
  5. 客戶選擇本行行動電話接收的筆數
  6. 客戶選擇自行輸入行動電話接收的筆數
  7. 簡訊發送成功筆數
  8. 簡訊發送失敗筆數
  9. 各知識點回答的筆數

對應 n8n 節點 (v0.0.1):
  automation_router → SMS_response → return_SMS → save_message
    → receive_confirmation_message  (等待客戶回覆是否接收訊息)
    → send_message_intent (LLM 分類 yes/no/repeat)
    → ambiguity_router1
        - yes    → EAI001/EAI055/EAI100 (查行內電話) → check_phone + phone_classifier
                                                       (yes/number/no)
        - no     → other_question (不接收, 直接問是否還有其他問題)
        - repeat → SMS_response (重播)

  phone_classifier:
    - yes    (set_phone)        : 客戶同意以本行系統手機接收
    - number (extract_phone+regex+confirm) : 客戶口頭給出新號碼
    - no/other (speck_phone)    : 客戶要自行說手機
    - (error 路徑 → error_to_human)

  Message:
    HTTP POST 真正發送 SMS。成功與否從 entry.executionStatus + 回應 body 推斷。
"""

from utils import (
    get_run_data,
    get_node_output,
    get_node_execution_time,
    get_node_status,
    node_was_executed,
    calc_node_duration_seconds,
)


def _accept_status(run_data: dict) -> str | None:
    """
    客戶對「是否接收簡訊」的回覆 (send_message_intent + ambiguity_router1)。
    回傳: 'accept' / 'reject' / 'replay' / None
    """
    if not node_was_executed(run_data, "send_message_intent"):
        return None
    out = get_node_output(run_data, "send_message_intent")
    if out:
        sel = (out.get("output") or {}).get("selected_intent")
        if sel == "yes":
            return "accept"
        if sel == "no":
            return "reject"
        if sel == "repeat":
            return "replay"
    # fallback: 觀察 ambiguity_router1 下游
    if node_was_executed(run_data, "EAI001") or node_was_executed(run_data, "get_phone_number"):
        return "accept"
    if node_was_executed(run_data, "other_question"):
        return "reject"
    return None


def _phone_choice(run_data: dict) -> str | None:
    """
    電話選擇方式:
      - 'bank'   : 客戶採用本行系統手機 (set_phone)
      - 'spoken' : 客戶口述新號碼 (set_other_phone / speck_phone)
      - None     : 尚未進入電話選擇
    """
    if not node_was_executed(run_data, "phone_classifier"):
        return None
    if node_was_executed(run_data, "set_phone"):
        return "bank"
    if node_was_executed(run_data, "set_other_phone"):
        return "spoken"
    if node_was_executed(run_data, "speck_phone"):
        return "spoken"
    return None


def _sms_send_result(run_data: dict) -> str | None:
    """
    Message 節點 (HTTP POST → SmSend) 的結果。
    回傳: 'success' / 'fail' / None
    """
    if not node_was_executed(run_data, "Message"):
        return None
    status = get_node_status(run_data, "Message")
    if status == "success":
        return "success"
    if status:
        return "fail"
    return None


def extract(execution: dict) -> dict | None:
    """
    從單一 execution 提取「18.說答案後發送訊息(SMS)」數據。
    僅在流程走到 SMS_response 時才會被提取。
    """
    run_data = get_run_data(execution)

    if not node_was_executed(run_data, "SMS_response"):
        return None

    # SMS_response 節點輸出
    sms_output = get_node_output(run_data, "SMS_response")
    session_id = sms_output.get("sessionID") if sms_output else None
    customer_id = sms_output.get("customerID") if sms_output else None

    # 知識點 (意圖)
    meta_output = get_node_output(run_data, "positive_metadata")
    intent = None
    standard_answer = None
    if meta_output:
        metadata = meta_output.get("metadata", {})
        intent = metadata.get("intent")
        standard_answer = metadata.get("standardAnswer")

    accept = _accept_status(run_data)
    phone_choice = _phone_choice(run_data)
    send_result = _sms_send_result(run_data)

    # 停留時間: 從 return_SMS (開始播音) 到 receive_confirmation_message (客戶回覆)
    stay_duration_sec = calc_node_duration_seconds(
        run_data, "return_SMS", "receive_confirmation_message"
    )

    return {
        "node": "18.說答案後發送訊息(SMS)",
        "entered": True,
        "session_id": session_id,
        "customer_id": customer_id,
        "intent": intent,
        "standard_answer": standard_answer,
        "accept_status": accept,                # accept / reject / replay
        "phone_choice": phone_choice,           # bank / spoken
        "sms_send_result": send_result,         # success / fail
        "stay_duration_sec": stay_duration_sec,
        "execution_time_ms": get_node_execution_time(run_data, "SMS_response"),
    }


def aggregate(records: list[dict]) -> dict:
    """彙總多筆 execution 的「18.說答案後發送訊息(SMS)」數據。"""
    valid = [r for r in records if r is not None]

    # 知識點 (意圖) 分布
    intent_distribution = {}
    for r in valid:
        key = r.get("intent") or "unknown"
        intent_distribution[key] = intent_distribution.get(key, 0) + 1

    accept_count = sum(1 for r in valid if r.get("accept_status") == "accept")
    reject_count = sum(1 for r in valid if r.get("accept_status") == "reject")
    replay_count = sum(1 for r in valid if r.get("accept_status") == "replay")

    bank_phone_count = sum(1 for r in valid if r.get("phone_choice") == "bank")
    custom_phone_count = sum(1 for r in valid if r.get("phone_choice") == "spoken")

    sms_success_count = sum(1 for r in valid if r.get("sms_send_result") == "success")
    sms_fail_count = sum(1 for r in valid if r.get("sms_send_result") == "fail")

    # 停留時間
    stay_records = [r for r in valid if r.get("stay_duration_sec") is not None]
    avg_stay = None
    if stay_records:
        avg_stay = round(sum(r["stay_duration_sec"] for r in stay_records) / len(stay_records), 3)

    return {
        "report_item": "18.說答案後發送訊息(SMS)",
        "total_count": len(valid),
        "accept_sms_count": accept_count,
        "reject_sms_count": reject_count,
        "replay_sms_count": replay_count,
        "bank_phone_count": bank_phone_count,
        "custom_phone_count": custom_phone_count,
        "sms_success_count": sms_success_count,
        "sms_fail_count": sms_fail_count,
        "avg_stay_duration_sec": avg_stay,
        "intent_distribution": intent_distribution,
    }
