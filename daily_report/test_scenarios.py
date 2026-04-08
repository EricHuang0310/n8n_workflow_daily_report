"""
test_scenarios.py - 批次測試情境定義
==========================================
為客服語音機器人的所有報表項目與例外情境，定義完整的測試案例。

每個情境由多個「步驟」組成:
  - step_type: "webhook" (呼叫主 webhook) / "resume" (呼叫 resumeUrl) / "hangup" (清除 session)
  - payload:   送出的 JSON body
  - expect:    預期結果描述 (供人工檢查用)

設計原則:
  - 每個情境使用不同的 sessionID 與 customerID 以避免互相干擾
  - 需要計數器的情境 (negative 第2次、other 第2次) 使用同一 sessionID 連續觸發
  - 每個情境開頭先呼叫 hangUp API 清除歷史，確保測試隔離
"""

import random
import string
from datetime import datetime


def _gen_session_id(prefix: str) -> str:
    """產生唯一的 session ID。"""
    ts = datetime.now().strftime("%H%M%S")
    rand = "".join(random.choices(string.digits, k=3))
    return f"{prefix}_{ts}_{rand}"


def _gen_customer_id(letter: str = "T") -> str:
    """產生測試用客戶 ID。"""
    return f"{letter}{random.randint(100000000, 999999999)}"


def _gen_phone() -> str:
    """產生測試用手機號碼。"""
    return f"09{random.randint(10000000, 99999999)}"


def _make_payload(session_id: str, customer_id: str, text: str, phone: str = None):
    """建立標準 webhook payload。"""
    return {
        "sessionID": session_id,
        "customerID": customer_id,
        "text": text,
        "phone": phone or _gen_phone(),
        "metada": {
            "history": None,
            "scriptNo": None,
            "voiceCommand": None,
            "resumeUrl": None,
        },
    }


def generate_all_scenarios() -> list[dict]:
    """
    產生所有測試情境。
    回傳情境清單，每個情境包含 name, description, steps, expected_report_items。
    """
    scenarios = []

    # ═══════════════════════════════════════════════════════════
    # 正常流程：明確問題 → 正向確認
    # ═══════════════════════════════════════════════════════════

    # ── 情境 1: 明確問題 → 正向確認 (客戶說「對」) ──
    sid = _gen_session_id("S01")
    cid = _gen_customer_id("A")
    phone = _gen_phone()
    scenarios.append({
        "id": "TC01",
        "name": "明確問題_正向確認_對",
        "description": "客戶問明確問題，機器人辨識為單一意圖，客戶確認「對」",
        "steps": [
            {
                "step": 1,
                "step_type": "hangup",
                "description": "清除 session 歷史",
                "payload": {"sessionID": sid},
            },
            {
                "step": 2,
                "step_type": "webhook",
                "description": "客戶說出問題: 我要如何開卡",
                "payload": _make_payload(sid, cid, "我要如何開卡", phone),
            },
            {
                "step": 3,
                "step_type": "resume",
                "description": "客戶正向確認: 對",
                "payload": _make_payload(sid, cid, "對", phone),
            },
        ],
        "expected_report_items": ["node_07", "node_08", "node_09(positive)", "node_10", "node_15"],
    })

    # ── 情境 2: 明確問題 → 正向確認 (客戶說「是的」) ──
    sid = _gen_session_id("S02")
    cid = _gen_customer_id("A")
    phone = _gen_phone()
    scenarios.append({
        "id": "TC02",
        "name": "明確問題_正向確認_是的",
        "description": "客戶問信用卡帳單，客戶確認「是的」",
        "steps": [
            {
                "step": 1,
                "step_type": "hangup",
                "description": "清除 session 歷史",
                "payload": {"sessionID": sid},
            },
            {
                "step": 2,
                "step_type": "webhook",
                "description": "客戶說出問題: 我的信用卡帳單什麼時候到",
                "payload": _make_payload(sid, cid, "我的信用卡帳單什麼時候到", phone),
            },
            {
                "step": 3,
                "step_type": "resume",
                "description": "客戶正向確認: 是的",
                "payload": _make_payload(sid, cid, "是的", phone),
            },
        ],
        "expected_report_items": ["node_07", "node_08", "node_09(positive)", "node_10"],
    })

    # ── 情境 3: 明確問題 → 正向確認 (另一個問題) ──
    sid = _gen_session_id("S03")
    cid = _gen_customer_id("B")
    phone = _gen_phone()
    scenarios.append({
        "id": "TC03",
        "name": "明確問題_正向確認_信用卡掛失",
        "description": "客戶問信用卡掛失，正向確認",
        "steps": [
            {
                "step": 1,
                "step_type": "hangup",
                "description": "清除 session 歷史",
                "payload": {"sessionID": sid},
            },
            {
                "step": 2,
                "step_type": "webhook",
                "description": "客戶說出問題: 我的信用卡不見了要掛失",
                "payload": _make_payload(sid, cid, "我的信用卡不見了要掛失", phone),
            },
            {
                "step": 3,
                "step_type": "resume",
                "description": "客戶正向確認: 沒錯",
                "payload": _make_payload(sid, cid, "沒錯", phone),
            },
        ],
        "expected_report_items": ["node_07", "node_08", "node_09(positive)", "node_10"],
    })

    # ── 情境 4: 明確問題 → 正向確認 (繳費問題) ──
    sid = _gen_session_id("S04")
    cid = _gen_customer_id("B")
    phone = _gen_phone()
    scenarios.append({
        "id": "TC04",
        "name": "明確問題_正向確認_繳費",
        "description": "客戶問如何繳卡費，正向確認「好的」",
        "steps": [
            {
                "step": 1,
                "step_type": "hangup",
                "description": "清除 session 歷史",
                "payload": {"sessionID": sid},
            },
            {
                "step": 2,
                "step_type": "webhook",
                "description": "客戶說出問題: 我要繳信用卡費",
                "payload": _make_payload(sid, cid, "我要繳信用卡費", phone),
            },
            {
                "step": 3,
                "step_type": "resume",
                "description": "客戶正向確認: 好的",
                "payload": _make_payload(sid, cid, "好的", phone),
            },
        ],
        "expected_report_items": ["node_07", "node_08", "node_09(positive)", "node_10"],
    })

    # ── 情境 5: 明確問題 → 正向確認 (額度查詢) ──
    sid = _gen_session_id("S05")
    cid = _gen_customer_id("C")
    phone = _gen_phone()
    scenarios.append({
        "id": "TC05",
        "name": "明確問題_正向確認_額度查詢",
        "description": "客戶查詢信用卡額度，正向確認",
        "steps": [
            {
                "step": 1,
                "step_type": "hangup",
                "description": "清除 session 歷史",
                "payload": {"sessionID": sid},
            },
            {
                "step": 2,
                "step_type": "webhook",
                "description": "客戶說出問題: 我想查信用卡額度",
                "payload": _make_payload(sid, cid, "我想查信用卡額度", phone),
            },
            {
                "step": 3,
                "step_type": "resume",
                "description": "客戶正向確認: 對，就是這個",
                "payload": _make_payload(sid, cid, "對，就是這個", phone),
            },
        ],
        "expected_report_items": ["node_07", "node_08", "node_09(positive)", "node_10", "node_15"],
    })

    # ═══════════════════════════════════════════════════════════
    # 正常流程：模糊問題 → 客戶選擇意圖
    # ═══════════════════════════════════════════════════════════

    # ── 情境 6: 模糊問題 → 客戶選擇第一個 ──
    sid = _gen_session_id("S06")
    cid = _gen_customer_id("C")
    phone = _gen_phone()
    scenarios.append({
        "id": "TC06",
        "name": "模糊問題_客戶選擇意圖",
        "description": "客戶問題模糊，機器人列出多個意圖，客戶選第一個",
        "steps": [
            {
                "step": 1,
                "step_type": "hangup",
                "description": "清除 session 歷史",
                "payload": {"sessionID": sid},
            },
            {
                "step": 2,
                "step_type": "webhook",
                "description": "客戶說出模糊問題: 信用卡的問題",
                "payload": _make_payload(sid, cid, "信用卡的問題", phone),
            },
            {
                "step": 3,
                "step_type": "resume",
                "description": "客戶選擇: 第一個",
                "payload": _make_payload(sid, cid, "第一個", phone),
            },
        ],
        "expected_report_items": ["node_07", "node_08(ambiguous)", "node_09(positive)", "node_10"],
    })

    # ── 情境 7: 模糊問題 → 另一個模糊查詢 ──
    sid = _gen_session_id("S07")
    cid = _gen_customer_id("D")
    phone = _gen_phone()
    scenarios.append({
        "id": "TC07",
        "name": "模糊問題_客戶選擇意圖_2",
        "description": "客戶問題模糊「我有問題」，機器人列出候選，客戶選擇",
        "steps": [
            {
                "step": 1,
                "step_type": "hangup",
                "description": "清除 session 歷史",
                "payload": {"sessionID": sid},
            },
            {
                "step": 2,
                "step_type": "webhook",
                "description": "客戶說出模糊問題: 我想問一下卡片的事情",
                "payload": _make_payload(sid, cid, "我想問一下卡片的事情", phone),
            },
            {
                "step": 3,
                "step_type": "resume",
                "description": "客戶選擇: 信用卡帳單",
                "payload": _make_payload(sid, cid, "信用卡帳單", phone),
            },
        ],
        "expected_report_items": ["node_07", "node_08(ambiguous)", "node_09(positive)", "node_10"],
    })

    # ═══════════════════════════════════════════════════════════
    # 例外路徑：客戶否定確認（negative）
    # ═══════════════════════════════════════════════════════════

    # ── 情境 8: 否定確認 (第一次) → 重新詢問 ──
    sid = _gen_session_id("S08")
    cid = _gen_customer_id("E")
    phone = _gen_phone()
    scenarios.append({
        "id": "TC08",
        "name": "否定確認_第一次_重新詢問",
        "description": "客戶否定機器人的意圖判斷（第一次），機器人請客戶重新說明",
        "steps": [
            {
                "step": 1,
                "step_type": "hangup",
                "description": "清除 session 歷史",
                "payload": {"sessionID": sid},
            },
            {
                "step": 2,
                "step_type": "webhook",
                "description": "客戶說出問題: 我想問帳單的事",
                "payload": _make_payload(sid, cid, "我想問帳單的事", phone),
            },
            {
                "step": 3,
                "step_type": "resume",
                "description": "客戶否定確認: 不對",
                "payload": _make_payload(sid, cid, "不對", phone),
            },
        ],
        "expected_report_items": ["node_09(negative)", "exception_02(negative_first)"],
    })

    # ── 情境 9: 否定確認 (連續兩次) → 轉接專員 ──
    sid = _gen_session_id("S09")
    cid = _gen_customer_id("E")
    phone = _gen_phone()
    scenarios.append({
        "id": "TC09",
        "name": "否定確認_連續兩次_轉接專員",
        "description": "客戶連續否定兩次，第二次直接轉接真人專員",
        "steps": [
            # 清除歷史
            {
                "step": 1,
                "step_type": "hangup",
                "description": "清除 session 歷史",
                "payload": {"sessionID": sid},
            },
            # 第一輪: 問題 → 否定
            {
                "step": 2,
                "step_type": "webhook",
                "description": "[第1輪] 客戶說出問題: 我要查帳",
                "payload": _make_payload(sid, cid, "我要查帳", phone),
            },
            {
                "step": 3,
                "step_type": "resume",
                "description": "[第1輪] 客戶否定: 不是這個",
                "payload": _make_payload(sid, cid, "不是這個", phone),
            },
            # 第二輪: 重新問 → 再次否定 → 轉接專員
            {
                "step": 4,
                "step_type": "webhook",
                "description": "[第2輪] 客戶重新說出問題: 我要問其他的",
                "payload": _make_payload(sid, cid, "我要問其他的", phone),
            },
            {
                "step": 5,
                "step_type": "resume",
                "description": "[第2輪] 客戶再次否定: 不對不對",
                "payload": _make_payload(sid, cid, "不對不對", phone),
            },
        ],
        "expected_report_items": ["exception_02(negative_second_transfer)"],
    })

    # ═══════════════════════════════════════════════════════════
    # 例外路徑：客戶回覆「其他」(other)
    # ═══════════════════════════════════════════════════════════

    # ── 情境 10: 其他回覆 (第一次) → 重聽 ──
    sid = _gen_session_id("S10")
    cid = _gen_customer_id("F")
    phone = _gen_phone()
    scenarios.append({
        "id": "TC10",
        "name": "其他回覆_第一次_重聽",
        "description": "客戶回覆無關內容（如「你好」），機器人重播意圖選項",
        "steps": [
            {
                "step": 1,
                "step_type": "hangup",
                "description": "清除 session 歷史",
                "payload": {"sessionID": sid},
            },
            {
                "step": 2,
                "step_type": "webhook",
                "description": "客戶說出問題: 我要辦分期",
                "payload": _make_payload(sid, cid, "我要辦分期", phone),
            },
            {
                "step": 3,
                "step_type": "resume",
                "description": "客戶回覆無關: 你好",
                "payload": _make_payload(sid, cid, "你好", phone),
            },
        ],
        "expected_report_items": ["node_09(other)", "exception_02(other_first)"],
    })

    # ── 情境 11: 其他回覆 → 再確認 → 正向確認 ──
    sid = _gen_session_id("S11")
    cid = _gen_customer_id("F")
    phone = _gen_phone()
    scenarios.append({
        "id": "TC11",
        "name": "其他回覆_後正向確認",
        "description": "客戶先說無關內容，重聽後正向確認",
        "steps": [
            {
                "step": 1,
                "step_type": "hangup",
                "description": "清除 session 歷史",
                "payload": {"sessionID": sid},
            },
            {
                "step": 2,
                "step_type": "webhook",
                "description": "客戶說出問題: 信用卡繳款方式",
                "payload": _make_payload(sid, cid, "信用卡繳款方式", phone),
            },
            {
                "step": 3,
                "step_type": "resume",
                "description": "客戶回覆無關: 什麼意思",
                "payload": _make_payload(sid, cid, "什麼意思", phone),
                "note": "此步驟 n8n 會進入 other 路徑，other_response 回傳後進入 receive_confirmation_again",
            },
            {
                "step": 4,
                "step_type": "resume",
                "description": "客戶重聽後正向確認: 對就是這個",
                "payload": _make_payload(sid, cid, "對就是這個", phone),
                "note": "此步驟回覆到 receive_confirmation_again 的 resumeUrl",
            },
        ],
        "expected_report_items": ["node_09(other→positive)", "node_10"],
    })

    # ═══════════════════════════════════════════════════════════
    # 例外路徑：客戶直接要求轉接專員
    # ═══════════════════════════════════════════════════════════

    # ── 情境 12: 客戶說「轉接專員」 ──
    sid = _gen_session_id("S12")
    cid = _gen_customer_id("G")
    phone = _gen_phone()
    scenarios.append({
        "id": "TC12",
        "name": "客戶直接要求轉專員",
        "description": "客戶一開始就說要轉接專員或真人客服",
        "steps": [
            {
                "step": 1,
                "step_type": "hangup",
                "description": "清除 session 歷史",
                "payload": {"sessionID": sid},
            },
            {
                "step": 2,
                "step_type": "webhook",
                "description": "客戶說出: 我要轉接專員",
                "payload": _make_payload(sid, cid, "我要轉接專員", phone),
            },
            {
                "step": 3,
                "step_type": "resume",
                "description": "客戶確認: 對",
                "payload": _make_payload(sid, cid, "對", phone),
            },
        ],
        "expected_report_items": ["exception_01(transfer_intent)"],
    })

    # ── 情境 13: 客戶說「找真人」 ──
    sid = _gen_session_id("S13")
    cid = _gen_customer_id("G")
    phone = _gen_phone()
    scenarios.append({
        "id": "TC13",
        "name": "客戶直接找真人",
        "description": "客戶直接說要找真人客服",
        "steps": [
            {
                "step": 1,
                "step_type": "hangup",
                "description": "清除 session 歷史",
                "payload": {"sessionID": sid},
            },
            {
                "step": 2,
                "step_type": "webhook",
                "description": "客戶說出: 我不想跟機器人講話找真人來",
                "payload": _make_payload(sid, cid, "我不想跟機器人講話找真人來", phone),
            },
            {
                "step": 3,
                "step_type": "resume",
                "description": "客戶確認轉接: 對",
                "payload": _make_payload(sid, cid, "對", phone),
            },
        ],
        "expected_report_items": ["exception_01(transfer_intent)"],
    })

    # ═══════════════════════════════════════════════════════════
    # 更多正常流程：不同客戶問題（增加意圖分布多樣性）
    # ═══════════════════════════════════════════════════════════

    additional_questions = [
        ("TC14", "預借現金", "我想要預借現金", "對"),
        ("TC15", "信用卡年費", "我想問信用卡年費多少", "是的"),
        ("TC16", "信用卡紅利", "我想查信用卡紅利點數", "對就是這個"),
        ("TC17", "信用卡分期", "我想辦信用卡分期付款", "好"),
        ("TC18", "信用卡換卡", "我的信用卡到期要換卡", "沒錯"),
        ("TC19", "信用卡優惠", "最近有什麼信用卡優惠", "是"),
        ("TC20", "臨時額度", "我想申請臨時額度調高", "對"),
    ]

    for tc_id, name, question, confirm in additional_questions:
        sid = _gen_session_id(tc_id)
        cid = _gen_customer_id("H")
        phone = _gen_phone()
        scenarios.append({
            "id": tc_id,
            "name": f"明確問題_正向確認_{name}",
            "description": f"客戶問「{question}」，正向確認「{confirm}」",
            "steps": [
                {
                    "step": 1,
                    "step_type": "hangup",
                    "description": "清除 session 歷史",
                    "payload": {"sessionID": sid},
                },
                {
                    "step": 2,
                    "step_type": "webhook",
                    "description": f"客戶說出問題: {question}",
                    "payload": _make_payload(sid, cid, question, phone),
                },
                {
                    "step": 3,
                    "step_type": "resume",
                    "description": f"客戶正向確認: {confirm}",
                    "payload": _make_payload(sid, cid, confirm, phone),
                },
            ],
            "expected_report_items": ["node_07", "node_08", "node_09(positive)", "node_10"],
        })

    return scenarios


def print_scenario_summary(scenarios: list[dict]):
    """印出所有測試情境的摘要表。"""
    print(f"\n{'='*70}")
    print(f"  共 {len(scenarios)} 個測試情境")
    print(f"{'='*70}")
    print(f"  {'ID':<6} {'名稱':<30} {'步驟數':<6} {'預期報表項目'}")
    print(f"  {'-'*6} {'-'*30} {'-'*6} {'-'*30}")
    for s in scenarios:
        name = s["name"][:28]
        steps = len(s["steps"])
        items = ", ".join(s["expected_report_items"][:3])
        if len(s["expected_report_items"]) > 3:
            items += "..."
        print(f"  {s['id']:<6} {name:<30} {steps:<6} {items}")
    print(f"{'='*70}\n")


# ── 直接執行時印出摘要 ──
if __name__ == "__main__":
    scenarios = generate_all_scenarios()
    print_scenario_summary(scenarios)

    # 也輸出完整 JSON 供檢視
    import json
    with open("test_scenarios_output.json", "w", encoding="utf-8") as f:
        json.dump(scenarios, f, ensure_ascii=False, indent=2)
    print(f"已匯出完整情境定義至 test_scenarios_output.json")