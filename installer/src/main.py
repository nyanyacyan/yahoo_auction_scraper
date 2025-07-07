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





# issues #2 起動確認すみ
"""
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# import
import sys
import os
import logging  # 追加

# パス対策（絶対パスを追加。これはinstaller/src/main.pyにいる場合！）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from installer.src.flow.base.chrome import Chrome
from installer.src.flow.base.spreadsheet_read import SpreadsheetReader

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,  # 必要に応じて変更
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# **********************************************************************************
# ----------------------------------------------------------------------------------
# 関数定義
def main():
    driver = Chrome.get_driver()
    driver.get("https://www.google.com")
    input("Chromeが起動してGoogleが開いたら何かキーを押してください: ")
    driver.quit()

    #! ここから追加：SpreadsheetReaderによる検索条件の取得
    SPREADSHEET_ID = "1nRJh0BqQazHe8qgT2YTZbMaZ9osPX835CbM3KkUjkcE"   # 必要に応じて実際のIDを入力
    SHEET_NAME = "Master"  # 例：シート名

    try:
        reader = SpreadsheetReader(spreadsheet_id=SPREADSHEET_ID, worksheet_name=SHEET_NAME)
        conditions = reader.get_search_conditions()
        logger.info("=== 検索条件 ===")
        for cond in conditions:
            logger.info(cond)
    except Exception as e:
        logger.error(f"スプレッドシート読込中にエラーが発生しました: {e}")

# **********************************************************************************

if __name__ == "__main__":
    main()
# ----------------------------------------------------------------------------------
"""

# issues #1 で完成した内容
"""
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# import
import sys
import os
# パス対策（絶対パスを追加。これはinstaller/src/main.pyにいる場合！）
#../../ に変えて1階層減らす（installer/から見たルートにする）ここを修正。
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from installer.src.flow.base.chrome import Chrome
# 相対パスimport
#from .flow.base.chrome import Chrome
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

# **********************************************************************************
# ----------------------------------------------------------------------------------
# 関数定義
def main():
    driver = Chrome.get_driver()
    driver.get("https://www.google.com")
    input("Chromeが起動してGoogleが開いたら何かキーを押してください: ")
    driver.quit()
    pass  #! ここを修正して実装してください
# **********************************************************************************

if __name__ == "__main__":
    main()

# ----------------------------------------------------------------------------------
"""