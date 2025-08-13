# ==========================================================
# import（標準、プロジェクト内モジュール）

import logging                               # ログ出力用（動作確認・デバッグに使う）
from selenium import webdriver               # Chrome等のブラウザを自動操作する本体
from selenium.webdriver.chrome.options import Options  # Chromeの起動オプションを設定する
from selenium.common.exceptions import WebDriverException  # 起動失敗時などの例外（※本コード内では未使用）
from typing import Optional                  # 引数が「値 or None」を取れることを表す型ヒントに使用



# ==========================================================
# ログ設定

logger = logging.getLogger(__name__)         # このモジュール専用のロガー



# ==========================================================
# class定義

class Chrome:                                # Chromeブラウザ生成用の小さなラッパークラス
    """
    SeleniumでChromeドライバーを生成するための薄いラッパークラス。
    役割：Chromeの起動設定（オプション）をまとめ、WebDriverインスタンスを返す。
    """



    # ==========================================================
    # 静的メソッド（インスタンス化不要で利用可能）

    @staticmethod                                  # インスタンスを作らずに呼べることを示すデコレータ
    def get_driver(user_agent: Optional[str] = None):  # UAを任意指定してChrome WebDriverを返す
        """
        引数:
            user_agent: ブラウザのUser-Agent文字列。指定するとWebサイトに伝える“名札”を偽装できる。
                        例) モバイルUAにしてスマホ表示を確認、など。Noneなら標準のUAを使用。
        戻り値:
            selenium.webdriver.Chrome のインスタンス（起動済みのブラウザ制御ハンドル）。
        注意:
            - ここでは例外処理をしていないため、ドライバー起動に失敗すると WebDriverException が上位へ送出される。
            （呼び出し側で try-except することを想定）
            - ヘッドレス起動（画面非表示）は設定していない。必要なら options.add_argument("--headless=new") を追加する。
            - ローカルのChromeとChromeDriverのバージョン整合が取れていないと起動に失敗する。
        """
        options = Options()                   # Chromeの起動オプション入れ物を作成

        if user_agent:                        # UAが指定された場合のみ、起動オプションへ反映する分岐
            # User-Agentを明示指定。検証や回避目的で“ブラウザのふり”を変えたいときに使う。
            options.add_argument(f"--user-agent={user_agent}")  # 起動時引数としてUAを渡す

        # 指定したオプションでChromeを起動してWebDriverを作成
        # ※ 起動に失敗すると WebDriverException（例: バージョン不一致、ドライバー未配置）が発生し得る
        driver = webdriver.Chrome(options=options)  # Chromeドライバーを起動して制御ハンドルを取得
        return driver                         # 呼び出し側で driver.get(url) 等を使って操作する





# ==============
# 実行の順序
# ==============
# 1. モジュール logging / selenium（webdriver, Options）/ 例外 / Optional をimportする
# → ブラウザ自動操作に必要な機能を読み込む。補足：この時点では“読み込み”だけで実行はされない。

# 2. logger = logging.getLogger(name) を実行する
# → このモジュール専用のロガーを取得する。補足：以降のINFO/ERRORなどがここに記録される。

# 3. class Chrome を定義する
# → Chromeドライバーを生成する小さなラッパの器を用意する。補足：定義は実行ではない（中の処理は呼ばれた時だけ動く）。

# 4. 静的メソッド get_driver（@staticmethod）を定義する
# → インスタンス不要で Chrome.get_driver(…) と呼べる入口を作る。補足：状態を持たない“ユーティリティ”として設計。

# 5. （get_driver が呼ばれたとき）options = Options() を作成する
# → Chromeの起動オプション（引数）を入れる容器を用意する。補足：ここではまだブラウザは起動しない。

# 6. （get_driver が呼ばれたとき）user_agent が渡されていれば options.add_argument(”–user-agent=…”) を追加する
# → 指定UAで起動する設定を付与する。補足：未指定なら何もしない（標準UAで起動）。

# 7. （get_driver が呼ばれたとき）driver = webdriver.Chrome(options=options) でブラウザを起動する
# → 指定オプションでChromeドライバーを立ち上げ、制御ハンドルを得る。補足：Chrome/ChromeDriverのバージョン不一致などの場合は WebDriverException が上位へ伝播する。

# 8. （get_driver が呼ばれたとき）return driver でWebDriverインスタンスを返す
# → 呼び出し側は driver.get(url) 等で操作できる。補足：ヘッドレスは未設定なので必要なら “–headless=new” を自分で追加する。