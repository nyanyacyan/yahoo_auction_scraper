# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$%$$$$$$$$$$$$$$$$$$$
# import
import sys
import os
import logging
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from installer.src.flow.base.chrome import Chrome
from installer.src.flow.base.spreadsheet_read import SpreadsheetReader
from installer.src.flow.base.url_builder import UrlBuilder
from installer.src.utils.text_utils import NumExtractor
import pandas as pd
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

# ------------------------------------------------------------------------------
# 関数定義
def main():
    logger.info("プログラム開始")

    # --- Chromeドライバー起動（不要ならコメントアウトOK） ---
    # --- Chromeクラスが正しく動くか実際に呼び出して確認するため。本番処理では削除しても良い
    logger.info("Chromeドライバーの起動処理を開始します。")
    driver = Chrome.get_driver()
    driver.get("https://www.google.com")
    logger.info("Chromeをヘッドレスモードで起動し、Googleを開きました。")
    driver.quit()
    logger.info("Chromeドライバーを終了しました。")
    # -----------------------------------------------------------

    # --- 商品タイトルなどから「ct」直前の数値を抽出するテスト ---
    test_text = "【6/27(金)】天然イエローダイヤモンド ルース 0.461ct LY VS2 鑑別 CGL│A4116mx 【0.4ct】 ダイヤ diamond"
    try:
        # NumExtractorで、商品タイトル中の「ct」直前にある数値（float型）を抽出する
        ct_value = NumExtractor.extract_ct_value(test_text)
        # 抽出結果の「型」と「値」をログ出力する
        logger.info(f"型: {type(ct_value)} | 値: {ct_value}")
    except Exception as e:
        logger.error(f"NumExtractor抽出失敗: {e}")

    SPREADSHEET_ID = "1nRJh0BqQazHe8qgT2YTZbMaZ9osPX835CbM3KkUjkcE"
    SHEET_NAME = "Master"

    try:
        logger.info("SpreadsheetReaderインスタンスを作成します。")
        reader = SpreadsheetReader(spreadsheet_id=SPREADSHEET_ID, worksheet_name=SHEET_NAME)
        logger.info(f"スプレッドシートから検索条件を取得します（ID: {SPREADSHEET_ID}, シート名: {SHEET_NAME}）")
        conditions = reader.get_search_conditions()
        logger.info(f"検索条件データ取得完了。取得件数: {len(conditions)}件")
        if not conditions:
            logger.warning("検索条件データが空です。")
            return

        def extract_keyword(row):
            # search_1～search_5 を結合し、空白を除去して返す
            return " ".join([row.get(f"search_{i}", "") for i in range(1, 6)]).strip()

        logger.info("=== 検索条件 ===")
        for i, cond in enumerate(conditions):
            keyword = extract_keyword(cond)
            if not keyword:
                continue  # キーワードが空はスキップ
            logger.info(f"{i+1}件目: {cond}")
    except Exception as e:
        logger.error(f"スプレッドシート読込中にエラーが発生しました: {e}")
        return

    # URL生成処理
    try:
        logger.info("URL生成処理を開始します。")
        url_builder = UrlBuilder()

        df = pd.DataFrame(conditions)
        # --- ここで有効なキーワードのみ抽出 ---
        search_cols = [col for col in df.columns if col.startswith("search_")]
        if search_cols:
            df['keyword'] = df[search_cols].fillna('').agg(' '.join, axis=1).str.strip()
        else:
            df['keyword'] = ''

        df_valid = df[df['keyword'] != '']  # 有効な行だけ
        logger.debug("DataFrame化完了:（有効なキーワードのみ表示）")
        for i, row in df_valid.iterrows():
            logger.debug(f"  {i+1}行目: {row.to_dict()}")

        # keyword列が無ければ search_1～search_5 を連結して keyword 列を作る
        if not df.empty and "keyword" not in df.columns:
            search_cols = [col for col in df.columns if col.startswith("search_")]
            if search_cols:
                df['keyword'] = df[search_cols].fillna('').agg(' '.join, axis=1).str.strip()
                df = df[df['keyword'] != '']
            else:
                logger.warning("search_1～search_5のようなカラムが見つかりません。URL生成をスキップします。")
                # return

        # 「keywordが空でない」行だけ抽出
        df = df[df['keyword'] != '']

        if df.empty:
            logger.warning("有効なキーワード行がありません。URL生成をスキップします。")
        else:
            for i, row in df.iterrows():
                keyword = row["keyword"]
                url = url_builder.build_url(keyword)
                logger.info(f"{i+1}行目:URL生成完了:キーワード = {keyword}\nurl={url}")

    except Exception as e:
        logger.error(f"URL生成中にエラーが発生しました: {e}")
        raise

    logger.info("プログラム終了")
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    main()