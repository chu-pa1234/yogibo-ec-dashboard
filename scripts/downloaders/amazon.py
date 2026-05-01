"""Amazon セラーセントラル Japan ダウンローダー"""

import os
from datetime import datetime, timedelta
from .base import BaseDownloader


class AmazonDownloader(BaseDownloader):
    channel_id   = "amazon"
    channel_name = "Amazon"
    login_url    = "https://sellercentral-japan.amazon.com/"
    check_url    = "https://sellercentral-japan.amazon.com/business-reports/"
    check_success = "sellercentral-japan.amazon.com/business-reports"

    REPORT_URL = (
        "https://sellercentral-japan.amazon.com/business-reports/"
        "ref=xx_sitemetric_favb_xx#/report"
        "?id=102%3ADetailSalesTrafficByParentItem"
        "&chartCols=&columns=0%2F1%2F2%2F7%2F8%2F13%2F14"
        "%2F19%2F20%2F25%2F26%2F27%2F28%2F29%2F30%2F31%2F32%2F33%2F34%2F35%2F36"
    )

    async def download(self, start_date: str, end_date: str, out_dir: str) -> list[str]:
        s = datetime.strptime(start_date, "%Y-%m-%d").date()
        e = datetime.strptime(end_date,   "%Y-%m-%d").date()

        ctx = await self._launch(headless=True)
        page = await ctx.new_page()
        saved = []

        d = s
        while d <= e:
            ymd = d.strftime("%Y年%m月%d日")
            print(f"  [Amazon] {ymd} をダウンロード中...")

            try:
                url = f"{self.REPORT_URL}&fromDate={d.isoformat()}&toDate={d.isoformat()}"
                await page.goto(url, wait_until="domcontentloaded", timeout=40_000)
                await page.wait_for_timeout(5_000)

                # ダウンロードボタン
                yy = str(d.year)[2:]
                mm = str(d.month).zfill(2)
                dd = str(d.day).zfill(2)
                out_name = f"BusinessReport-{yy}-{mm}-{dd}.csv"
                out_path = os.path.join(out_dir, out_name)

                async with page.expect_download(timeout=30_000) as dl_info:
                    await page.get_by_role("button", name="Download").click()
                dl = await dl_info.value
                await dl.save_as(out_path)
                saved.append(out_path)
                print(f"    → 保存: {os.path.basename(out_path)}")

            except Exception as ex:
                print(f"    [警告] {ymd} 失敗: {ex}")

            d += timedelta(days=1)

        await self.close()
        return saved
