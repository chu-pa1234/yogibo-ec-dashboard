"""
楽天 商品分析CSVを結合してダッシュボード用CSVに変換するスクリプト

使い方:
  python rakuten_merge.py --folder "C:/Users/d.nakamura/Downloads/RKT"

オプション:
  --folder  CSVファイルが入っているフォルダのパス
  --out     出力ファイルパス（省略時: フォルダ内に rakuten_merged.csv を作成）

ファイル名ルール:
  YYYYMMDD_item_list.csv（リネーム不要）
  例: 20260421_item_list.csv → 2026-04-21
"""

import csv
import glob
import os
import re
import argparse

HEADER_ROW = 5  # 0始まり: 6行目がヘッダー

COLUMN_MAP = {
    "商品管理番号": "SKU",
    "商品名":       "商品名",
    "ユニークユーザー数": "UU",
    "売上件数":     "注文件数",
    "売上個数":     "販売数量",
    "売上":         "売上金額",
}

def extract_date(filename):
    """ファイル名から日付を抽出: 20260421_item_list.csv → 2026-04-21"""
    m = re.search(r"(\d{4})(\d{2})(\d{2})_item_list", filename)
    if not m:
        return None
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

def clean_number(val):
    return re.sub(r"[^\d.]", "", val) or "0"

def process_files(folder, out_path):
    files = sorted(glob.glob(os.path.join(folder, "*_item_list.csv")))
    files = [f for f in files if os.path.basename(f) != os.path.basename(out_path)]

    if not files:
        print(f"CSVファイルが見つかりません: {folder}")
        return 0

    rows_out = []
    for fpath in files:
        fname = os.path.basename(fpath)
        data_date = extract_date(fname)
        if not data_date:
            print(f"  スキップ（日付を抽出できません）: {fname}")
            continue

        with open(fpath, encoding="utf-8-sig") as f:
            all_rows = list(csv.DictReader(f, fieldnames=None))

        # 先頭5行はメタ情報 → スキップ、6行目がヘッダー
        with open(fpath, encoding="utf-8-sig") as f:
            raw = list(csv.reader(f))

        if len(raw) < HEADER_ROW + 2:
            continue

        headers = raw[HEADER_ROW]
        data_rows = raw[HEADER_ROW + 1:]

        day_rows = 0
        aggregated = {}
        for row in data_rows:
            if not row or not row[0].strip().isdigit():
                continue
            rec = dict(zip(headers, row))
            out = {"date": data_date, "channel": "rakuten"}
            for src, dst in COLUMN_MAP.items():
                val = rec.get(src, "").strip()
                if dst in ("UU", "注文件数", "販売数量", "売上金額"):
                    val = clean_number(val)
                out[dst] = val

            # 同一代表コードを集計
            key = (data_date, "rakuten", out["SKU"])
            if key not in aggregated:
                aggregated[key] = dict(out)
            else:
                for col in ("UU", "注文件数", "販売数量", "売上金額"):
                    aggregated[key][col] = str(int(aggregated[key].get(col) or 0) + int(out.get(col) or 0))
            day_rows += 1

        rows_out.extend(aggregated.values())
        print(f"  {fname} → {data_date} ({len(aggregated)}件)")

    if not rows_out:
        print("変換できる行がありませんでした")
        return 0

    fieldnames = ["date", "channel", "SKU", "商品名", "UU", "注文件数", "販売数量", "売上金額"]
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    return len(rows_out)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", required=True)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    out_path = args.out or os.path.join(args.folder, "rakuten_merged.csv")
    print(f"処理開始: {args.folder}\n")
    count = process_files(args.folder, out_path)
    if count:
        print(f"\n完了: {count}行 → {out_path}")

if __name__ == "__main__":
    main()
