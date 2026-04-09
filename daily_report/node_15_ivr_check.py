"""
node_15_ivr_check.py - 15.是否為語音一站式
=============================================
報表項目 (項次 10):
  1. 進入此節點之數量
  2. 客戶停留時間
  3. 轉接既有語音各項功能的筆數
  4. 非轉接既有語音功能的筆數

對應 n8n 節點: automation_router 的 to_ivr / SMS 分流
  - to_ivr (transfer_ivr_auth) → 轉接語音功能 (IVR)
  - SMS (send_message)         → 非語音功能 (發訊息)
  
注意: 此節點僅在 automation_router 判定「可自動化處理」後才會進入。
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
    從單一 execution 提取「15.是否為語音一站式」數據。
    只有走到可自動化路線 (IVR 或 SMS) 的 execution 才算進入此節點。
    """
    run_data = get_run_data(execution)

    is_ivr = node_was_executed(run_data, "IVR_response")
    is_sms = node_was_executed(run_data, "SMS_response")

    if not is_ivr and not is_sms:
        return None

    # 取得 IVR 的詳細資訊
    ivr_detail = None
    if is_ivr:
        ivr_output = get_node_output(run_data, "IVR_response")
        if ivr_output:
            meta = ivr_output.get("metadata", {})
            ivr_detail = {
                "voice_command": meta.get("voiceCommand"),
                "script_no": meta.get("scriptNo"),
                "call_type": meta.get("callType"),
            }

    sms_detail = None
    if is_sms:
        sms_output = get_node_output(run_data, "SMS_response")
        if sms_output:
            meta = sms_output.get("metadata", {})
            sms_detail = {
                "call_type": meta.get("callType"),
            }

    extract_output = get_node_output(run_data, "extract_intent")
    session_id = extract_output.get("sessionID") if extract_output else None

    # 停留時間: 從 automation_router 到 IVR_response / SMS_response
    end_node = "IVR_response" if is_ivr else "SMS_response"
    stay_duration_sec = calc_node_duration_seconds(
        run_data, "automation_router", end_node
    )

    return {
        "node": "15.是否為語音一站式",
        "entered": True,
        "session_id": session_id,
        "is_ivr_transfer": is_ivr,
        "is_sms": is_sms,
        "ivr_detail": ivr_detail,
        "sms_detail": sms_detail,
        "stay_duration_sec": stay_duration_sec,
    }


def aggregate(records: list[dict]) -> dict:
    """彙總多筆 execution 的「15.是否為語音一站式」數據。"""
    valid = [r for r in records if r is not None]

    ivr_count = sum(1 for r in valid if r.get("is_ivr_transfer"))
    sms_count = sum(1 for r in valid if r.get("is_sms"))

    # IVR 各功能分布 (by voiceCommand code)
    ivr_function_dist = {}
    total_stay_sec = 0.0
    stay_count = 0
    for r in valid:
        detail = r.get("ivr_detail")
        if detail and detail.get("voice_command"):
            cmd = detail["voice_command"]
            ivr_function_dist[cmd] = ivr_function_dist.get(cmd, 0) + 1
        if r.get("stay_duration_sec") is not None:
            total_stay_sec += r["stay_duration_sec"]
            stay_count += 1

    return {
        "report_item": "15.是否為語音一站式",
        "total_count": len(valid),
        "avg_stay_duration_sec": (
            round(total_stay_sec / stay_count, 3) if stay_count else None
        ),
        "ivr_transfer_count": ivr_count,
        "non_ivr_count": sms_count,
        "ivr_function_distribution": ivr_function_dist,
    }
