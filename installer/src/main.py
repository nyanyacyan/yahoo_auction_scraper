# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$%$$$$$$$$$$$$$$$$$$$
# import
import sys
import os
import logging
import pandas as pd
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from installer.src.flow.base.chrome import Chrome
from installer.src.flow.base.spreadsheet_read import SpreadsheetReader
from installer.src.flow.base.url_builder import UrlBuilder
from installer.src.utils.text_utils import NumExtractor
from installer.src.flow.base.utils import DateConverter
from installer.src.flow.base.number_calculator import PriceCalculator
from installer.src.flow.base.spreadsheet_read import SpreadsheetReader
from installer.src.flow.base.chrome import Chrome
from installer.src.flow.base.selenium_manager import Selenium
from installer.src.flow.detail_page_flow import DetailPageFlow
from installer.src.flow.base.spreadsheet_write import SpreadsheetWriter

# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
# )
# logger = logging.getLogger(__name__)
# 必要に応じてロガー初期化
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

# ------------------------------------------------------------------------------
# 関数定義
def main():
    logger.info("プログラム開始")
    # =============================== Config ===============================
    SPREADSHEET_ID = "1nRJh0BqQazHe8qgT2YTZbMaZ9osPX835CbM3KkUjkcE"
    SEARCH_COND_SHEET = "Master"    # 検索条件用
    DATA_OUTPUT_SHEET = "1"         # 結果出力用
    SHEET_NAME = DATA_OUTPUT_SHEET  # ← この行を追加

    # --- 商品タイトルなどから「ct」直前の数値を抽出するテスト ---
    test_text = "【6/27(金)】天然イエローダイヤモンド ルース 0.461ct LY VS2 鑑別 CGL│A4116mx 【0.4ct】 ダイヤ diamond"
    try:
        ct_value = NumExtractor.extract_ct_value(test_text)
        logger.info(f"型: {type(ct_value)} | 値: {ct_value}")
    except Exception as e:
        logger.error(f"NumExtractor抽出失敗: {e}")



    try:
        logger.info("SpreadsheetReaderインスタンスを作成します。")
        reader = SpreadsheetReader(spreadsheet_id=SPREADSHEET_ID, worksheet_name=SEARCH_COND_SHEET)

        worksheet = reader.get_worksheet(DATA_OUTPUT_SHEET)
        writer = SpreadsheetWriter(worksheet)

        logger.info(f"スプレッドシートから検索条件を取得します（ID: {SPREADSHEET_ID}, シート名: {SHEET_NAME}）")
        conditions = reader.get_search_conditions()
        logger.info(f"検索条件データ取得完了。取得件数: {len(conditions)}件")
        if not conditions:
            logger.warning("検索条件データが空です。")
            return

        def extract_keyword(row):
            return " ".join([row.get(f"search_{i}", "") for i in range(1, 6)]).strip()

        logger.info("=== 検索条件 ===")
        for i, cond in enumerate(conditions):
            keyword = extract_keyword(cond)
            if not keyword:
                continue
            logger.info(f"{i+1}件目: {cond}")

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

        for rec in test_data:
            try:
                writer.write_record(rec)
            except Exception as e:
                logger.error(f"書き込みエラー: {e}")


    except Exception as e:
        logger.error(f"スプレッドシート読込中にエラーが発生しました: {e}")
        return

    # URL生成処理
    try:
        logger.info("URL生成処理を開始します。")
        url_builder = UrlBuilder()

        df = pd.DataFrame(conditions)
        search_cols = [col for col in df.columns if col.startswith("search_")]
        if search_cols:
            df['keyword'] = df[search_cols].fillna('').agg(' '.join, axis=1).str.strip()
        else:
            df['keyword'] = ''

        df_valid = df[df['keyword'] != '']
        logger.debug("DataFrame化完了:（有効なキーワードのみ表示）")
        for i, row in df_valid.iterrows():
            logger.debug(f"  {i+1}行目: {row.to_dict()}")

        if not df.empty and "keyword" not in df.columns:
            search_cols = [col for col in df.columns if col.startswith("search_")]
            if search_cols:
                df['keyword'] = df[search_cols].fillna('').agg(' '.join, axis=1).str.strip()
                df = df[df['keyword'] != '']
            else:
                logger.warning("search_1～search_5のようなカラムが見つかりません。URL生成をスキップします。")

        df = df[df['keyword'] != '']

        if df.empty:
            logger.warning("有効なキーワード行がありません。URL生成をスキップします。")
        else:
            for i, row in df.iterrows():
                keyword = row["keyword"]
                url = url_builder.build_url(keyword)
                logger.info(f"{i+1}行目:URL生成完了:キーワード = {keyword}\nurl={url}")

        # ==================== ここからSelenium利用処理 ====================
        try:
            if not df.empty:
                # 例：最初の1キーワードのみ動作確認（安全のため）
                first_keyword = df.iloc[0]['keyword']
                first_url = url_builder.build_url(first_keyword)
                logger.info(f"SeleniumでアクセスするURL: {first_url}")

                # Selenium関連import
                from installer.src.flow.base.selenium_manager import Selenium

                # Chromeドライバー起動
                driver = Chrome.get_driver()
                selenium_util = Selenium(driver)

                # 一覧ページを開く
                driver.get(first_url)

                # 終了日リスト取得
                try:
                    end_dates = selenium_util.get_auction_end_dates()
                    logger.info(f"終了日リスト: {end_dates}")
                except Exception as e:
                    logger.error(f"終了日取得で例外発生: {e}")

                # 商品詳細URL取得
                try:
                    urls = selenium_util.get_auction_urls()
                    logger.info(f"商品詳細ページURLリスト: {urls}")
                except Exception as e:
                    logger.error(f"商品URL取得で例外発生: {e}")

                # 詳細ページにアクセスして商品情報を取得（最初の商品のみ）
                if urls:
                    driver.get(urls[0])
                    try:
                        item_info = selenium_util.get_item_info()
                        logger.info(f"商品情報: {item_info}")
                    except Exception as e:
                        logger.error(f"詳細取得で例外発生: {e}")

                # ==================== DetailPageFlow動作確認 ====================
                try:
                    if urls:
                        from installer.src.flow.detail_page_flow import DetailPageFlow
                        detail_flow = DetailPageFlow(driver, selenium_util)

                        logger.info("DetailPageFlowによる詳細データ抽出テストを開始します。")
                        detail_result = detail_flow.extract_detail(urls[0])
                        logger.info(f"DetailPageFlow抽出結果: {detail_result}")
                except Exception as e:
                    logger.error(f"DetailPageFlow動作確認中にエラー: {e}")
                # ================================================================

                # ドライバー終了
                driver.quit()
        except Exception as e:
            logger.error(f"Selenium利用中にエラー発生: {e}")
        # ==================== Selenium利用処理ここまで ====================

    except Exception as e:
        logger.error(f"URL生成中にエラーが発生しました: {e}")
        raise

    # --- DateConverterのテスト ---
    try:
        logger.info("DateConverterによる終了日時変換テストを開始します。")
        sample_end_time = "06/27 22:13"
        converted_date = DateConverter.convert(sample_end_time)
        logger.info(f"変換結果: 型={type(converted_date)} | 値={converted_date}")
    except Exception as e:
        logger.error(f"DateConverter変換テストで例外発生: {e}")

    # --- PriceCalculatorテスト呼び出し ---
    logger.info("PriceCalculatorによる1ct単価計算テストを開始します。")
    try:
        sample_title = "天然ダイヤ 0.508ct F VS2"
        sample_price = 51700
        price_per_ct = PriceCalculator.calculate_price_per_carat(sample_title, sample_price)
        logger.info(f"テスト用タイトル: {sample_title} / 落札価格: {sample_price}円 → 1ct単価: {price_per_ct} 円/ct")
    except Exception as e:
        logger.error(f"PriceCalculatorテストで例外発生: {e}")

    logger.info("プログラム終了")
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    main()
















    
    
    
    
# # $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$%$$$$$$$$$$$$$$$$$$$
# # import
# import sys
# import os
# import logging
# import pandas as pd
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
# from installer.src.flow.base.chrome import Chrome
# from installer.src.flow.base.spreadsheet_read import SpreadsheetReader
# from installer.src.flow.base.url_builder import UrlBuilder
# from installer.src.utils.text_utils import NumExtractor
# from installer.src.flow.base.utils import DateConverter
# from installer.src.flow.base.number_calculator import PriceCalculator

# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
# )
# logger = logging.getLogger(__name__)
# # $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

# # ------------------------------------------------------------------------------
# # 関数定義
# def main():
#     logger.info("プログラム開始")

#     # --- 商品タイトルなどから「ct」直前の数値を抽出するテスト ---
#     test_text = "【6/27(金)】天然イエローダイヤモンド ルース 0.461ct LY VS2 鑑別 CGL│A4116mx 【0.4ct】 ダイヤ diamond"
#     try:
#         ct_value = NumExtractor.extract_ct_value(test_text)
#         logger.info(f"型: {type(ct_value)} | 値: {ct_value}")
#     except Exception as e:
#         logger.error(f"NumExtractor抽出失敗: {e}")

#     SPREADSHEET_ID = "1nRJh0BqQazHe8qgT2YTZbMaZ9osPX835CbM3KkUjkcE"
#     SHEET_NAME = "Master"

#     try:
#         logger.info("SpreadsheetReaderインスタンスを作成します。")
#         reader = SpreadsheetReader(spreadsheet_id=SPREADSHEET_ID, worksheet_name=SHEET_NAME)
#         logger.info(f"スプレッドシートから検索条件を取得します（ID: {SPREADSHEET_ID}, シート名: {SHEET_NAME}）")
#         conditions = reader.get_search_conditions()
#         logger.info(f"検索条件データ取得完了。取得件数: {len(conditions)}件")
#         if not conditions:
#             logger.warning("検索条件データが空です。")
#             return

#         def extract_keyword(row):
#             return " ".join([row.get(f"search_{i}", "") for i in range(1, 6)]).strip()

#         logger.info("=== 検索条件 ===")
#         for i, cond in enumerate(conditions):
#             keyword = extract_keyword(cond)
#             if not keyword:
#                 continue
#             logger.info(f"{i+1}件目: {cond}")
#     except Exception as e:
#         logger.error(f"スプレッドシート読込中にエラーが発生しました: {e}")
#         return

#     # URL生成処理
#     try:
#         logger.info("URL生成処理を開始します。")
#         url_builder = UrlBuilder()

#         df = pd.DataFrame(conditions)
#         search_cols = [col for col in df.columns if col.startswith("search_")]
#         if search_cols:
#             df['keyword'] = df[search_cols].fillna('').agg(' '.join, axis=1).str.strip()
#         else:
#             df['keyword'] = ''

#         df_valid = df[df['keyword'] != '']
#         logger.debug("DataFrame化完了:（有効なキーワードのみ表示）")
#         for i, row in df_valid.iterrows():
#             logger.debug(f"  {i+1}行目: {row.to_dict()}")

#         if not df.empty and "keyword" not in df.columns:
#             search_cols = [col for col in df.columns if col.startswith("search_")]
#             if search_cols:
#                 df['keyword'] = df[search_cols].fillna('').agg(' '.join, axis=1).str.strip()
#                 df = df[df['keyword'] != '']
#             else:
#                 logger.warning("search_1～search_5のようなカラムが見つかりません。URL生成をスキップします。")

#         df = df[df['keyword'] != '']

#         if df.empty:
#             logger.warning("有効なキーワード行がありません。URL生成をスキップします。")
#         else:
#             for i, row in df.iterrows():
#                 keyword = row["keyword"]
#                 url = url_builder.build_url(keyword)
#                 logger.info(f"{i+1}行目:URL生成完了:キーワード = {keyword}\nurl={url}")

#         # ==================== ここからSelenium利用処理 ====================
#         try:
#             if not df.empty:
#                 # 例：最初の1キーワードのみ動作確認（安全のため）
#                 first_keyword = df.iloc[0]['keyword']
#                 first_url = url_builder.build_url(first_keyword)
#                 logger.info(f"SeleniumでアクセスするURL: {first_url}")

#                 # Selenium関連import
#                 from installer.src.flow.base.selenium_manager import Selenium

#                 # Chromeドライバー起動
#                 driver = Chrome.get_driver()
#                 selenium_util = Selenium(driver)

#                 # 一覧ページを開く
#                 driver.get(first_url)

#                 # 終了日リスト取得
#                 try:
#                     end_dates = selenium_util.get_auction_end_dates()
#                     logger.info(f"終了日リスト: {end_dates}")
#                 except Exception as e:
#                     logger.error(f"終了日取得で例外発生: {e}")

#                 # 商品詳細URL取得
#                 try:
#                     urls = selenium_util.get_auction_urls()
#                     logger.info(f"商品詳細ページURLリスト: {urls}")
#                 except Exception as e:
#                     logger.error(f"商品URL取得で例外発生: {e}")

#                 # 詳細ページにアクセスして商品情報を取得（最初の商品のみ）
#                 if urls:
#                     driver.get(urls[0])
#                     try:
#                         item_info = selenium_util.get_item_info()
#                         logger.info(f"商品情報: {item_info}")
#                     except Exception as e:
#                         logger.error(f"詳細取得で例外発生: {e}")

#                 # ==================== DetailPageFlow動作確認 ====================
#                 try:
#                     if urls:
#                         from installer.src.flow.detail_page_flow import DetailPageFlow
#                         detail_flow = DetailPageFlow(driver, selenium_util)

#                         logger.info("DetailPageFlowによる詳細データ抽出テストを開始します。")
#                         detail_result = detail_flow.extract_detail(urls[0])
#                         logger.info(f"DetailPageFlow抽出結果: {detail_result}")
#                 except Exception as e:
#                     logger.error(f"DetailPageFlow動作確認中にエラー: {e}")
#                 # ================================================================

#                 # ドライバー終了
#                 driver.quit()
#         except Exception as e:
#             logger.error(f"Selenium利用中にエラー発生: {e}")
#         # ==================== Selenium利用処理ここまで ====================

#     except Exception as e:
#         logger.error(f"URL生成中にエラーが発生しました: {e}")
#         raise

#     # --- DateConverterのテスト ---
#     try:
#         logger.info("DateConverterによる終了日時変換テストを開始します。")
#         sample_end_time = "06/27 22:13"
#         converted_date = DateConverter.convert(sample_end_time)
#         logger.info(f"変換結果: 型={type(converted_date)} | 値={converted_date}")
#     except Exception as e:
#         logger.error(f"DateConverter変換テストで例外発生: {e}")

#     # --- PriceCalculatorテスト呼び出し ---
#     logger.info("PriceCalculatorによる1ct単価計算テストを開始します。")
#     try:
#         sample_title = "天然ダイヤ 0.508ct F VS2"
#         sample_price = 51700
#         price_per_ct = PriceCalculator.calculate_price_per_carat(sample_title, sample_price)
#         logger.info(f"テスト用タイトル: {sample_title} / 落札価格: {sample_price}円 → 1ct単価: {price_per_ct} 円/ct")
#     except Exception as e:
#         logger.error(f"PriceCalculatorテストで例外発生: {e}")

#     logger.info("プログラム終了")
# # ------------------------------------------------------------------------------

# if __name__ == "__main__":
#     main()