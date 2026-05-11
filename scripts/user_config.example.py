from pathlib import Path

# Downloads フォルダを自動解決（ユーザー名のハードコード不要）
_DL = Path.home() / "Downloads"

# ダウンロード先フォルダ（各チャネルのCSV保存先）
DOWNLOAD_DIRS = {
    "amazon":  str(_DL / "AMZ"),
    "yahoo":   str(_DL / "PPM"),
    "rakuten": str(_DL / "RKT"),
    "own_ec":  str(_DL / "SPF"),
}

# マッピングファイルのパス
AMAZON_MAPPING_FILE  = str(_DL / "Amazon代表コードと親ASIN突合せ表.xlsx")
SHOPIFY_MAPPING_FILE = str(_DL / "Book2.csv")
