"""
node_10_automation_check.py - 10.是否可自動化處理
===================================================
報表項目 (項次 6):
  1. 進入此節點之數量
  2. 客戶停留時間
  3. 可自動化處理的筆數 (SMS / IVR)
  4. 不可自動化處理的筆數 (轉接專員)

對應 n8n 節點: automation_router
  - SMS (send_message)           → 可自動化
  - to_ivr (transfer_ivr_auth)   → 可自動化
  - to_human (transfer_direct)   → 不可自動化
  - to_human_auth (transfer_auth)→ 不可自動化
"""

from utils import (
    get_run_data,
    get_node_output,
    get_node_execution_time,
    node_was_executed,
    calc_node_duration_seconds,
)

# 可自動化的 action 類型
AUTOMATABLE_ACTIONS = {"send_message", "transfer_ivr_auth"}
# 不可自動化 (需轉真人) 的 action 類型
NON_AUTOMATABLE_ACTIONS = {"transfer_direct", "transfer_auth"}


def _determine_action(run_data: dict) -> str | None:
    """
    從最終回覆節點判斷走了哪條路。
    """
    action_nodes = {
        "SMS_response": "send_message",
        "live_support_response1": "transfer_direct",
        "live_support_response2": "transfer_auth",
        "IVR_response": "transfer_ivr_auth",
    }
    for node_name, action in action_nodes.items():
        if node_was_executed(run_data, node_name):
            return action

    # 備用: 從 positive_metadata 取 subsequentActions 推算
    meta = get_node_output(run_data, "positive_metadata")
    if meta:
        subsequent = meta.get("metadata", {}).get("subsequentActions", "")
        mapping = {
            "不核身轉接專員": "transfer_direct",
            "核身後轉接專員": "transfer_auth",
            "核身後轉接語音功能": "transfer_ivr_auth",
            "發訊息": "send_message",
        }
        return mapping.get(subsequent)

    return None


def extract(execution: dict) -> dict | None:
    """
    從單一 execution 提取「10.是否可自動化處理」數據。
    """
    run_data = get_run_data(execution)

    if not node_was_executed(run_data, "automation_router"):
        return None

    action = _determine_action(run_data)
    is_automatable = action in AUTOMATABLE_ACTIONS if action else None

    # automation_router 節點本身的執行時間
    exec_time_ms = get_node_execution_time(run_data, "automation_router")

    # 取得 session 資訊
    extract_output = get_node_output(run_data, "extract_intent")
    session_id = extract_output.get("sessionID") if extract_output else None

    # 取得最終 metadata 與最終節點名稱 (用於計算停留時間)
    final_output = None
    final_node_name = None
    for resp_node in ["SMS_response", "live_support_response1",
                       "live_support_response2", "IVR_response"]:
        if node_was_executed(run_data, resp_node):
            final_output = get_node_output(run_data, resp_node)
            final_node_name = resp_node
            break

    # 停留時間: 從 automation_router 到最終回覆節點
    stay_duration_sec = None
    if final_node_name:
        stay_duration_sec = calc_node_duration_seconds(
            run_data, "automation_router", final_node_name
        )

    return {
        "node": "10.是否可自動化處理",
        "entered": True,
        "session_id": session_id,
        "action": action,
        "is_automatable": is_automatable,
        "subsequent_action_detail": final_output.get("metadata") if final_output else None,
        "stay_duration_sec": stay_duration_sec,
        "execution_time_ms": exec_time_ms,
    }


def aggregate(records: list[dict]) -> dict:
    """彙總多筆 execution 的「10.是否可自動化處理」數據。"""
    valid = [r for r in records if r is not None]

    automatable = sum(1 for r in valid if r.get("is_automatable") is True)
    non_automatable = sum(1 for r in valid if r.get("is_automatable") is False)

    # 各 action 統計
    action_dist = {}
    total_stay_sec = 0.0
    stay_count = 0
    for r in valid:
        act = r.get("action", "unknown")
        action_dist[act] = action_dist.get(act, 0) + 1
        if r.get("stay_duration_sec") is not None:
            total_stay_sec += r["stay_duration_sec"]
            stay_count += 1

    return {
        "report_item": "10.是否可自動化處理",
        "total_count": len(valid),
        "avg_stay_duration_sec": (
            round(total_stay_sec / stay_count, 3) if stay_count else None
        ),
        "automatable_count": automatable,
        "non_automatable_count": non_automatable,
        "action_distribution": action_dist,
    }
