"""
exception_error.py - 例外4: 任一節點發生系統 ERROR
=====================================================
報表項目 (例外情境 項次 4):
  1. 發生次數並轉接專員的筆數
  2. ERROR 代碼/類型
  3. ERROR 發生的節點

對應 n8n 節點 (v0.0.1):
  - 任何節點 executionStatus == "error"
    (注意: "waiting" 不算 ERROR, 屬於例外3 TimeOut)
  - intent_identification / intent_identification2 設定 onError: continueErrorOutput
    → error_msg → error_to_human → return_error_to_human
  - extract_phone (LangChain chainLlm) 設定 onError → error_to_human
  - phone_classifier fallback → error_to_human
  - Text Classifier fallback (output 2) → error_msg → error_to_human
  - execution 全域 status == "error" / "crashed"

waiting 狀態屬於 TimeOut 例外, 不在此處計入。
"""

from utils import (
    get_run_data,
    get_node_output,
    get_node_status,
    node_was_executed,
    get_all_node_names,
)

# 視為 error 的節點狀態 (排除 success / waiting / running)
ERROR_NODE_STATUS = {"error", "failed", "crashed"}


def extract(execution: dict) -> dict | None:
    """
    從單一 execution 提取「例外4: 系統 ERROR」數據。
    """
    run_data = get_run_data(execution)
    exec_status = execution.get("status")

    error_nodes = []
    error_details = []

    # 掃描所有節點: 只收 "真正出錯" 的 (排除 waiting)
    for node_name in get_all_node_names(run_data):
        status = get_node_status(run_data, node_name)
        if not status or status not in ERROR_NODE_STATUS:
            continue
        entries = run_data.get(node_name, [])
        info = {"node": node_name, "status": status}
        if entries:
            entry = entries[0]
            err = entry.get("error", {})
            if isinstance(err, dict):
                info["error_message"] = err.get("message", "")
                info["error_type"] = err.get("name", "")
            elif isinstance(err, str):
                info["error_message"] = err
        error_nodes.append(node_name)
        error_details.append(info)

    # error_to_human 路徑 (intent_identification onError / classifier fallback)
    went_error_to_human = node_was_executed(run_data, "error_to_human")
    if went_error_to_human and not error_nodes:
        # 找出觸發 error_to_human 的上游節點 (error_msg / extract_phone / phone_classifier)
        triggering = []
        for upstream in ("error_msg", "extract_phone", "phone_classifier"):
            if node_was_executed(run_data, upstream):
                triggering.append(upstream)
        error_nodes.extend(triggering or ["intent_identification(error_output)"])
        for n in triggering or ["intent_identification"]:
            error_details.append({
                "node": n,
                "status": "error_output_triggered",
                "error_message": "觸發 error output → 轉接真人客服",
            })

    # 全域 execution error (非 waiting / canceled / success)
    is_execution_error = exec_status in ("error", "crashed")
    if is_execution_error and not error_nodes:
        error_nodes.append("execution_level")
        error_details.append({
            "node": "execution_level",
            "status": exec_status,
            "error_message": "整體 execution 失敗",
        })

    if not error_nodes and not is_execution_error and not went_error_to_human:
        return None

    # 客戶資訊
    webhook = get_node_output(run_data, "receive_message_API")
    body = webhook.get("body", {}) if webhook else {}

    return {
        "exception": "任一節點發生系統ERROR",
        "session_id": body.get("sessionID"),
        "customer_id": body.get("customerID"),
        "execution_status": exec_status,
        "error_nodes": error_nodes,
        "error_details": error_details,
        "transferred_to_human": went_error_to_human,
    }


def aggregate(records: list[dict]) -> dict:
    """彙總多筆 execution 的「例外4: 系統 ERROR」數據。"""
    valid = [r for r in records if r is not None]

    transferred_count = sum(1 for r in valid if r.get("transferred_to_human"))

    error_node_dist = {}
    error_type_dist = {}
    for r in valid:
        for detail in r.get("error_details", []):
            node = detail.get("node", "unknown")
            error_node_dist[node] = error_node_dist.get(node, 0) + 1
            etype = detail.get("error_type") or detail.get("status", "unknown")
            error_type_dist[etype] = error_type_dist.get(etype, 0) + 1

    return {
        "report_item": "例外4.任一節點發生系統ERROR",
        "total_error_count": len(valid),
        "transferred_to_human_count": transferred_count,
        "error_node_distribution": error_node_dist,
        "error_type_distribution": error_type_dist,
    }
