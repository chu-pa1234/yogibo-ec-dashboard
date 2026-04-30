"""
Amazon セラーセントラル 日別CSVを結合してダッシュボード用CSVに変換するスクリプト

使い方:
  python amazon_merge.py --folder "C:/Users/d.nakamura/Downloads/AMZ"

オプション:
  --folder  CSVファイルが入っているフォルダのパス
  --out     出力ファイルパス (省略時: フォルダ内に amazon_merged.csv を作成)
"""

import csv
import glob
import os
import re
import argparse

COLUMN_MAP = {
    "（親）ASIN":         "SKU",
    "タイトル":            "商品名",
    "セッション数 - 合計": "UU",
    "注文品目総数":         "注文件数",
    "注文商品の売上額":     "売上金額",
    "注文された商品点数":   "販売数量",
}

def clean_number(val):
    return re.sub(r"[￥¥,%\s]", "", val)

def extract_date(filename):
    """ファイル名から日付を抽出: BusinessReport-26-04-30.csv → 2026-04-30"""
    m = re.search(r"-(\d{2})-(\d{2})-(\d{2})\.csv$", filename)
    if not m:
        return None
    yy, month, day = m.group(1), m.group(2), m.group(3)
    return f"20{yy}-{month}-{day}"

def process_files(folder, out_path):
    files = sorted(glob.glob(os.path.join(folder, "*.csv")))
    files = [f for f in files if os.path.basename(f) != os.path.basename(out_path)]

    if not files:
        print(f"CSVファイルが見つかりません: {folder}")
        return

    rows_out = []
    for fpath in files:
        fname = os.path.basename(fpath)
        data_date = extract_date(fname)
        if not data_date:
            print(f"  スキップ（日付を抽出できません）: {fname}")
            continue
        print(f"  {fname} → {data_date}")

        with open(fpath, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                out = {"date": data_date, "channel": "amazon"}
                for src_col, dst_col in COLUMN_MAP.items():
                    val = row.get(src_col, "").strip()
                    if dst_col in ("UU", "注文件数", "販売数量", "売上金額"):
                        val = clean_number(val)
                    out[dst_col] = val
                rows_out.append(out)

    if not rows_out:
        print("変換できる行がありませんでした")
        return

    fieldnames = ["date", "channel", "SKU", "商品名", "UU", "注文件数", "販売数量", "売上金額"]
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"\n完了: {len(rows_out)}行 → {out_path}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", required=True)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    out_path = args.out or os.path.join(args.folder, "amazon_merged.csv")
    print(f"処理開始: {args.folder}\n")
    process_files(args.folder, out_path)

if __name__ == "__main__":
    main()
