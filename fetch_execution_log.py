"""
fetch_execution_log.py - 從 n8n API 下載執行 LOG
=================================================
透過 GET request 取得客服語音機器人的 Execution Log，
先移除個資（customerID、phone）後，再儲存為 VoiceBotServiceLog{Date}.json。

使用方式:
  python fetch_execution_log.py
  python fetch_execution_log.py --date 20260518
  python fetch_execution_log.py --output D:\\03_客服語音機器人
"""

import argparse
import json
import requests
from datetime import datetime
from pathlib import Path

WORKFLOW_ID = "mvmIg3oo45ZM5B9A"
WORKFLOW_URL = f"http://10.13.60.173:5670/api/v1/workflows/{WORKFLOW_ID}?excludePinnedData=true"
API_URL_TEMPLATE = (
        "http://10.13.60.173:5670/api/v1/executions"
        "?includeData=true"
        f"&workflowId={WORKFLOW_ID}"
        "&projectId={project_id}"
)

TIMEOUT_SECONDS = 60

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlNGNmZjQ1ZS0zYjgyLTQ5ODUtOTcxYy1jNjczZWFmYzdhMGYiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzgyNzk5MDU2fQ.fjBOqx9LPvw2KKoiJMLZlPUNfk1AnKgvo02OZN4gSDk"

# 需要去除的個資欄位名稱。scrub_pii 會遞迴掃整份 execution，
# 不論出現在哪一個節點、哪一層，只要 key 名稱在此集合中就移除。
PII_KEYS = frozenset({"customerID", "phone"})


def scrub_pii(obj, pii_keys=PII_KEYS):
    """遞迴移除任意層級中的個資欄位（就地修改並回傳同一物件）。

    n8n 的 runData 裡，customerID / phone 會散落在多個節點
    （receive_message_API、extract_intent、receive_confirmation... 等），
    因此以「key 名稱」為準遞迴清除，才能確保完整去個資，
    而不是只清單一條路徑。
    """
    if isinstance(obj, dict):
        for key in list(obj.keys()):
            if key in pii_keys:
                del obj[key]
            else:
                scrub_pii(obj[key], pii_keys)
    elif isinstance(obj, list):
        for item in obj:
            scrub_pii(item, pii_keys)
    return obj


def build_execution_api_url() -> str:
    """先查 workflow 取得 projectId，再組 execution API URL。"""
    headers = {"X-N8N-API-KEY": API_KEY}
    try:
        resp = requests.get(WORKFLOW_URL, headers=headers, timeout=TIMEOUT_SECONDS, verify=False)
        resp.raise_for_status()
        payload = resp.json()
    except requests.HTTPError as e:
        code = e.response.status_code if e.response is not None else "?"
        reason = e.response.reason if e.response is not None else str(e)
        raise RuntimeError(f"HTTP {code}: {reason}") from e
    except requests.RequestException as e:
        raise RuntimeError(f"連線失敗: {e}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"無法解析回應 JSON: {e}") from e

    shared = payload.get("shared") or []
    if not shared or not isinstance(shared, list):
        raise RuntimeError("workflow 回應缺少 shared 資料")

    project_id = shared[0].get("projectId", "")
    if not project_id:
        raise RuntimeError("workflow 回應缺少 projectId")

    return API_URL_TEMPLATE.format(project_id=project_id)


def fetch_one_page(url: str) -> dict:
    """對 n8n API 發出 GET request，回傳解析後的 JSON dict（單頁）。"""
    headers = {"X-N8N-API-KEY": API_KEY}
    try:
        resp = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS, verify=False)
        resp.raise_for_status()
    except requests.HTTPError as e:
        code = e.response.status_code if e.response is not None else "?"
        reason = e.response.reason if e.response is not None else str(e)
        raise RuntimeError(f"HTTP {code}: {reason}") from e
    except requests.RequestException as e:
        raise RuntimeError(f"連線失敗: {e}") from e

    try:
        return resp.json()
    except json.JSONDecodeError as e:
        raise RuntimeError(f"無法解析回應 JSON: {e}") from e


def fetch_execution_log(base_url: str, target_date: str | None = None) -> dict:
    """自動分頁抓取 execution，並可在抓取時按日期過濾與提前停止。

    target_date 格式為 YYYYMMDD。
    若提供 target_date，會在抓取每頁時先保留該日期資料，
    並在資料時間已早於目標日期時提前停止後續分頁請求。
    """
    all_executions = []
    url = base_url
    page = 1
    target_ymd = None

    if target_date:
        target_ymd = f"{target_date[:4]}-{target_date[4:6]}-{target_date[6:8]}"

    while True:
        print(f"  [PAGE {page}] GET {url[:80]}...")
        data = fetch_one_page(url)
        executions = data.get("data", [])

        stop_paging = False
        kept_in_page = 0
        for ex in executions:
            started_at = str(ex.get("startedAt", ""))
            date_ymd = started_at[:10]

            if target_ymd:
                if date_ymd == target_ymd:
                    all_executions.append(ex)
                    kept_in_page += 1
                elif date_ymd and date_ymd < target_ymd:
                    # API 通常以新到舊排序，碰到更早日期即可停止分頁。
                    stop_paging = True
            else:
                all_executions.append(ex)
                kept_in_page += 1

        print(
            f"  [PAGE {page}] 原始 {len(executions)} 筆，"
            f"保留 {kept_in_page} 筆，累計 {len(all_executions)} 筆"
        )

        if stop_paging:
            print(f"  [PAGE {page}] 偵測到早於 {target_ymd} 的資料，提前停止分頁")
            break

        next_cursor = data.get("nextCursor")
        if not next_cursor:
            break

        # 組裝下一頁 URL
        separator = "&" if "?" in base_url else "?"
        url = f"{base_url}{separator}cursor={next_cursor}"
        page += 1

    return {"data": all_executions}


def filter_by_date(data: dict, date_str: str) -> dict:
    """保留 startedAt 符合指定日期的執行紀錄。

    date_str 格式為 YYYYMMDD（與 --date 參數一致）。
    n8n startedAt 格式範例：2026-05-18T08:00:00.000Z
    """
    target = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    executions = data.get("data", [])
    filtered = [
        ex for ex in executions
        if str(ex.get("startedAt", "")).startswith(target)
    ]
    return {**data, "data": filtered}


def main():
    parser = argparse.ArgumentParser(description="從 n8n API 下載 Execution Log")
    parser.add_argument(
        "--date",
        default=datetime.now().strftime("%Y%m%d"),
        help="輸出檔名中的日期，格式 YYYYMMDD（預設：今天）",
    )
    parser.add_argument(
        "--output",
        default=str(Path(__file__).parent.parent / "DailyLog"),
        help="輸出目錄（預設：本腳本上一層的 DailyLog）",
    )
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"VoiceBotServiceLog_{args.date}.json"
    output_path = output_dir / filename

    print(f"[INFO] 正在查詢 workflow 資訊並組裝 execution API URL...")
    api_url = build_execution_api_url()

    print(f"[INFO] 正在向 n8n API 發出請求（自動分頁 + 抓取中日期篩選）...")
    data = fetch_execution_log(api_url, target_date=args.date)

    total = len(data.get("data", []))
    print(f"[INFO] 共取得 {total} 筆 execution")
    print(f"[INFO] 日期 {args.date} 最終保留 {total} 筆")

    # 寫檔前先去個資：遞迴移除所有 customerID / phone 欄位。
    scrub_pii(data)
    print(f"[INFO] 已移除個資欄位：{', '.join(sorted(PII_KEYS))}")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[INFO] 已儲存：{output_path}")


if __name__ == "__main__":
    main()
