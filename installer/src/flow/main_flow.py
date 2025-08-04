# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$%$$$$$$$$$$$$$$$$$$$
# import
import logging
from typing import List, Dict, Any
import pandas as pd

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

logger = logging.getLogger(__name__)
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

# **********************************************************************************
# class定義

class Config:
    # スプレッドシートID、検索条件シート名、出力先シート名の設定
    SPREADSHEET_ID = "1nRJh0BqQazHe8qgT2YTZbMaZ9osPX835CbM3KkUjkcE"
    SEARCH_COND_SHEET = "Master"
    DATA_OUTPUT_SHEET = "1"

# ------------------------------------------------------------------------------
# class定義
class MainFlow:
    def __init__(self, config: Config):
        # コンストラクタ：設定情報を保持しロガーを初期化
        self.config = config
        self.logger = logger

    # ------------------------------------------------------------------------------
    # カラット数抽出テスト関数
    def test_num_extractor(self, text: str) -> None:
        # テキストからカラット数を抽出し、型と値をログに出力することで抽出ロジックを検証
        try:
            ct_value = NumExtractor.extract_ct_value(text)
            self.logger.info(f"カラット抽出: 型={type(ct_value)} | 値={ct_value}")
        except Exception as e:
            self.logger.error(f"NumExtractor抽出失敗: {e}")

    # ------------------------------------------------------------------------------
    # スプレッドシートから検索条件を取得する関数
    def load_search_conditions(self) -> List[Dict[str, Any]]:
        # Googleスプレッドシートの指定シートから検索条件を辞書リスト形式で取得し、取得件数をログに出す
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

    # ------------------------------------------------------------------------------
    # テストデータを指定ワークシートへ一括書き込みする関数
    def write_test_data(self, worksheet) -> None:
        # テスト用のサンプルデータを作成し、一括書き込み用フローを利用してGoogleスプレッドシートに書き込み
        # 書き込み成功・失敗結果をログ出力
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

    # ------------------------------------------------------------------------------
    # キーワード抽出関数
    def extract_keyword(self, row: Dict[str, Any]) -> str:
        # 1行の検索ワードカラム（search_1～search_5）を空白区切りで連結してキーワード文字列を生成し返却
        return " ".join([str(row.get(f"search_{i}", "")) for i in range(1, 6)]).strip()

    # ------------------------------------------------------------------------------
    # URL生成とSeleniumによるページ情報取得フロー
    def url_and_selenium_flow(self, conditions: List[Dict[str, Any]]) -> None:
        # 検索条件が空なら処理中断
        if not conditions:
            self.logger.warning("条件が空なのでURL生成処理スキップ")
            return

        url_builder = UrlBuilder()
        df = pd.DataFrame(conditions)

        # 取得した条件を1行ずつ処理
        for idx, row in df.iterrows():
            # 開始日・終了日をDateConverterで変換（日付型に）
            try:
                start_date = DateConverter.convert(row.get("start_date"))
                end_date = DateConverter.convert(row.get("end_date"))
            except Exception as e:
                self.logger.error(f"{idx+1}行目: 開始・終了日変換失敗: {e}")
                continue

            # 検索ワードを連結してキーワード生成
            keyword = self.extract_keyword(row)
            if not keyword:
                self.logger.warning(f"{idx+1}行目: キーワードなし。スキップ")
                continue

            # 検索用URL生成
            search_url = url_builder.build_url(keyword)
            self.logger.info(f"{idx+1}行目: キーワード={keyword} | URL={search_url}")

            # Chromeドライバ起動
            driver = Chrome.get_driver()
            selenium_util = Selenium(driver)
            driver.get(search_url)

            detail_urls = []  # 対象期間内の詳細URLリスト

            while True:
                # 商品一覧から終了日時取得（日付変換し対象期間内判定）
                try:
                    end_times = selenium_util.get_auction_end_dates()
                except Exception as e:
                    self.logger.warning(f"{idx+1}行目: 終了日時取得失敗: {e}")
                    break

                # 対象商品の詳細URLを商品一覧から取得
                try:
                    urls = selenium_util.get_auction_urls()
                except Exception as e:
                    self.logger.warning(f"{idx+1}行目: 商品URL取得失敗: {e}")
                    break

                # 取得した終了日時ごとに期間判定し、期間内の詳細URLを収集
                period_matched = False
                for end_time, url in zip(end_times, urls):
                    try:
                        end_date_only = DateConverter.convert(end_time)
                    except Exception as e:
                        self.logger.warning(f"{idx+1}行目: 日付変換失敗: {e}")
                        continue

                    if end_date_only < start_date:
                        # 開始日より前なら処理終了（breakループ）
                        period_matched = False
                        break
                    elif end_date_only > end_date:
                        # 終了日より後ならスキップ（continue）
                        continue
                    else:
                        # 期間内なのでURLを追加
                        detail_urls.append(url)
                        period_matched = True

                if not period_matched:
                    # 期間内の商品が無ければ終了
                    break

                # 「次へ」ボタンがあればクリックして次ページへ
                try:
                    has_next = selenium_util.click_next()
                    if not has_next:
                        break
                except Exception as e:
                    self.logger.warning(f"{idx+1}行目: 次へクリック失敗または次ページなし: {e}")
                    break

            # 詳細URLリストが空なら次の行へ
            if not detail_urls:
                self.logger.info(f"{idx+1}行目: 対象期間内の商品なし")
                driver.quit()
                continue

            # DetailPageFlowで詳細情報を抽出しリストに格納
            details = []
            for detail_url in detail_urls:
                try:
                    detail_flow = DetailPageFlow(driver, selenium_util)
                    detail_data = detail_flow.extract_detail(detail_url)
                    details.append(detail_data)
                    self.logger.info(f"{idx+1}行目: 詳細抽出成功: {detail_url}")
                except Exception as e:
                    self.logger.warning(f"{idx+1}行目: 詳細抽出失敗 {detail_url}: {e}")

            driver.quit()

# ここに追加↓
            try:
                # 書き込みたいカラムキーの順番を指定
                keys = ["date", "title", "price", "ct", "1ct_price", "image"]

                # 辞書リストをリストのリストに変換
                list_of_lists = [[d.get(k, "") for k in keys] for d in details]

                reader = SpreadsheetReader(self.config.SPREADSHEET_ID, row.get("ws_name", self.config.DATA_OUTPUT_SHEET))
                worksheet = reader.get_worksheet(row.get("ws_name", self.config.DATA_OUTPUT_SHEET))
                writer = SpreadsheetWriter(worksheet)
                writer.append_rows(list_of_lists)  # ここにリストのリストを渡す
                self.logger.info(f"{idx+1}行目: スプレッドシートに詳細情報を追記しました。件数: {len(details)}")
            except Exception as e:
                self.logger.error(f"{idx+1}行目: スプレッドシート書き込み失敗: {e}")
# ここまで追加↑

            # # 取得した詳細情報をSpreadsheetWriterでまとめて書き込み
            # try:
            #     reader = SpreadsheetReader(self.config.SPREADSHEET_ID, row.get("ws_name", self.config.DATA_OUTPUT_SHEET))
            #     worksheet = reader.get_worksheet(row.get("ws_name", self.config.DATA_OUTPUT_SHEET))
            #     writer = SpreadsheetWriter(worksheet)
            #     writer.append_rows(details)
            #     self.logger.info(f"{idx+1}行目: スプレッドシートに詳細情報を追記しました。件数: {len(details)}")
            # except Exception as e:
            #     self.logger.error(f"{idx+1}行目: スプレッドシート書き込み失敗: {e}")

    # ------------------------------------------------------------------------------
    # 日付変換テスト関数
    def test_date_converter(self, sample_end_time: str) -> None:
        # 指定された日時文字列をDateConverterで変換し、型と値をログに出力
        try:
            converted_date = DateConverter.convert(sample_end_time)
            self.logger.info(f"日付変換: 型={type(converted_date)} | 値={converted_date}")
        except Exception as e:
            self.logger.error(f"DateConverter変換テストでエラー: {e}")

    # ------------------------------------------------------------------------------
    # 1ct単価計算テスト関数
    def test_price_calculator(self, title: str, price: int) -> None:
        # 指定のタイトルと価格から1カラットあたりの単価を計算し結果をログ出力
        try:
            price_per_ct = PriceCalculator.calculate_price_per_carat(title, price)
            self.logger.info(f"タイトル: {title} / 落札価格: {price} → 1ct単価: {price_per_ct} 円/ct")
        except Exception as e:
            self.logger.error(f"PriceCalculatorテスト失敗: {e}")

    # ------------------------------------------------------------------------------
    # 画像URLをIMAGE関数式に変換するテスト関数
    def test_image_downloader(self) -> None:
        # 指定URLの画像をGoogle SheetsのIMAGE関数式に変換し、ログと標準出力に結果を出力
        try:
            image_url = "https://auctions.c.yimg.jp/images.auctions.yahoo.co.jp/image/dr000/auc0106/user/5ec807c934150c37fea5b1cda6cdb4938dea1bcdd982696a3d9c90b59c549314/i-img1200x849-17500560233691ls9baa33.jpg"
            formula = ImageDownloader.get_image_formula(image_url)
            self.logger.info(f"ImageDownloaderテスト成功: {formula}")
            print(f"IMAGE式: {formula}")
        except Exception as e:
            self.logger.error("ImageDownloaderテスト失敗", exc_info=True)
            print("画像ダウンロード失敗:", e)

    # ------------------------------------------------------------------------------
    # メイン処理実行関数
    def run(self) -> None:
        # プログラム開始ログを出力
        self.logger.info("プログラム開始")

        # カラット数抽出テストを実行し抽出結果をログ出力
        self.test_num_extractor(
            "【6/27(金)】天然イエローダイヤモンド ルース 0.461ct LY VS2 鑑別 CGL│A4116mx 【0.4ct】 ダイヤ diamond"
        )

        # Googleスプレッドシートから検索条件を読み込み
        conditions = self.load_search_conditions()
        if not conditions:
            # 取得失敗または空の場合はエラーログを出力し処理中断
            self.logger.error("検索条件取得失敗または空。以降の処理中断。")
            return

        # 書き込み用のワークシートを取得し、テストデータを一括書き込み
        reader = SpreadsheetReader(self.config.SPREADSHEET_ID, self.config.SEARCH_COND_SHEET)
        worksheet = reader.get_worksheet(self.config.DATA_OUTPUT_SHEET)
        self.write_test_data(worksheet)

        # URL生成とSeleniumによるページ情報取得フローを実行
        self.url_and_selenium_flow(conditions)

        # 日付変換テストを実行し結果をログに出力
        self.test_date_converter("06/27 22:13")

        # 1カラット単価計算テストを実行し結果をログに出力
        self.test_price_calculator("天然ダイヤ 0.508ct F VS2", 51700)

        # 画像ダウンロード用関数のテストを実行し、結果をログと標準出力に出力
        self.test_image_downloader()

        # プログラム終了ログを出力
        self.logger.info("プログラム終了")
# **********************************************************************************