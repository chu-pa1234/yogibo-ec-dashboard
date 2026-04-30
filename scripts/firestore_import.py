"""
結合済みCSVをFirestoreに直接インポートするスクリプト

使い方:
  python firestore_import.py --csv "C:/path/to/merged.csv"
  python firestore_import.py --csv "amazon_merged.csv" --csv "yahoo_merged.csv"

前提:
  pip install requests
"""

import csv
import argparse
import requests
import sys
import io
import time
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROJECT_ID = "yogibo-ecmall-dashboad-f1610"
API_KEY    = "AIzaSyBDnQEypk4i7QU15qKbR1AGKAHZ0qkMgK0"
COLLECTION = "ec_data"
BATCH_SIZE = 500

BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"
DOC_PATH = f"projects/{PROJECT_ID}/databases/(default)/documents/{COLLECTION}"
AUTH_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API_KEY}"

INT_COLS = {"UU", "注文件数", "販売数量", "売上金額"}

def get_auth_token():
    """Firebase 匿名認証でIDトークンを取得"""
    resp = requests.post(AUTH_URL, json={"returnSecureToken": True}, timeout=10)
    resp.raise_for_status()
    token = resp.json().get("idToken")
    print(f"  認証OK")
    return token

def to_firestore_value(key, val):
    if key in INT_COLS:
        try:
            return {"integerValue": str(int(float(val or 0)))}
        except ValueError:
            return {"integerValue": "0"}
    return {"stringValue": str(val or "")}

def make_doc_id(row):
    return f"{row['date']}_{row['channel']}_{row['SKU']}".replace("/", "_").replace(" ", "_")

def aggregate_rows(rows):
    """同一 date+channel+SKU の行を合算してユニーク化"""
    merged = {}
    for row in rows:
        doc_id = make_doc_id(row)
        if doc_id not in merged:
            merged[doc_id] = dict(row)
        else:
            for col in INT_COLS:
                try:
                    merged[doc_id][col] = str(int(float(merged[doc_id].get(col) or 0)) + int(float(row.get(col) or 0)))
                except ValueError:
                    pass
    return merged

def batch_write(writes, token):
    url = f"{BASE_URL}:batchWrite?key={API_KEY}"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.post(url, json={"writes": writes}, headers=headers, timeout=30)
    if resp.status_code not in (200, 201):
        print(f"  [エラー] {resp.status_code}: {resp.text[:200]}")
        return False
    return True

def import_csv(path, token):
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print(f"  データなし: {path}")
        return

    deduped = aggregate_rows(rows)
    print(f"  {len(rows)}行 → 重複合算後 {len(deduped)}件")

    writes = []
    success = 0

    for doc_id, row in deduped.items():
        fields = {k: to_firestore_value(k, v) for k, v in row.items()}
        writes.append({
            "update": {
                "name": f"{DOC_PATH}/{doc_id}",
                "fields": fields
            }
        })

        if len(writes) >= BATCH_SIZE:
            if batch_write(writes, token):
                success += len(writes)
                print(f"    {success}/{len(deduped)}件...")
            writes = []
            time.sleep(0.2)

    if writes:
        if batch_write(writes, token):
            success += len(writes)

    print(f"  完了: {success}/{len(deduped)}件 → Firestore")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", action="append", required=True)
    args = parser.parse_args()

    print("Firebase 認証中...")
    token = get_auth_token()

    for path in args.csv:
        print(f"\nインポート: {path}")
        import_csv(path, token)

if __name__ == "__main__":
    main()
