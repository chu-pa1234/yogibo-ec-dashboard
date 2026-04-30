"""
Yahoo!ショッピング 日別CSVを結合してダッシュボード用CSVに変換するスクリプト

使い方:
  python yahoo_merge.py --folder "C:/Users/d.nakamura/Downloads/PPM"

オプション:
  --folder  CSVファイルが入っているフォルダのパス
  --out     出力ファイルパス（省略時: フォルダ内に yahoo_merged.csv を作成）

ファイル名ルール:
  yogibo-store-item_report_YYMMDD.csv
  例: yogibo-store-item_report_260429.csv → 2026-04-29
"""

import csv
import glob
import os
import re
import argparse

COLUMN_MAP = {
    "商品コード":       "SKU",
    "商品名":           "商品名",
    "訪問者数":         "UU",
    "注文数合計":        "注文件数",
    "注文点数合計":      "販売数量",
    "売上合計値（税込）": "売上金額",
}

def extract_date(filename):
    """ファイル名から日付を抽出: yogibo-store-item_report_260429.csv → 2026-04-29"""
    m = re.search(r"_(\d{2})(\d{2})(\d{2})\.csv$", filename)
    if not m:
        return None
    yy, mm, dd = m.group(1), m.group(2), m.group(3)
    return f"20{yy}-{mm}-{dd}"

def clean_number(val):
    """数値以外を除去（集計対象外 → 0）"""
    cleaned = re.sub(r"[^\d.]", "", val)
    return cleaned if cleaned else "0"

def process_files(folder, out_path):
    files = sorted(glob.glob(os.path.join(folder, "*.csv")))
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

        with open(fpath, encoding="shift-jis", errors="replace") as f:
            reader = csv.DictReader(f)
            day_rows = 0
            for row in reader:
                # サブコードなし行のみ使用（商品コード単位の集計行）
                if row.get("サブコード", "").strip():
                    continue

                out = {"date": data_date, "channel": "yahoo"}
                for src_col, dst_col in COLUMN_MAP.items():
                    val = row.get(src_col, "").strip()
                    if dst_col in ("UU", "注文件数", "販売数量", "売上金額"):
                        val = clean_number(val)
                    out[dst_col] = val
                rows_out.append(out)
                day_rows += 1

        print(f"  {fname} → {data_date} ({day_rows}行)")

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

    out_path = args.out or os.path.join(args.folder, "yahoo_merged.csv")
    print(f"処理開始: {args.folder}\n")
    count = process_files(args.folder, out_path)
    if count:
        print(f"\n完了: {count}行 → {out_path}")

if __name__ == "__main__":
    main()
