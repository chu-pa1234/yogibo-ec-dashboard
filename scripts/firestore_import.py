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

FIELD_RENAME = {
    "SKU":    "sku",
    "商品名": "name",
    "UU":     "uu",
    "注文件数": "orders",
    "販売数量": "units",
    "売上金額": "revenue",
}

def normalize_sku(sku):
    """PRO- で始まるSKUを PRE- に統一"""
    if sku.upper().startswith('PRO-'):
        return 'PRE-' + sku[4:]
    return sku

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
    """SKUを正規化（PRO-→PRE-）してから同一 date+channel+SKU を合算"""
    merged = {}
    for row in rows:
        row = dict(row)
        row['SKU'] = normalize_sku(row.get('SKU', ''))
        if 'sku' in row:
            row['sku'] = normalize_sku(row.get('sku', ''))
        doc_id = make_doc_id(row)
        if doc_id not in merged:
            merged[doc_id] = row
        else:
            for col in INT_COLS:
                try:
                    merged[doc_id][col] = str(int(float(merged[doc_id].get(col) or 0)) + int(float(row.get(col) or 0)))
                except ValueError:
                    pass
    return merged

def write_doc(doc_id, fields, token, retries=3):
    url = f"{BASE_URL}/{COLLECTION}/{doc_id}"
    headers = {"Authorization": f"Bearer {token}"}
    for attempt in range(retries):
        try:
            resp = requests.patch(url, json={"fields": fields}, headers=headers, timeout=15)
            return resp.status_code in (200, 201)
        except requests.exceptions.ConnectionError:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                return False

def import_csv(path, token):
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print(f"  データなし: {path}")
        return

    deduped = aggregate_rows(rows)
    print(f"  {len(rows)}行 → 重複合算後 {len(deduped)}件")

    success = 0
    errors  = 0
    for i, (doc_id, row) in enumerate(deduped.items(), 1):
        fields = {FIELD_RENAME.get(k, k): to_firestore_value(k, v) for k, v in row.items()}
        if write_doc(doc_id, fields, token):
            success += 1
        else:
            errors += 1
        if i % 100 == 0:
            print(f"    {i}/{len(deduped)}件...")
        time.sleep(0.02)

    print(f"  完了: {success}件成功 / {errors}件失敗 → Firestore")

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
