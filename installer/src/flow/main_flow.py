import time
import random
from typing import List, Dict, Any
import pandas as pd
import logging

from installer.src.flow.base.chrome import Chrome
from installer.src.flow.base.spreadsheet_read import SpreadsheetReader
from installer.src.flow.base.url_builder import UrlBuilder
from installer.src.utils.text_utils import NumExtractor
from installer.src.flow.base.utils import DateConverter
from installer.src.flow.base.number_calculator import PriceCalculator
from installer.src.flow.base.selenium_manager import Selenium
from installer.src.flow.detail_page_flow import DetailPageFlow
from installer.src.flow.base.spreadsheet_write import SpreadsheetWriter
from installer.src.flow.write_gss_flow import WriteGssFlow
from flow.base.image_downloader import ImageDownloader
from selenium.webdriver.common.by import By
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


logger = logging.getLogger(__name__)



def random_sleep(min_seconds=0.5, max_seconds=1.5):
    sleep_time = random.uniform(min_seconds, max_seconds)
    logger.debug(f"ランダムスリープ: {sleep_time:.2f}秒")
    time.sleep(sleep_time)

class Config:
    SPREADSHEET_ID = "1nRJh0BqQazHe8qgT2YTZbMaZ9osPX835CbM3KkUjkcE"
    SEARCH_COND_SHEET = "Master"
    DATA_OUTPUT_SHEET = "1"

class MainFlow:
    def __init__(self, config: Config):
        self.config = config
        self.logger = logger

    def test_num_extractor(self, text: str) -> None:
        try:
            ct_value = NumExtractor.extract_ct_value(text)
            self.logger.info(f"カラット抽出: 型={type(ct_value)} | 値={ct_value}")
        except Exception as e:
            self.logger.error(f"NumExtractor抽出失敗: {e}")

    def load_search_conditions(self) -> List[Dict[str, Any]]:
        try:
            reader = SpreadsheetReader(
                spreadsheet_id=self.config.SPREADSHEET_ID,
                worksheet_name=self.config.SEARCH_COND_SHEET
            )
            self.logger.info(f"スプレッドシート({self.config.SPREADSHEET_ID})から検索条件取得")
            conditions = reader.get_search_conditions()
            self.logger.info(f"取得件数: {len(conditions)}件")
            return conditions
        except Exception as e:
            self.logger.error(f"スプレッドシート読込中エラー: {e}")
            return []

    def write_test_data(self, worksheet) -> None:
        test_data = [
            {
                "date": "2025-06-27",
                "title": "ダイヤ ルース 0.500ct 鑑定書付き",
                "price": 51700,
                "ct": 0.500,
                "1ct_price": 84100,
                "image": "https://auctions.c.yimg.jp/images.auctions.yahoo.co.jp/image/dr000/auc0106/user/5ec807c934150c37fea5b1cda6cdb4938dea1bcdd982696a3d9c90b59c549314/i-img1200x849-17500560233691ls9baa33.jpg"
            },
            {
                "date": "2025-06-28",
                "title": "ダイヤモンドルース 0.200ct 新品",
                "price": 20000,
                "ct": 0.200,
                "1ct_price": 32600,
                "image": "https://auctions.c.yimg.jp/images.auctions.yahoo.co.jp/image/dr000/auc0106/user/5ec807c934150c37fea5b1cda6cdb4938dea1bcdd982696a3d9c90b59c549314/i-img1200x849-17500560233691ls9baa33.jpg"
            }
        ]
        try:
            flow = WriteGssFlow(worksheet)
            flow.run(test_data)
            self.logger.info("テストデータ一括書き込み成功")
        except Exception as e:
            self.logger.error(f"テストデータ書き込み失敗: {e}")

    def extract_keyword(self, row: Dict[str, Any]) -> str:
        return " ".join([str(row.get(f"search_{i}", "")) for i in range(1, 6)]).strip()

    def url_and_selenium_flow(self, conditions: List[Dict[str, Any]]) -> None:
        if not conditions:
            self.logger.warning("条件が空なのでURL生成処理スキップ")
            return

        df = pd.DataFrame(conditions)
        df = df[df["start_date"].astype(str).str.strip() != ""]
        df = df[df["end_date"].astype(str).str.strip() != ""]

        url_builder = UrlBuilder()

        # --- ここで一度だけChromeDriverを起動 ---
        driver = Chrome.get_driver()
        selenium_util = Selenium(driver)

        for idx, row in df.iterrows():
            try:
                start_date = DateConverter.convert(row.get("start_date"))
                end_date = DateConverter.convert(row.get("end_date"))
            except Exception as e:
                self.logger.error(f"{idx+1}行目: 開始・終了日変換失敗: {e}")
                continue

            keyword = self.extract_keyword(row)
            if not keyword:
                self.logger.warning(f"{idx+1}行目: キーワードなし。スキップ")
                continue

            search_url = url_builder.build_url(keyword)
            self.logger.info(f"{idx+1}行目: キーワード={keyword} | URL={search_url}")

            # driver = Chrome.get_driver()
            # selenium_util = Selenium(driver)
            driver.get(search_url)
            random_sleep()

            # 例: 「落札相場」ボタンのセレクタを指定
            wait = WebDriverWait(driver, 10)
            try:
                elem = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".Auction__pastAuctionBtn")))
                elem.click()
                random_sleep()
            except Exception as e:
                self.logger.warning(f"落札相場ボタン押下失敗: {e}")

            random_sleep()
            detail_urls = []

# =============================== ページ巡回しながら全件収集 ===============================
            # 商品URL取得（最初の1件のみ）
            try:
                urls = selenium_util.get_auction_urls()
                first_url = urls[0] if urls else None
                detail_urls = [first_url] if first_url else []
            except Exception as e:
                self.logger.warning(f"商品URL取得失敗: {e}")
                detail_urls = []
# =============================== ページ巡回しながら全件収集 ===============================
            # detail_urls = []

            # while True:
            #     try:
            #         end_times = selenium_util.get_auction_end_dates()
            #         urls = selenium_util.get_auction_urls()
            #     except Exception as e:
            #         self.logger.warning(f"{idx+1}行目: 商品URLまたは終了日時取得失敗: {e}")
            #         break

            #     for end_time, url in zip(end_times, urls):
            #         try:
            #             end_date_only = DateConverter.convert(end_time)
            #         except Exception as e:
            #             self.logger.warning(f"{idx+1}行目: 日付変換失敗: {e}")
            #             continue

            #         if end_date_only < start_date:
            #             break  # 残りは古いので打ち切り
            #         elif end_date_only > end_date:
            #             continue  # 期間外はスキップ
            #         else:
            #             detail_urls.append(url)

            #     # 次ページがあれば進む
            #     try:
            #         has_next = selenium_util.click_next()
            #         if not has_next:
            #             break
            #         random_sleep()
            #     except Exception as e:
            #         self.logger.warning(f"{idx+1}行目: 次へクリック失敗または次ページなし: {e}")
            #         break
# ======================================================================================








            if not detail_urls:
                self.logger.info(f"{idx+1}行目: 対象期間内の商品なし")
                driver.quit()
                continue




            if not detail_urls:
                self.logger.info(f"{idx+1}行目: 対象期間内の商品なし")
                # driver.quit()
                continue

            details = []
            for detail_url in detail_urls:
                try:
                    detail_flow = DetailPageFlow(driver, selenium_util)
                    detail_data = detail_flow.extract_detail(detail_url)
                    details.append(detail_data)
                    self.logger.info(f"{idx+1}行目: 詳細抽出成功: {detail_url}")
                    random_sleep()
                except Exception as e:
                    self.logger.warning(f"{idx+1}行目: 詳細抽出失敗 {detail_url}: {e}")

            # driver.quit()

            try:
                keys = ["date", "title", "price", "ct", "1ct_price", "image"]
                list_of_lists = [[d.get(k, "") for k in keys] for d in details]

                # ★ここでlist_of_listsの中身を確認
                print("list_of_lists:", list_of_lists)  # または logger.debug("list_of_lists: %s", list_of_lists)

                # reader = SpreadsheetReader(self.config.SPREADSHEET_ID, row.get("ws_name", self.config.DATA_OUTPUT_SHEET))
                # worksheet = reader.get_worksheet(row.get("ws_name", self.config.DATA_OUTPUT_SHEET))

                output_sheet_name = "1"
                reader = SpreadsheetReader(self.config.SPREADSHEET_ID, output_sheet_name)
                worksheet = reader.get_worksheet(output_sheet_name)


                # ★worksheetの中身も確認
                print("worksheet:", worksheet)  # または logger.debug("worksheet: %s", worksheet)

                writer = SpreadsheetWriter(worksheet)
                result = writer.append_rows(list_of_lists)

                # ★append_rowsの戻り値も確認
                print("append_rows result:", result)  # または logger.debug("append_rows result: %s", result)

                self.logger.info(f"{idx+1}行目: スプレッドシートに詳細情報を追記しました。件数: {len(details)}")
            except Exception as e:
                self.logger.error(f"{idx+1}行目: スプレッドシート書き込み失敗", exc_info=True)

    def test_date_converter(self, sample_end_time: str) -> None:
        try:
            converted_date = DateConverter.convert(sample_end_time)
            self.logger.info(f"日付変換: 型={type(converted_date)} | 値={converted_date}")
        except Exception as e:
            self.logger.error(f"DateConverter変換テストでエラー: {e}")

    def test_price_calculator(self, title: str, price: int) -> None:
        try:
            price_per_ct = PriceCalculator.calculate_price_per_carat(title, price)
            self.logger.info(f"タイトル: {title} / 落札価格: {price} → 1ct単価: {price_per_ct} 円/ct")
        except Exception as e:
            self.logger.error(f"PriceCalculatorテスト失敗: {e}")

    def test_image_downloader(self) -> None:
        try:
            image_url = "https://auctions.c.yimg.jp/images.auctions.yahoo.co.jp/image/dr000/auc0106/user/5ec807c934150c37fea5b1cda6cdb4938dea1bcdd982696a3d9c90b59c549314/i-img1200x849-17500560233691ls9baa33.jpg"
            formula = ImageDownloader.get_image_formula(image_url)
            self.logger.info(f"ImageDownloaderテスト成功: {formula}")
            print(f"IMAGE式: {formula}")
        except Exception as e:
            self.logger.error("ImageDownloaderテスト失敗", exc_info=True)
            print("画像ダウンロード失敗:", e)

    def run(self) -> None:
        self.logger.info("プログラム開始")

        # self.test_num_extractor(
        #     "【6/27(金)】天然イエローダイヤモンド ルース 0.461ct LY VS2 鑑別 CGL│A4116mx 【0.4ct】 ダイヤ diamond"
        # )

        conditions = self.load_search_conditions()
        if not conditions:
            self.logger.error("検索条件取得失敗または空。以降の処理中断。")
            return

        reader = SpreadsheetReader(self.config.SPREADSHEET_ID, self.config.SEARCH_COND_SHEET)
        worksheet = reader.get_worksheet(self.config.DATA_OUTPUT_SHEET)
        # self.write_test_data(worksheet)

        self.url_and_selenium_flow(conditions)

        # self.test_date_converter("06/27 22:13")
        # self.test_price_calculator("天然ダイヤ 0.508ct F VS2", 51700)
        # self.test_image_downloader()

        self.logger.info("プログラム終了")