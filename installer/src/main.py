# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# import
import sys
import os
import logging
from typing import List, Dict, Any
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

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
from flow.base.image_downloader import ImageDownloader  # ←★追加

# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# 設定値をクラスでまとめる
class Config:
    SPREADSHEET_ID: str = "1nRJh0BqQazHe8qgT2YTZbMaZ9osPX835CbM3KkUjkcE"
    SEARCH_COND_SHEET: str = "Master"
    DATA_OUTPUT_SHEET: str = "1"
    SHEET_NAME: str = DATA_OUTPUT_SHEET

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# 関数定義
# カラット数抽出テスト
def test_num_extractor(text: str) -> None:
    try:
        ct_value = NumExtractor.extract_ct_value(text)
        logger.info(f"カラット抽出: 型={type(ct_value)} | 値={ct_value}")
    except Exception as e:
        logger.error(f"NumExtractor抽出失敗: {e}")

# ------------------------------------------------------------------------------
# 関数定義
# スプレッドシートから検索条件を取得
def load_search_conditions(config: Config) -> List[Dict[str, Any]]:
    try:
        reader = SpreadsheetReader(
            spreadsheet_id=config.SPREADSHEET_ID,
            worksheet_name=config.SEARCH_COND_SHEET
        )
        logger.info(f"スプレッドシート({config.SPREADSHEET_ID})から検索条件取得")
        conditions = reader.get_search_conditions()
        logger.info(f"取得件数: {len(conditions)}件")
        return conditions
    except Exception as e:
        logger.error(f"スプレッドシート読込中エラー: {e}")
        return []

# ------------------------------------------------------------------------------
# 関数定義
# スプレッドシートへテストデータ一括書き込み
def write_test_data(config: Config, worksheet: Any) -> None:
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
        logger.info("テストデータ一括書き込み成功")
    except Exception as e:
        logger.error(f"テストデータ書き込み失敗: {e}")

# ------------------------------------------------------------------------------
# 関数定義
# キーワード抽出関数
def extract_keyword(row: Dict[str, Any]) -> str:
    return " ".join([str(row.get(f"search_{i}", "")) for i in range(1, 6)]).strip()

# ------------------------------------------------------------------------------
# 関数定義
# URL生成・Seleniumテスト処理
def url_and_selenium_flow(conditions: List[Dict[str, Any]]) -> None:
    if not conditions:
        logger.warning("条件が空なのでURL生成処理スキップ")
        return
    url_builder = UrlBuilder()
    df = pd.DataFrame(conditions)
    search_cols = [col for col in df.columns if col.startswith("search_")]
    df['keyword'] = df[search_cols].fillna('').astype(str).agg(' '.join, axis=1).str.strip() if search_cols else ''
    df_valid = df[df['keyword'] != '']
    if df_valid.empty:
        logger.warning("有効なキーワード行がありません")
        return
    for i, row in df_valid.iterrows():
        keyword = row["keyword"]
        url = url_builder.build_url(keyword)
        logger.info(f"{i+1}行目: キーワード={keyword} | url={url}")

    # Seleniumテスト（最初の1件のみ動作検証）
    try:
        first_keyword = df_valid.iloc[0]["keyword"]
        first_url = url_builder.build_url(first_keyword)
        logger.info(f"Seleniumでアクセス: {first_url}")
        driver = Chrome.get_driver()
        selenium_util = Selenium(driver)
        driver.get(first_url)
        try:
            end_dates = selenium_util.get_auction_end_dates()
            logger.info(f"終了日リスト: {end_dates}")
        except Exception as e:
            logger.warning(f"終了日取得失敗: {e}")
        try:
            urls = selenium_util.get_auction_urls()
            logger.info(f"商品詳細ページURLリスト: {urls}")
        except Exception as e:
            logger.warning(f"商品URL取得失敗: {e}")
        if urls:
            driver.get(urls[0])
            try:
                item_info = selenium_util.get_item_info()
                logger.info(f"商品情報: {item_info}")
            except Exception as e:
                logger.warning(f"詳細取得失敗: {e}")
            try:
                detail_flow = DetailPageFlow(driver, selenium_util)
                detail_result = detail_flow.extract_detail(urls[0])
                logger.info(f"DetailPageFlow抽出結果: {detail_result}")
            except Exception as e:
                logger.warning(f"DetailPageFlow動作確認エラー: {e}")
        driver.quit()
    except Exception as e:
        logger.error(f"Selenium利用時エラー: {e}")

# ------------------------------------------------------------------------------
# 関数定義
# 日付変換テスト
def test_date_converter(sample_end_time: str) -> None:
    try:
        converted_date = DateConverter.convert(sample_end_time)
        logger.info(f"日付変換: 型={type(converted_date)} | 値={converted_date}")
    except Exception as e:
        logger.error(f"DateConverter変換テストでエラー: {e}")

# ------------------------------------------------------------------------------
# 関数定義
# 1ct単価計算テスト
def test_price_calculator(title: str, price: int) -> None:
    try:
        price_per_ct = PriceCalculator.calculate_price_per_carat(title, price)
        logger.info(f"タイトル: {title} / 落札価格: {price} → 1ct単価: {price_per_ct} 円/ct")
    except Exception as e:
        logger.error(f"PriceCalculatorテスト失敗: {e}")

# ------------------------------------------------------------------------------
# 関数定義
# 画像ダウンロード＆リサイズテスト
def test_image_downloader():
    try:
        image_url = "https://auctions.c.yimg.jp/images.auctions.yahoo.co.jp/image/dr000/auc0106/user/5ec807c934150c37fea5b1cda6cdb4938dea1bcdd982696a3d9c90b59c549314/i-img1200x849-17500560233691ls9baa33.jpg"
        formula = ImageDownloader.get_image_formula(image_url)  # ←ここを修正
        logger.info(f"ImageDownloaderテスト成功: {formula}")
        print(f"IMAGE式: {formula}")
    except Exception as e:
        logger.error("ImageDownloaderテスト失敗", exc_info=True)
        print("画像ダウンロード失敗:", e)

# ------------------------------------------------------------------------------
# 関数定義
# メイン処理
def main() -> None:
    logger.info("プログラム開始")
    config = Config()

    # カラット数抽出テスト
    test_num_extractor(
        "【6/27(金)】天然イエローダイヤモンド ルース 0.461ct LY VS2 鑑別 CGL│A4116mx 【0.4ct】 ダイヤ diamond"
    )

    # 検索条件の取得とテストデータ書き込み
    conditions = load_search_conditions(config)
    if not conditions:
        logger.error("検索条件取得失敗または空。以降の処理中断。")
        return
    reader = SpreadsheetReader(config.SPREADSHEET_ID, config.SEARCH_COND_SHEET)
    worksheet = reader.get_worksheet(config.DATA_OUTPUT_SHEET)
    write_test_data(config, worksheet)

    # URL生成＆Seleniumテスト
    url_and_selenium_flow(conditions)

    # 日付変換テスト
    test_date_converter("06/27 22:13")

    # 1ct単価計算テスト
    test_price_calculator("天然ダイヤ 0.508ct F VS2", 51700)

    # 画像ダウンロード＆リサイズテスト
    test_image_downloader()

    logger.info("プログラム終了")
# **********************************************************************************

if __name__ == "__main__":
    main()