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

對應 n8n 節點:
  - automation_router → SMS 路徑 → SMS_response → return_SMS
  
  ⚠ 目前 workflow 狀態:
     SMS_response 設定 action="send_message"，但流程在 return_SMS 後即結束。
     以下指標目前 CAN 從 log 中提取:
       ✅ 1. 進入此節點之數量 (走到 SMS_response 的次數)
       ✅ 9. 各知識點回答的筆數 (從 positive_metadata.intent 取得)
     以下指標 CANNOT 完整取得 (需 workflow 擴充後續節點):
       🔲 2. 客戶停留時間 (需要後續確認節點)
       🔲 3-4. 接收/不接收訊息 (需要後續客戶確認節點)
       🔲 5-6. 電話選擇方式 (需要後續選擇節點)
       🔲 7-8. 簡訊發送結果 (需要實際 SMS 發送節點)
     
     當 workflow 新增相關節點後，修改下方的節點名稱常數即可。
"""

from utils import (
    get_run_data,
    get_node_output,
    get_node_execution_time,
    node_was_executed,
    calc_node_duration_seconds,
)

# ── 未來節點名稱 (workflow 擴充後更新) ──────────
# 當 workflow 新增以下節點時，取消註解並填入正確名稱
NODE_SMS_CONFIRM = None          # 客戶確認是否接收簡訊的 wait 節點
NODE_SMS_PHONE_SELECT = None     # 客戶選擇電話的節點
NODE_SMS_SEND_RESULT = None      # 實際發送簡訊的結果節點


def extract(execution: dict) -> dict | None:
    """
    從單一 execution 提取「18.說答案後發送訊息(SMS)」數據。
    僅在流程走到 SMS_response 時才會被提取。
    """
    run_data = get_run_data(execution)

    if not node_was_executed(run_data, "SMS_response"):
        return None

    # 取得 SMS_response 節點輸出
    sms_output = get_node_output(run_data, "SMS_response")
    session_id = sms_output.get("sessionID") if sms_output else None
    customer_id = sms_output.get("customerID") if sms_output else None

    # 取得知識點 (意圖)
    meta_output = get_node_output(run_data, "positive_metadata")
    intent = None
    standard_answer = None
    if meta_output:
        metadata = meta_output.get("metadata", {})
        intent = metadata.get("intent")
        standard_answer = metadata.get("standardAnswer")

    # ── 目前可提取的欄位 ──
    record = {
        "node": "18.說答案後發送訊息(SMS)",
        "entered": True,
        "session_id": session_id,
        "customer_id": customer_id,
        "intent": intent,
        "standard_answer": standard_answer,
        "execution_time_ms": get_node_execution_time(run_data, "SMS_response"),
    }

    # ── 未來可提取的欄位 (workflow 擴充後啟用) ──

    # 客戶停留時間
    # if NODE_SMS_CONFIRM and node_was_executed(run_data, NODE_SMS_CONFIRM):
    #     record["stay_duration_sec"] = calc_node_duration_seconds(
    #         run_data, "return_SMS", NODE_SMS_CONFIRM
    #     )

    # 客戶是否選擇接收訊息
    # if NODE_SMS_CONFIRM and node_was_executed(run_data, NODE_SMS_CONFIRM):
    #     confirm_output = get_node_output(run_data, NODE_SMS_CONFIRM)
    #     record["accept_sms"] = confirm_output.get("accept")  # True/False

    # 電話選擇方式
    # if NODE_SMS_PHONE_SELECT and node_was_executed(run_data, NODE_SMS_PHONE_SELECT):
    #     phone_output = get_node_output(run_data, NODE_SMS_PHONE_SELECT)
    #     record["phone_type"] = phone_output.get("phone_type")  # "bank" / "custom"

    # 簡訊發送結果
    # if NODE_SMS_SEND_RESULT and node_was_executed(run_data, NODE_SMS_SEND_RESULT):
    #     send_output = get_node_output(run_data, NODE_SMS_SEND_RESULT)
    #     record["sms_sent_success"] = send_output.get("success")  # True/False

    return record


def aggregate(records: list[dict]) -> dict:
    """彙總多筆 execution 的「18.說答案後發送訊息(SMS)」數據。"""
    valid = [r for r in records if r is not None]

    # 各知識點 (意圖) 回答統計
    intent_distribution = {}
    for r in valid:
        intent = r.get("intent", "unknown")
        intent_distribution[intent] = intent_distribution.get(intent, 0) + 1

    result = {
        "report_item": "18.說答案後發送訊息(SMS)",
        "total_count": len(valid),
        "intent_distribution": intent_distribution,
    }

    # ── 未來欄位 (有資料時自動統計) ──

    # 接收/不接收訊息統計
    accept_records = [r for r in valid if "accept_sms" in r]
    if accept_records:
        result["accept_sms_count"] = sum(1 for r in accept_records if r.get("accept_sms"))
        result["reject_sms_count"] = sum(1 for r in accept_records if not r.get("accept_sms"))

    # 電話選擇方式統計
    phone_records = [r for r in valid if "phone_type" in r]
    if phone_records:
        result["bank_phone_count"] = sum(1 for r in phone_records if r.get("phone_type") == "bank")
        result["custom_phone_count"] = sum(1 for r in phone_records if r.get("phone_type") == "custom")

    # 簡訊發送結果統計
    send_records = [r for r in valid if "sms_sent_success" in r]
    if send_records:
        result["sms_success_count"] = sum(1 for r in send_records if r.get("sms_sent_success"))
        result["sms_fail_count"] = sum(1 for r in send_records if not r.get("sms_sent_success"))

    # 停留時間統計
    stay_records = [r for r in valid if r.get("stay_duration_sec") is not None]
    if stay_records:
        total_stay = sum(r["stay_duration_sec"] for r in stay_records)
        result["avg_stay_duration_sec"] = round(total_stay / len(stay_records), 3)

    return result