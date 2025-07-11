# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$%$$$$$$$$$$$$$$$$$$$
# import
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
logger = logging.getLogger(__name__)
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

# **********************************************************************************
# class定義
class Chrome:
    @staticmethod
    # ------------------------------------------------------------------------------
    # 関数定義
    def get_driver():
        """
        Selenium Managerを使ってChromeDriverを起動し、driverオブジェクトを返す。
        エラー時はloggerで記録しraiseで伝播。
        """
        try:
            options = Options()
            options.add_argument("--window-size=1200,800")
            # 必要なら他のオプションも追加可能
            options.add_argument("--headless=new")

            driver = webdriver.Chrome(options=options)  # Selenium Manager利用
            logger.info("ChromeDriverを起動しました。")
            return driver
        except WebDriverException as e:
            logger.error(f"ChromeDriverの起動に失敗しました: {e}")
            raise
        except Exception as e:
            logger.error(f"予期しないエラー: {e}")
            raise
    # ------------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    driver = Chrome.get_driver()
    driver.get("https://www.google.com")
    # input("Chromeが起動したら何かキーを押してください: ")
    driver.quit()
# **********************************************************************************






