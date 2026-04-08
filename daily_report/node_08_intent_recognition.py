"""
node_08_intent_recognition.py - 8.理解問題
=============================================
報表項目 (項次 4):
  1. 進入此節點之數量
  2. 客戶停留時間
  3. LLM辨識的意圖
  4. 明確問題的筆數
  5. 模糊問題的筆數

對應 n8n 節點: intent_identification, extract_intent
判斷邏輯:
  - output 陣列長度 == 1 → 明確問題
  - output 陣列長度 >= 2 → 模糊問題 (回傳最多3個候選意圖)
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
    從單一 execution 提取「8.理解問題」節點數據。
    """
    run_data = get_run_data(execution)

    if not node_was_executed(run_data, "intent_identification"):
        return None

    intent_output = get_node_output(run_data, "intent_identification")
    if not intent_output:
        return None

    output_list = intent_output.get("output", [])
    intents = [item.get("intent") for item in output_list if item.get("intent")]
    response_model = output_list[0].get("responseModel") if output_list else None

    # 明確 vs 模糊
    is_clear = len(output_list) == 1
    is_ambiguous = len(output_list) >= 2

    # 停留時間: intent_identification 本身的執行時間 (包含呼叫 LLM)
    exec_time_ms = get_node_execution_time(run_data, "intent_identification")

    # 從 intent_identification 到下一步 extract_intent 的時間差
    stay_duration_sec = calc_node_duration_seconds(
        run_data, "intent_identification", "extract_intent"
    )

    # 取出 extract_intent 節點的完整資訊
    extract_output = get_node_output(run_data, "extract_intent")
    session_id = extract_output.get("sessionID") if extract_output else None

    return {
        "node": "8.理解問題",
        "entered": True,
        "session_id": session_id,
        "intents": intents,
        "intent_count": len(output_list),
        "is_clear": is_clear,
        "is_ambiguous": is_ambiguous,
        "response_model": response_model,
        "intent_identification_time_ms": exec_time_ms,
        "stay_duration_sec": stay_duration_sec,
    }


def aggregate(records: list[dict]) -> dict:
    """彙總多筆 execution 的「8.理解問題」數據。"""
    valid = [r for r in records if r is not None]

    clear_count = sum(1 for r in valid if r.get("is_clear"))
    ambiguous_count = sum(1 for r in valid if r.get("is_ambiguous"))

    all_intents = {}
    total_intent_time_ms = 0
    intent_time_count = 0

    for r in valid:
        for intent in r.get("intents", []):
            all_intents[intent] = all_intents.get(intent, 0) + 1
        if r.get("intent_identification_time_ms") is not None:
            total_intent_time_ms += r["intent_identification_time_ms"]
            intent_time_count += 1

    return {
        "report_item": "8.理解問題",
        "total_count": len(valid),
        "clear_question_count": clear_count,
        "ambiguous_question_count": ambiguous_count,
        "avg_intent_identification_time_ms": (
            round(total_intent_time_ms / intent_time_count, 1)
            if intent_time_count else None
        ),
        "intent_distribution": all_intents,
    }
