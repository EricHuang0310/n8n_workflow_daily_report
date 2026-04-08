"""
node_09_confirm_question.py - 9.與客戶確認問題
================================================
報表項目 (項次 5):
  1. 進入此節點之數量
  2. 客戶停留時間
  3. 客戶正向回覆的筆數
  4. 客戶負向回覆的筆數
  5. 重聽的筆數 (other)

對應 n8n 節點: set_confirm_response → receive_confirmation → ambiguous_intent_analyze → ambiguity_router
判斷邏輯:
  - ambiguity_router output.selected_intent == "positive" → 正向
  - ambiguity_router output.selected_intent == "negative" → 負向
  - ambiguity_router output.selected_intent == "other"    → 重聽/其他
  - 若 selected_intent 非以上三者 → 客戶選擇了特定意圖 (視為正向)
"""

from utils import (
    get_run_data,
    get_node_output,
    get_node_execution_time,
    node_was_executed,
    calc_node_duration_seconds,
)


def _determine_response_type(run_data: dict) -> str | None:
    """
    根據 ambiguous_intent_analyze 輸出判斷客戶回覆類型。
    回傳: 'positive' / 'negative' / 'other' / 'intent_selected' / None
    """
    analyze_output = get_node_output(run_data, "ambiguous_intent_analyze")
    if not analyze_output:
        return None

    output_obj = analyze_output.get("output", {})
    selected = output_obj.get("selected_intent", "")

    if selected == "positive":
        return "positive"
    elif selected == "negative":
        return "negative"
    elif selected == "other":
        return "other"
    elif selected:
        # 客戶在模糊選項中選了某個意圖 → 視同正向確認
        return "positive"
    return None


def extract(execution: dict) -> dict | None:
    """
    從單一 execution 提取「9.與客戶確認問題」節點數據。
    """
    run_data = get_run_data(execution)

    # 核心節點: set_confirm_response (播放確認語音) 或 receive_confirmation (等待回覆)
    if not node_was_executed(run_data, "set_confirm_response"):
        return None

    # 客戶停留時間: 從 return_confirm (開始播音) 到 receive_confirmation (收到回覆)
    stay_duration_sec = calc_node_duration_seconds(
        run_data, "return_confirm", "receive_confirmation"
    )

    # 取得客戶回覆內容
    confirm_output = get_node_output(run_data, "set_confirm")
    confirm_text = confirm_output.get("confirm_query") if confirm_output else None

    # 判斷回覆類型
    response_type = _determine_response_type(run_data)

    # 取得 session 資訊
    extract_output = get_node_output(run_data, "extract_intent")
    session_id = extract_output.get("sessionID") if extract_output else None

    return {
        "node": "9.與客戶確認問題",
        "entered": True,
        "session_id": session_id,
        "customer_confirm_text": confirm_text,
        "response_type": response_type,
        "stay_duration_sec": stay_duration_sec,
        "llm_analysis_time_ms": get_node_execution_time(run_data, "ambiguous_intent_analyze"),
    }


def aggregate(records: list[dict]) -> dict:
    """彙總多筆 execution 的「9.與客戶確認問題」數據。"""
    valid = [r for r in records if r is not None]

    positive_count = sum(1 for r in valid if r.get("response_type") == "positive")
    negative_count = sum(1 for r in valid if r.get("response_type") == "negative")
    other_count = sum(1 for r in valid if r.get("response_type") == "other")

    total_stay = 0.0
    stay_n = 0
    for r in valid:
        if r.get("stay_duration_sec") is not None:
            total_stay += r["stay_duration_sec"]
            stay_n += 1

    return {
        "report_item": "9.與客戶確認問題",
        "total_count": len(valid),
        "positive_count": positive_count,
        "negative_count": negative_count,
        "other_replay_count": other_count,
        "avg_stay_duration_sec": round(total_stay / stay_n, 3) if stay_n else None,
    }
