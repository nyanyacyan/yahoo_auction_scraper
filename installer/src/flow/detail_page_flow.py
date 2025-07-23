# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$%$$$$$$$$$$$$$$$$$$$
# import
import logging
from installer.src.flow.base.number_calculator import PriceCalculator
from installer.src.utils.text_utils import NumExtractor
from installer.src.flow.base.utils import DateConverter
# ロガーのセットアップ（エラーや進捗を出力するため）
logger = logging.getLogger(__name__)
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

# **********************************************************************************
# class定義
class DetailPageFlow:

    # ------------------------------------------------------------------------------
    # 関数定義
    def __init__(self, driver, selenium_util):
        """
        Yahoo!オークション詳細ページのデータ抽出フロー管理
        :param driver: Selenium WebDriver インスタンス
        :param selenium_util: Seleniumのヘルパークラスインスタンス
        """
        self.driver = driver
        self.selenium_util = selenium_util
        self.price_calculator = PriceCalculator()
        self.num_extractor = NumExtractor()
        self.date_converter = DateConverter()

    # ------------------------------------------------------------------------------
    # 関数定義
#     def extract_detail(self, url: str) -> dict:
#         """
#         指定URLの詳細ページから必要データを抽出し辞書形式で返却
#         :param url: 詳細ページURL
#         :return: dict
#         """
#         logger.info(f"詳細ページにアクセス: {url}")
#         try:
#             # 詳細ページへ移動
#             self.driver.get(url)

#             # 件名取得
#             title = self.selenium_util.get_title()
#             logger.debug(f"件名取得: {title}")

#             # 価格取得
#             price = self.selenium_util.get_price()
#             logger.debug(f"価格取得: {price}")

#             # 画像URL（1枚目のみ）
#             image_url = self.selenium_util.get_image_url()
#             logger.debug(f"画像URL取得: {image_url}")

#             # カラット数抽出
#             ct = self.num_extractor.extract_ct_value(title)
#             logger.debug(f"カラット数抽出: {ct}")

#             # 1ct単価計算
#             price_per_ct = self.price_calculator.calculate_price_per_carat(title, price)
#             logger.debug(f"1カラット単価計算: {price_per_ct}")

#             # 終了日取得
#             end_date_str = self.selenium_util.get_detail_end_date()
#             date = self.date_converter.convert(end_date_str)
#             logger.debug(f"終了日取得: {date}")

#             # スプシ用画像フォーマット
#             # image_formula = f'=IMAGE("{image_url}", 4, 80, 80)'
#             image_formula = f'=IMAGE("{image_url}", 4, 80, 80)'
#             item["image"] = image_formula

#             result = {
#                 "date": str(date),
#                 "title": title,
#                 "price": price,
#                 "ct": ct,
#                 "1ct_price": price_per_ct,
#                 "image": image_formula
#             }

#             logger.info(f"抽出結果: {result}")
#             return result

#         except Exception as e:
#             logger.error(f"詳細ページデータ抽出中にエラー: {e}", exc_info=True)
#             raise
# # **********************************************************************************






def extract_detail(self, url: str) -> dict:
    """
    指定URLの詳細ページから必要データを抽出し辞書形式で返却
    :param url: 詳細ページURL
    :return: dict
    """
    logger.info(f"詳細ページにアクセス: {url}")
    try:
        # 詳細ページへ移動
        self.driver.get(url)

        # 件名取得
        title = self.selenium_util.get_title()
        logger.debug(f"件名取得: {title}")

        # 価格取得
        price = self.selenium_util.get_price()
        logger.debug(f"価格取得: {price}")

        # 画像URL（1枚目のみ）
        image_url = self.selenium_util.get_image_url()
        logger.debug(f"画像URL取得: {image_url}")

        # カラット数抽出
        ct = self.num_extractor.extract_ct_value(title)
        logger.debug(f"カラット数抽出: {ct}")

        # 1ct単価計算
        price_per_ct = self.price_calculator.calculate_price_per_carat(title, price)
        logger.debug(f"1カラット単価計算: {price_per_ct}")

        # 終了日取得
        end_date_str = self.selenium_util.get_detail_end_date()
        date = self.date_converter.convert(end_date_str)
        logger.debug(f"終了日取得: {date}")

        # スプシ用画像フォーマット
        image_formula = f'=IMAGE("{image_url}", 4, 80, 80)'

        result = {
            "date": f"'{date}",
            "title": title,
            "price": price,
            "ct": ct,
            "1ct_price": price_per_ct,
            "image": image_formula
        }

        logger.info(f"抽出結果: {result}")
        return result

    except Exception as e:
        logger.error(f"詳細ページデータ抽出中にエラー: {e}", exc_info=True)
        raise