"""
utils.py - n8n Execution Log 共用解析工具
==========================================
提供載入 execution log、提取節點資料、計算時間差等基礎功能。
"""

import json
from datetime import datetime, timezone
from typing import Any


def load_execution_log(filepath: str) -> list[dict]:
    """
    載入 n8n execution log JSON 檔案，回傳 execution 清單。
    支援格式:
      - { "data": [ ... ] }            (API 回傳格式)
      - { "data": [ ... ], "nextCursor": ... }
      - [ { ... }, ... ]               (直接陣列)
    """
    with open(filepath, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return raw.get("data", [raw])
    return [raw]


def get_run_data(execution: dict) -> dict:
    """從單一 execution 取出 runData (node_name -> node_execution_entries)。"""
    return (
        execution
        .get("data", {})
        .get("resultData", {})
        .get("runData", {})
    )


def get_node_output(run_data: dict, node_name: str, entry_index: int = 0) -> dict | None:
    """
    從 runData 取出特定節點的輸出 JSON。
    回傳 main[0][0].json 或 None (若節點不存在)。
    """
    entries = run_data.get(node_name)
    if not entries or entry_index >= len(entries):
        return None
    entry = entries[entry_index]
    main = entry.get("data", {}).get("main", [[]])
    if main and main[0]:
        return main[0][0].get("json", {})
    return None


def get_node_execution_time(run_data: dict, node_name: str, entry_index: int = 0) -> int | None:
    """取得節點執行時間 (毫秒)。"""
    entries = run_data.get(node_name)
    if not entries or entry_index >= len(entries):
        return None
    return entries[entry_index].get("executionTime")


def get_node_status(run_data: dict, node_name: str, entry_index: int = 0) -> str | None:
    """取得節點執行狀態 (success / error)。"""
    entries = run_data.get(node_name)
    if not entries or entry_index >= len(entries):
        return None
    return entries[entry_index].get("executionStatus")


def get_node_start_time(run_data: dict, node_name: str, entry_index: int = 0) -> int | None:
    """取得節點開始時間 (epoch ms)。"""
    entries = run_data.get(node_name)
    if not entries or entry_index >= len(entries):
        return None
    return entries[entry_index].get("startTime")


def node_was_executed(run_data: dict, node_name: str) -> bool:
    """判斷節點是否被執行過。"""
    return node_name in run_data and len(run_data[node_name]) > 0


def get_execution_metadata(execution: dict) -> dict:
    """取出 execution 的基本 metadata。"""
    return {
        "execution_id": execution.get("id"),
        "status": execution.get("status"),
        "started_at": execution.get("startedAt"),
        "stopped_at": execution.get("stoppedAt"),
        "workflow_id": execution.get("workflowId"),
    }


def calc_node_duration_seconds(run_data: dict, start_node: str, end_node: str) -> float | None:
    """
    計算從 start_node 到 end_node 的停留時間 (秒)。
    使用 startTime (epoch ms) 做差。
    """
    t1 = get_node_start_time(run_data, start_node)
    t2 = get_node_start_time(run_data, end_node)
    if t1 is not None and t2 is not None:
        return round((t2 - t1) / 1000.0, 3)
    return None


def get_all_node_names(run_data: dict) -> list[str]:
    """取得所有被執行的節點名稱。"""
    return list(run_data.keys())


def has_error_output(run_data: dict, node_name: str) -> bool:
    """檢查節點是否有 error output (走了 onError 路徑)。"""
    entries = run_data.get(node_name, [])
    if not entries:
        return False
    entry = entries[0]
    main = entry.get("data", {}).get("main", [])
    # n8n error output 通常在 main[1]
    return len(main) > 1 and main[1] is not None and len(main[1]) > 0

# logs  = load_execution_log('../n8n範例log.json')
# print(logs)
