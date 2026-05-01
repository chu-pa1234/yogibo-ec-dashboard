"""楽天 RMS データツール ダウンローダー"""

import os
from datetime import datetime, timedelta
from .base import BaseDownloader


class RakutenDownloader(BaseDownloader):
    channel_id   = "rakuten"
    channel_name = "楽天"
    login_url    = "https://glogin.rms.rakuten.co.jp/"
    check_url    = "https://datatool.rms.rakuten.co.jp/access/item"
    check_success = "datatool.rms.rakuten.co.jp"

    async def download(self, start_date: str, end_date: str, out_dir: str) -> list[str]:
        """日別にCSVをダウンロード"""
        from datetime import date as dt_date
        s = datetime.strptime(start_date, "%Y-%m-%d").date()
        e = datetime.strptime(end_date,   "%Y-%m-%d").date()

        ctx = await self._launch(headless=True)
        page = await ctx.new_page()
        saved = []

        d = s
        while d <= e:
            date_str = d.strftime("%Y%m%d")
            ymd = d.strftime("%Y年%m月%d日")
            print(f"  [楽天] {ymd} をダウンロード中...")

            try:
                url = (
                    f"https://datatool.rms.rakuten.co.jp/access/item"
                    f"?startDate={d.strftime('%Y-%m-%d')}"
                    f"&endDate={d.strftime('%Y-%m-%d')}"
                )
                await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                await page.wait_for_timeout(3_000)

                # CSV ダウンロードボタンをクリック
                async with page.expect_download(timeout=30_000) as dl_info:
                    await page.get_by_role("button", name="CSVダウンロード").first.click()
                dl = await dl_info.value

                out_path = os.path.join(out_dir, f"{date_str}_item_list.csv")
                await dl.save_as(out_path)
                saved.append(out_path)
                print(f"    → 保存: {os.path.basename(out_path)}")

            except Exception as ex:
                print(f"    [警告] {ymd} 失敗: {ex}")

            d += timedelta(days=1)

        await self.close()
        return saved
