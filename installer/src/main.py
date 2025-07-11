import sys
import os
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from installer.src.flow.base.chrome import Chrome
from installer.src.flow.base.spreadsheet_read import SpreadsheetReader

from installer.src.flow.base.url_builder import UrlBuilder
import pandas as pd  # DataFrameで受け渡しする場合用

logging.basicConfig(
    level=logging.DEBUG,  # debugまで表示
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    logger.info("プログラム開始")

    logger.info("Chromeドライバーの起動処理を開始します。")
    driver = Chrome.get_driver()
    driver.get("https://www.google.com")
    logger.info("Chromeをヘッドレスモードで起動し、Googleを開きました。")
    # ↓↓↓ ここでユーザー入力待ちは削除！！
    # input("Chromeが起動してGoogleが開いたら何かキーを押してください: ")
    driver.quit()
    logger.info("Chromeドライバーを終了しました。")

    SPREADSHEET_ID = "1nRJh0BqQazHe8qgT2YTZbMaZ9osPX835CbM3KkUjkcE"
    SHEET_NAME = "Master"

    try:
        logger.info("SpreadsheetReaderインスタンスを作成します。")
        reader = SpreadsheetReader(spreadsheet_id=SPREADSHEET_ID, worksheet_name=SHEET_NAME)
        logger.info(f"スプレッドシートから検索条件を取得します（ID: {SPREADSHEET_ID}, シート名: {SHEET_NAME}）")
        conditions = reader.get_search_conditions()
        logger.info(f"検索条件データ取得完了。取得件数: {len(conditions)}件")
        if conditions:
            logger.debug(f"最初のデータ: {conditions[0]}")
        else:
            logger.warning("検索条件データが空です。")
        logger.info("=== 検索条件 ===")
        for i, cond in enumerate(conditions):
            logger.info(f"{i+1}件目: {cond}")
    except Exception as e:
        logger.error(f"スプレッドシート読込中にエラーが発生しました: {e}")

    try:
        logger.info("URL生成処理を開始します。")
        url_builder = UrlBuilder()

        # conditionsがlist of dict（例: [{'keyword': 'ギター'}, ...]）の場合、DataFrameに変換
        df = pd.DataFrame(conditions)
        logger.debug(f"DataFrame化完了: {df.head().to_dict(orient='records') if not df.empty else '空データ'}")

        # "keyword"列が無ければ search_1～search_5 を連結して "keyword"列を作る
        if not df.empty and "keyword" not in df.columns:
            search_cols = [col for col in df.columns if col.startswith("search_")]
            if search_cols:
                df['keyword'] = df[search_cols].fillna('').agg(' '.join, axis=1).str.strip()
                df = df[df['keyword'] != '']  # 空行除去
            else:
                logger.warning("search_1～search_5のようなカラムが見つかりません。URL生成をスキップします。")

        if not df.empty and "keyword" in df.columns:
            urls = url_builder.build_urls_from_dataframe(df, keyword_column="keyword")
            logger.info(f"URL生成完了（件数: {len(urls)}件）")
            for i, url in enumerate(urls):
                logger.info(f"{i+1}件目URL: {url}")
        else:
            logger.warning("キーワード列が存在しない、もしくはデータが空のため、URL生成をスキップします。")

    except Exception as e:
        logger.error(f"URL生成中にエラーが発生しました: {e}")
        raise  # 明示的に再スロー

    logger.info("プログラム終了")

if __name__ == "__main__":
    main()














# issues #2 起動確認すみ
""" 
import sys
import os
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from installer.src.flow.base.chrome import Chrome
from installer.src.flow.base.spreadsheet_read import SpreadsheetReader

logging.basicConfig(
    level=logging.DEBUG,  # debugまで表示
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    logger.info("プログラム開始")

    logger.info("Chromeドライバーの起動処理を開始します。")
    driver = Chrome.get_driver()
    driver.get("https://www.google.com")
    logger.info("ChromeがGoogleを開きました。")
    input("Chromeが起動してGoogleが開いたら何かキーを押してください: ")
    driver.quit()
    logger.info("Chromeドライバーを終了しました。")

    SPREADSHEET_ID = "1nRJh0BqQazHe8qgT2YTZbMaZ9osPX835CbM3KkUjkcE"
    SHEET_NAME = "Master"

    try:
        logger.info("SpreadsheetReaderインスタンスを作成します。")
        reader = SpreadsheetReader(spreadsheet_id=SPREADSHEET_ID, worksheet_name=SHEET_NAME)
        logger.info(f"スプレッドシートから検索条件を取得します（ID: {SPREADSHEET_ID}, シート名: {SHEET_NAME}）")
        conditions = reader.get_search_conditions()
        logger.info(f"検索条件データ取得完了。取得件数: {len(conditions)}件")
        if conditions:
            logger.debug(f"最初のデータ: {conditions[0]}")
        else:
            logger.warning("検索条件データが空です。")
        logger.info("=== 検索条件 ===")
        for i, cond in enumerate(conditions):
            logger.info(f"{i+1}件目: {cond}")
    except Exception as e:
        logger.error(f"スプレッドシート読込中にエラーが発生しました: {e}")

    logger.info("プログラム終了")

if __name__ == "__main__":
    main()
"""




