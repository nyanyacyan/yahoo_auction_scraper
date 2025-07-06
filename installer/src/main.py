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
    SPREADSHEET_ID = "1SA9kpYxeSZjeJXtrhJ7GZ3RKXoIr2JRqzlv_ILqYZeY"   # 必要に応じて実際のIDを入力
    SHEET_NAME = "シート1"  # 例：シート名

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











# issues#2 起動確認すみ ただし、print文
"""
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# import
import sys
import os

# パス対策（絶対パスを追加。これはinstaller/src/main.pyにいる場合！）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from installer.src.flow.base.chrome import Chrome
from installer.src.flow.base.spreadsheet_read import SpreadsheetReader

# **********************************************************************************
# ----------------------------------------------------------------------------------
# 関数定義
def main():
    driver = Chrome.get_driver()
    driver.get("https://www.google.com")
    input("Chromeが起動してGoogleが開いたら何かキーを押してください: ")
    driver.quit()

    #! ここから追加：SpreadsheetReaderによる検索条件の取得
    SPREADSHEET_ID = "1SA9kpYxeSZjeJXtrhJ7GZ3RKXoIr2JRqzlv_ILqYZeY"   # 必要に応じて実際のIDを入力
    SHEET_NAME = "シート1"  # 例：シート名

    try:
        reader = SpreadsheetReader(spreadsheet_id=SPREADSHEET_ID, worksheet_name=SHEET_NAME)
        conditions = reader.get_search_conditions()
        print("=== 検索条件 ===")
        for cond in conditions:
            print(cond)
    except Exception as e:
        print(f"スプレッドシート読込中にエラーが発生しました: {e}")

# **********************************************************************************

if __name__ == "__main__":
    main()
# ----------------------------------------------------------------------------------
"""

# close #1 で完成した内容
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