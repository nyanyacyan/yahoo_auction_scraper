# ==========================================================
# import（標準、プロジェクト内モジュール）  # 以降で使用するライブラリ/モジュールを読み込む宣言

import logging  # 標準ライブラリ。ログの出力・レベル制御などを行う
from typing import Optional, List, Dict, Any  # 型ヒント用の型。引数や戻り値の意図を明確にする
from selenium import webdriver  # SeleniumのWebDriver本体。ブラウザの自動操作に用いる
from selenium.webdriver.chrome.options import Options  # Chrome起動時の各種オプション設定を行うクラス
from selenium.common.exceptions import WebDriverException  # WebDriver関連の例外（起動失敗時など）を表す型
from installer.src.const import browser as CBR  # ブラウザ関連の既定値を集約した定数モジュールをCBRの別名で参照


# ==========================================================
# ログ設定  # このモジュール専用のロガーを取得して以降の情報出力に用いる

logger = logging.getLogger(__name__)  # モジュール名を付けたロガーを取得（ハンドラ/レベルは上位で設定想定）
# 空行: ここで論理的なまとまり（設定→クラス定義）を分け、読みやすさを確保する


# ==========================================================
# class定義

class Chrome:  # Selenium用のChromeDriverを構築・保持する薄いラッパークラス
    """
    Selenium で ChromeDriver を生成する薄いラッパ。
    既定値は installer.src.const.browser の定数から取得し、引数があればそれを優先する。
    """


    # ==========================================================
    # コンストラクタ

    def __init__(
        self,  # コンストラクタ。インスタンス生成時に呼ばれる
        *,
        headless: Optional[bool] = None,  # ヘッドレス実行の有無（未指定なら定数の既定値）
        user_agent: Optional[str] = None,  # UA文字列（未指定なら既定）
        window_size: Optional[str] = None,  # ウィンドウサイズ "幅x高さ" 形式（未指定なら既定）
        extra_args: Optional[List[str]] = None,  # 追加で渡すChrome起動引数（任意のリスト）
        binary_location: Optional[str] = None,  # Chrome実行ファイルのパス（明示指定したい場合）
        page_load_strategy: Optional[str] = None,  # ページ読み込み戦略 "normal"|"eager"|"none"
        prefs: Optional[Dict[str, Any]] = None,  # Chromeのprefs（ダウンロード先などの詳細設定）
        detach: Optional[bool] = None,  # Trueでスクリプト終了後もブラウザを自動で閉じない
    ) -> None:  # 戻り値はなし
        """
        Args:
            headless: True でヘッドレス起動。未指定は CBR.HEADLESS_DEFAULT
            user_agent: UA 文字列。未指定は CBR.USER_AGENT_DEFAULT
            window_size: "WxH" 形式。未指定は CBR.WINDOW_SIZE
            extra_args: 追加の --xxx Chrome 引数
            binary_location: Chrome 実行ファイルのパス。未指定は CBR.CHROME_BINARY
            page_load_strategy: "normal"|"eager"|"none"（未指定は CBR.PAGE_LOAD_STRATEGY）
            prefs: Chrome の prefs（未指定は CBR.PREFS）
            detach: True でブラウザを自動で閉じない（未指定は CBR.DETACH）
        Raises:
            WebDriverException: 起動失敗時（呼び出し側で捕捉してください）
        """
        # 上のdocstringは引数/例外の仕様説明。処理本体はこの下から

        # 既定値を const から解決  # 未指定（None）の項目はCBRの既定値を使う
        is_headless_mode = CBR.HEADLESS_DEFAULT if headless is None else bool(headless)  # ヘッドレス有無を決定
        user_agent_str = user_agent if user_agent else CBR.USER_AGENT_DEFAULT  # UA文字列を決定（空なら既定）
        window_size_str = window_size if window_size else CBR.WINDOW_SIZE  # ウィンドウサイズを決定
        page_load_strategy_str = page_load_strategy if page_load_strategy else CBR.PAGE_LOAD_STRATEGY  # 読み込み戦略を決定
        chrome_binary_path = binary_location if binary_location else CBR.CHROME_BINARY  # 実行ファイルパスを決定
        is_detach_enabled = CBR.DETACH if detach is None else bool(detach)  # detach指定の最終値を決定
        # 空行: ここからはオプション辞書(prefs)の組み立て処理に切り替わる

        # prefs は const を浅コピーしてユーザー指定を上書き  # 既定設定に対し呼び出し側の指定をマージする
        merged_prefs: Dict[str, Any] = dict(CBR.PREFS or {})  # Noneガードしつつdict化して編集可能にする
        if prefs:  # 呼び出し側からprefsが渡された場合のみ上書き
            merged_prefs.update(prefs)  # 既定に対してユーザー設定を反映
        # DOWNLOAD_DIR が指定されていたら prefs に適用  # ダウンロード先の既定ディレクトリを設定
        if CBR.DOWNLOAD_DIR:  # 定数でダウンロード先が定義されている場合
            merged_prefs.setdefault("download.default_directory", CBR.DOWNLOAD_DIR)  # 既に指定がなければ適用
        # 空行: ここからChromeの起動オプション(Options)を構築する

        # Options 構築  # Chrome起動用のオプションコンテナを作成
        chrome_options: Options = Options()  # 以降のadd_argument等で設定を積み上げる器
        # 空行: ページ読み込み戦略の設定ブロックに続く

        # page load strategy  # Selenium4以降の属性で読み込み戦略を切り替える
        try:
            chrome_options.page_load_strategy = page_load_strategy_str  # eager/normal/noneのいずれかを適用
        except Exception:  # 環境差やバージョン差で失敗しても致命ではない
            pass  # 失敗時はデフォルト戦略にフォールバック
        # 空行: ここから個別のオプション（ヘッドレス/UA/サイズ等）の付与

        # ヘッドレス  # 画面を表示せずに実行する設定
        if is_headless_mode:  # Trueのときのみヘッドレスフラグを付与
            # 新ヘッドレス（Chrome 109+）  # 新方式のヘッドレスを明示して互換性を確保
            chrome_options.add_argument("--headless=new")  # 新ヘッドレスモードを有効化

        # UA  # サイト側の振る舞いに影響するUser-Agentを指定
        if user_agent_str:  # 空文字でなければ設定
            chrome_options.add_argument(f"--user-agent={user_agent_str}")  # UAをコマンドライン引数で渡す

        # ウィンドウサイズ  # 初期ウィンドウの幅×高さを指定
        if window_size_str:  # 値があれば反映
            chrome_options.add_argument(f"--window-size={window_size_str}")  # 例: "1280,720" ではなく "1280x720" に注意

        # 既定の追加引数  # プロジェクトで共通に付けたい安定化オプション群
        for arg in CBR.BASE_ARGS:  # 事前に定義された引数リストを順に適用
            chrome_options.add_argument(arg)  # 例: サンドボックス無効化等（環境依存の安定化目的）

        # 任意の追加引数  # 呼び出し側が更に細かいフラグを足せる拡張ポイント
        if extra_args:  # リストが与えられたときのみ処理
            for arg in extra_args:  # 各要素を検証しつつ追加
                if arg and isinstance(arg, str):  # None/空や非文字列を弾く簡易バリデーション
                    chrome_options.add_argument(arg)  # 妥当な引数のみ追加する

        # 実行ファイルパス  # システム既定のChromeが使えない環境で明示パスを指定する
        if chrome_binary_path:  # パスが解決できた場合のみ設定
            chrome_options.binary_location = chrome_binary_path  # 指定パスのChromeを使用する

        # experimental options  # 実験的APIでprefs/detach等をまとめて指定
        if merged_prefs:  # 設定辞書が存在する場合のみ
            chrome_options.add_experimental_option("prefs", merged_prefs)  # ダウンロード先などの詳細設定を適用
        chrome_options.add_experimental_option("detach", is_detach_enabled)  # Trueならスクリプト終了後もブラウザを閉じない
        # 空行: ここで主要な起動パラメータをログ出力してデバッグ容易化

        # ログ（主要設定のみ）  # 起動時の重要パラメータを記録（UAは有無だけBoolで表示して冗長さを抑制）
        logger.info(
            "Launching Chrome: headless=%s, window=%s, pls=%s, ua=%s, detach=%s",
            is_headless_mode, window_size_str, page_load_strategy_str, bool(user_agent_str), is_detach_enabled
        )
        # 空行: 実際にChromeDriverを起動する処理に入る

        # ドライバ生成（Selenium 4.6+ は driver manager 内蔵）  # WebDriverManager内蔵で自動取得/起動が可能
        self._webdriver: webdriver.Chrome = webdriver.Chrome(options=chrome_options)  # 上で組んだオプションを渡して起動


    # ==========================================================
    # メソッド定義

    @property  # 属性アクセス経由でdriverを取得できるようにするプロパティ
    def driver(self) -> webdriver.Chrome:  # 呼び出し側に返すのはChromeのWebDriver型
        """生成済み WebDriver を返す"""  # 短いdocstringでプロパティの役割を説明
        return self._webdriver  # __init__で生成したWebDriverインスタンスをそのまま返す
        # 空行: ここから下は旧コードとの互換インターフェースを提供する


    # ==========================================================
    # メソッド定義

    @staticmethod  # インスタンス化せずに呼び出せるメソッドとして定義
    def get_driver(
        headless: Optional[bool] = None,  # そのままChrome.__init__に渡すヘッドレス指定
        user_agent: Optional[str] = None,  # そのままChrome.__init__に渡すUA指定
        **kwargs: Any,  # その他の任意キーワード引数を受け取り、そのまま委譲
    ) -> webdriver.Chrome:  # 戻り値は起動済みのWebDriver
        """
        旧コード互換のためのショートカット。
        __init__ の引数をそのまま受け取り、 driver を返す。
        例:
            Chrome.get_driver(headless=True, user_agent=".../Mobile")
        """
        # 空行: 互換APIの実体はChromeの一時インスタンスを作ってdriverだけ返すシンプルな仕組み

        instance = Chrome(  # 一時的にChromeラッパーを生成
            headless=headless,  # ヘッドレス指定を委譲
            user_agent=user_agent,  # UA指定を委譲
            **kwargs,  # 残りの引数もまとめて委譲（window_sizeやprefs等）
        )  # ここで__init__が実行されWebDriverが立ち上がる
        return instance.driver  # ラッパー内のWebDriver本体だけを取り出して返す
