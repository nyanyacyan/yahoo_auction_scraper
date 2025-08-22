# ==========================================================
# import（標準、プロジェクト内モジュール）  # ここから必要なモジュールを読み込む

import logging  # Python標準のログ機能を提供するモジュール。ログレベルやハンドラ設定に使う
import re  # 正規表現を扱うモジュール。ログメッセージのパターン判定に使用
from typing import Any, Callable  # 型ヒント用。柔軟な引数型やコールバックの型を明示
try:  # 例外発生（モジュール未存在等）に備えた読み込みブロック
    from installer.src.const import log as C_LOG  # プロジェクトのログ関連定数を読み込む（推奨パス）
except Exception:  # 何らかの理由で読み込めない場合のフォールバック定義に入る


    # ==========================================================
    # class定義  # WebDriver操作を高レベルAPIとしてまとめる

    class _FallbackLogConst:  # 最低限必要な定数を備えた代替クラス（本番定数が無くても動かすため）
        CONSOLE_FORMAT = "%(levelname)s:%(name)s:%(message)s"  # コンソール出力のログフォーマット
        CONSOLE_LEVEL = "INFO"  # ルートロガーの既定レベル（文字列指定）
        URLLIB3_LEVEL = "WARNING"  # urllib3 の既定ログレベル
        NOISY_LOGGERS = (  # ノイズを出しがちなロガー名の集合（抑制対象）
            "selenium.webdriver.remote.remote_connection",
            "selenium.webdriver.common.selenium_manager",
            "urllib3.connectionpool",
        )
        ENABLE_FILTER_HTTP200 = True  # HTTP200行を抑制するかどうか
        ENABLE_FILTER_STATUS_2XX = True  # 2xxステータス行を抑制するかどうか
        ENABLE_FILTER_FINISHED_REQ = True  # “Finished Request”行を抑制するかどうか
        ENABLE_FILTER_READY_STATE = True  # readyStateポーリングログを抑制するかどうか
        RE_HTTP200  = r'HTTP/1\.1"\s+200\b'  # HTTP200を検出するための正規表現
        RE_STATUS   = r'status=(\d{3})'  # ステータスコードを抽出する正規表現
        RE_READY    = r'execute/sync.*document\.readyState'  # readyStateポーリング検出用パターン
        RE_FINISHED = r'Finished Request'  # 処理完了ログ検出用パターン
        DEFAULT_MUTE_READY_STATE = True  # readyStateログ抑制のデフォルト値
        DISABLE_PROPAGATION = True  # ロガーの親伝播を止める既定フラグ
    C_LOG = _FallbackLogConst()  # type: ignore  # 実際の定数が無い場合はこのフォールバックをC_LOGとして使う


# ==========================================================
# 関数定義

def _to_level(level_like: Any, default: int = logging.INFO) -> int:  # 文字列/数値をloggingレベルの整数へ変換する補助関数
    """文字列/数値いずれも logging レベルへ正規化"""  # 関数の目的を1行で説明（詳細は実装参照）
    if isinstance(level_like, int):  # すでに数値レベルならそのまま返す
        return level_like  # 例: logging.DEBUG(10) 等
    level_str = str(level_like).strip().upper()  # "debug" → "DEBUG"のように正規化
    return getattr(logging, level_str, default)  # 定義が無ければ既定レベルを返す


# ==========================================================
# class定義

class _DropSeleniumNoise:  # ログRecordを受け取り、不要なメッセージを落とすフィルタ
    """Selenium/urllib3の“成功時ノイズ”を抑制するフィルタ（const制御対応）。"""  # 目的：成功時の冗長ログを隠す


    # ==========================================================
    # コンストラクタ

    def __init__(self, mute_ready_state: bool | None = None) -> None:  # 抑制の各種フラグと正規表現を初期化
        # const 側の既定を採用（引数が None のとき）  # 呼び出し側未指定なら定数の既定値を使う
        if mute_ready_state is None:  # 引数が省略された場合の扱い
            mute_ready_state = bool(getattr(C_LOG, "DEFAULT_MUTE_READY_STATE", True))  # 定数から既定値を取得
        self.mute_ready_state: bool = bool(mute_ready_state)  # インスタンスに保持しfilter内で参照

        # パターンを const から注入  # どのログを落とすかを正規表現で表現
        self.re_http200: re.Pattern[str] = re.compile(getattr(C_LOG, "RE_HTTP200", r'HTTP/1\.1"\s+200\b'))  # HTTP200検出
        self.re_status:  re.Pattern[str] = re.compile(getattr(C_LOG, "RE_STATUS",  r'status=(\d{3})'))  # ステータス抽出
        self.re_ready:   re.Pattern[str] = re.compile(getattr(C_LOG, "RE_READY",   r'execute/sync.*document\.readyState'))  # readyState
        self.re_finish:  re.Pattern[str] = re.compile(getattr(C_LOG, "RE_FINISHED", r'Finished Request'))  # 完了ログ

        # 有効/無効フラグ  # どのフィルタを適用するかを定数から制御
        self.en_http200         = bool(getattr(C_LOG, "ENABLE_FILTER_HTTP200", True))  # HTTP200の抑制可否
        self.en_status_2xx      = bool(getattr(C_LOG, "ENABLE_FILTER_STATUS_2XX", True))  # 2xx抑制可否
        self.en_finished_req    = bool(getattr(C_LOG, "ENABLE_FILTER_FINISHED_REQ", True))  # 完了ログ抑制可否
        self.en_ready_state     = bool(getattr(C_LOG, "ENABLE_FILTER_READY_STATE", True))  # readyState抑制可否


    # ==========================================================
    # メソッド定義

    def filter(self, record: logging.LogRecord) -> bool:  # ログRecord毎に呼ばれ、Trueで通過/Falseで棄却
        msg: str = record.getMessage()  # 実際のメッセージ文字列を取り出す

        # urllib3: ..."HTTP/1.1" 200 ...  # HTTP200は成功なのでノイズとして落とす
        if self.en_http200 and self.re_http200.search(msg):  # パターン一致かつ有効時のみ
            return False  # ログを非表示にする

        # selenium: Remote response: status=200 ...  # ステータスコード2xxなら同様に落とす
        if self.en_status_2xx:  # 機能自体が有効な場合のみ判定
            status_match = self.re_status.search(msg)  # "status=200" のような部分にマッチ
            if status_match and 200 <= int(status_match.group(1)) < 300:  # 2xx範囲かどうか判定
                return False  # 成功ノイズとして抑制

        # selenium: Finished Request  # リクエスト完了ログは冗長なため抑制
        if self.en_finished_req and self.re_finish.search(msg):  # パターン一致チェック
            return False  # 非表示

        # selenium: readyState ポーリング  # DOM準備状態のポーリングログを抑制（設定でON/OFF）
        if self.en_ready_state and self.mute_ready_state and self.re_ready.search(msg):  # 条件が全て満たされたら
            return False  # 非表示

        return True  # どの抑制条件にも該当しなければ表示する


# ==========================================================
# 関数定義

def _set_level_and_filter(logger_name: str, level: int, noise_filter: Any) -> None:  # 指定ロガーにレベル/フィルタを設定
    target_logger: logging.Logger = logging.getLogger(logger_name)  # 名前からロガーを取得
    target_logger.setLevel(level)  # 指定レベルに設定（例: WARNING）
    # 伝播抑制は const で制御  # 親ロガーへログを伝播させるかを切替
    if bool(getattr(C_LOG, "DISABLE_PROPAGATION", True)):  # 既定で伝播停止が有効
        target_logger.propagate = False  # 親ロガーへ流さない
    target_logger.addFilter(noise_filter)  # ロガー自身にフィルタを追加
    for handler in target_logger.handlers:  # 既存ハンドラにも同じフィルタを付与
        handler.addFilter(noise_filter)  # ハンドラ側でもフィルタ適用（重複表示対策）


# ==========================================================
# class定義

class _CleanupFiltersCallable:  # cleanup 処理を保持する“呼び出し可能”オブジェクト
    """適用したフィルタを解除するための呼び出し体（関数の入れ子定義を避ける）。"""  # __call__で実行できる


    # ==========================================================
    # コンストラクタ

    def __init__(self, targets: list[str], noise_filter: Any) -> None:  # 解除対象ロガーとフィルタを受け取る
        self._targets = list(targets)  # ロガー名のリストを保持
        self._noise_filter = noise_filter  # 除去対象のフィルタ参照を保持


    # ==========================================================
    # メソッド定義

    def __call__(self) -> None:  # () で呼び出すとフィルタ除去が実行される
        for logger_name in self._targets:  # 各ロガーに対して
            target_logger = logging.getLogger(logger_name)  # ロガーを取得
            target_logger.filters = [f for f in target_logger.filters if f is not self._noise_filter]  # ロガー直下のフィルタから除去
            for handler in target_logger.handlers:  # 各ハンドラのフィルタも
                handler.filters = [f for f in handler.filters if f is not self._noise_filter]  # 同様に除去


# ==========================================================
# 関数定義

def install_log_trimmer(  # ライブラリ由来の“成功時ノイズ”をまとめて抑える初期化関数
    console_level: int | str = None,  # ルートの最低ログレベル。文字列/数値どちらでも可
    mute_ready_state: bool | None = None,  # readyStateログを抑制するか。Noneなら定数の既定
) -> Callable[[], None]:  # 呼び出し後に解除するためのCallableを戻り値として返す（入れ子関数は定義しない）
    """
    ライブラリのノイズをミュートする。戻り値 cleanup() で解除可。
    - console_level     : ルートロガーの最低レベル（未指定なら const）
    - mute_ready_state  : readyStateポーリング抑制（未指定なら const）
    """  # 利用者向けの使い方と引数の意味を説明

    # 既定値を const から決定  # 引数が省略時は定数のデフォルトを採用
    if console_level is None:  # ルートロガーの最低レベル未指定の場合
        console_level = getattr(C_LOG, "CONSOLE_LEVEL", "INFO")  # 既定はINFO（文字列）
    if mute_ready_state is None:  # readyState抑制の指定が無い場合
        mute_ready_state = getattr(C_LOG, "DEFAULT_MUTE_READY_STATE", True)  # 既定はTrue

    # ルート設定（未設定なら）  # まだハンドラが無い=未初期化なら basicConfig で最小設定
    root_logger: logging.Logger = logging.getLogger()  # ルートロガーを取得
    if not root_logger.handlers:  # 既に設定済みかどうかを確認
        logging.basicConfig(  # 最低限のコンソール出力設定を行う
            level=_to_level(console_level),  # 文字列/数値どちらでも受けて整数レベルへ
            format=str(getattr(C_LOG, "CONSOLE_FORMAT", "%(levelname)s:%(name)s:%(message)s")),  # 出力フォーマット
        )

    noise_filter = _DropSeleniumNoise(mute_ready_state=mute_ready_state)  # フィルタインスタンスを生成（設定を反映）

    # “3点セット”ほかノイズ源に WARN レベル & フィルタ  # 主要なノイズロガーへ一括適用
    noisy_logger_names = tuple(getattr(C_LOG, "NOISY_LOGGERS", (  # 対象ロガー名のタプルを取得（定数から）
        "selenium.webdriver.remote.remote_connection",
        "selenium.webdriver.common.selenium_manager",
        "urllib3.connectionpool",
    )))  # 既定の3つ（必要に応じて定数側で拡張）
    for logger_name in noisy_logger_names:  # 対象ロガーそれぞれに設定を適用
        _set_level_and_filter(logger_name, logging.WARNING, noise_filter)  # レベルをWARNにし、フィルタを付与

    # 予防的に urllib3 全体も抑える  # connectionpool以外のurllib3ログも抑制したい場合の保険
    urllib3_log_level = _to_level(getattr(C_LOG, "URLLIB3_LEVEL", "WARNING"), logging.WARNING)  # 既定レベルの解決
    target_logger = logging.getLogger("urllib3")  # urllib3ルートロガー
    target_logger.setLevel(urllib3_log_level)  # レベル設定
    if bool(getattr(C_LOG, "DISABLE_PROPAGATION", True)):  # 親伝播の抑止が有効なら
        target_logger.propagate = False  # 伝播を止める（重複表示防止）

    targets: list[str] = list(noisy_logger_names) + ["urllib3"]  # 解除対象ロガー一覧（3点+urllib3）
    cleanup_callable = _CleanupFiltersCallable(targets=targets, noise_filter=noise_filter)  # 入れ子関数の代わりに呼び出し体を生成
    return cleanup_callable  # 設定適用の解除関数オブジェクトを返す（__call__で実行）
