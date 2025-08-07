# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$%$$$$$$$$$$$$$$$$$$$
# import
import logging  # ログ出力用（デバッグ・障害解析・運用監視に必須）
from selenium import webdriver  # Selenium本体。ブラウザ自動制御のためのメインライブラリ
from selenium.webdriver.chrome.options import Options  # Chrome固有の各種オプション設定を行うためのクラス
from selenium.common.exceptions import WebDriverException  # ドライバ起動等で発生する標準例外クラス
logger = logging.getLogger(__name__)  # このモジュール専用のロガーインスタンス取得
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

# **********************************************************************************
# class定義
class Chrome:
    @staticmethod  # インスタンス化せずクラス名で直接呼び出し可能な静的メソッドにする
    # ------------------------------------------------------------------------------
    # 関数定義
    def get_driver():
        """
        Selenium Managerを使ってChromeDriverを起動し、driverオブジェクトを返す。
        エラー時はloggerで記録しraiseで伝播。
        """
        try:
            options = Options()  # Chrome起動オプションを格納するためのオブジェクト生成

            options.add_argument("--window-size=1200,800")  # ウィンドウサイズ（幅, 高さ）を固定。UI崩れ・要素位置ズレ防止

            # 必要なら他のオプションも追加可能（例：User-Agent偽装、プロキシ設定など拡張性あり）
            # options.add_argument("--headless=new")  # ヘッドレスモード（画面描画せず処理を高速化＆サーバー上でも実行可能）

            driver = webdriver.Chrome(options=options)  # Selenium 4.6以降はSelenium Managerで自動的にドライバ管理
            logger.info("ChromeDriverを起動しました。")  # 正常起動時はログ出力
            return driver  # ブラウザ制御用のWebDriverオブジェクトを返却

        except WebDriverException as e:  # ドライバ起動失敗・異常時
            logger.error(f"ChromeDriverの起動に失敗しました: {e}")  # 詳細エラーログ出力
            raise  # 呼び出し元に例外伝播（明示的な失敗通知）

        except Exception as e:  # その他すべての想定外の例外
            logger.error(f"予期しないエラー: {e}")  # 障害調査に役立つよう詳細出力
            raise  # 上記同様、伝播