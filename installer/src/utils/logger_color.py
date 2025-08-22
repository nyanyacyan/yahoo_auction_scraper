# ==========================================================
# import（標準、プロジェクト内モジュール）  # ここから必要なモジュールを読み込む

import logging  # ログ機能を提供する標準ライブラリ。レベル/フォーマットを扱う
import sys  # stdout/stderr の参照や TTY 判定に利用
from typing import Any  # 関数引数などの型ヒント用（柔軟な型指定）
try:
    from installer.src.const import log as C_LOG  # プロジェクト共通のログ設定定数を読み込む
except Exception:


    # ==========================================================
    # class定義

    class _FallbackLogConst:  # 定数が無い環境でも動くよう最低限の既定値を定義
        ENABLE_COLOR = True  # 色出力を有効にする既定
        COLOR_TTY_ONLY = True  # 端末（TTY）上のみ色付けするかのフラグ
        FORCE_COLOR = False  # 強制的に色付けするか（TTY でなくても）
        COLOR_RESET = "\033[0m"  # ANSIカラーのリセットコード
        COLOR_LEVEL_MAP = {  # ログレベルごとの色コード対応表
            "DEBUG":    "\033[90m",
            "INFO":     "\033[94m",
            "WARNING":  "\033[93m",
            "ERROR":    "\033[91m",
            "CRITICAL": "\033[95m",
        }
        CONSOLE_DATEFMT = "%H:%M:%S"  # 日付表示のフォーマット（時:分:秒）
        # 既定の“色付き向け”フォーマット  # 行頭に時刻、レベル、ロガー名:行番号、メッセージ
        CONSOLE_FORMAT_COLORED = "%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s"
        # 既存のシンプル既定（無ければこちらは未使用）  # 色無し環境向けの簡易フォーマット
        CONSOLE_FORMAT = "%(levelname)s:%(name)s:%(message)s"
        CONSOLE_STREAM = "stdout"  # 出力先ストリーム（stdout or stderr）
    C_LOG = _FallbackLogConst()  # type: ignore  # 実際の定数が無い場合はこちらを C_LOG として使う


# ==========================================================
# 関数定義

def _is_tty(stream: Any) -> bool:  # ストリームが TTY（端末）かどうかを判定する
    try:
        return stream.isatty()  # TTYなら True、ファイルやVSCodeのコンソール等は False
    except Exception:
        return False  # isatty が無い/失敗した場合は TTY ではない扱い


# ==========================================================
# 関数定義

def _pick_stream() -> Any:  # 出力先のストリーム（stdout/stderr）を定数に従って選ぶ
    """const の CONSOLE_STREAM に応じて stdout/stderr を選択。"""  # 設定により出力先を切り替える
    stream_target = str(getattr(C_LOG, "CONSOLE_STREAM", "stdout")).lower()  # 設定値を小文字化
    return sys.stderr if stream_target == "stderr" else sys.stdout  # 既定は stdout


# ==========================================================
# 関数定義

def _should_color(stream: Any) -> bool:  # 色付けを行うべきかを総合判定
    if not bool(getattr(C_LOG, "ENABLE_COLOR", True)):  # まず機能自体が無効なら
        return False  # 色付けしない
    if bool(getattr(C_LOG, "FORCE_COLOR", False)):  # 強制フラグがあれば
        return True  # 常に色付けする
    if bool(getattr(C_LOG, "COLOR_TTY_ONLY", True)):  # TTY のみ色付けする設定なら
        return _is_tty(stream)  # 実際に TTY かどうかで判断
    return True  # それ以外は色付けOK


# ==========================================================
# class定義

class AnsiColorFormatter(logging.Formatter):  # ANSIカラーを付与する専用フォーマッタ


    # ==========================================================
    # コンストラクタ

    def __init__(
        self,
        fmt: str | None = None,  # メッセージのフォーマット文字列
        datefmt: str | None = None,  # 日付文字列のフォーマット
        style: str = "%",  # フォーマットの記法（%/{}/$）
        validate: bool = True,  # フォーマットの検証を行うか
    ) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt, style=style, validate=validate)  # 親クラス初期化
        self._colors: dict[str, str] = dict(getattr(C_LOG, "COLOR_LEVEL_MAP", {}))  # レベル→色コードの辞書
        self._reset: str = str(getattr(C_LOG, "COLOR_RESET", "\033[0m"))  # 末尾に付けるリセットコード


    # ==========================================================
    # メソッド定義

    def format(self, record: logging.LogRecord) -> str:  # 1件のログレコードを文字列に整形
        formatted_msg: str = super().format(record)  # まず親クラスの通常整形を行う
        level_color: str = self._colors.get(record.levelname, "")  # レベルに対応する色を取得（無ければ空）
        return f"{level_color}{formatted_msg}{self._reset}" if level_color else formatted_msg  # 色があれば前後に付与


# ==========================================================
# 関数定義

def enable_colored_console(
    level: int | None = None,  # ロガーの出力レベル（Noneなら変更しない）
    logger_name: str | None = None,  # 対象ロガー名（Noneならルートロガー）
    fmt: str | None = None,  # フォーマット文字列の上書き
    datefmt: str | None = None,  # 日付フォーマットの上書き
) -> None:
    """
    コンソール（StreamHandler）だけ色付きにする。ファイル出力は無着色のまま。
    VS Code の Debug Console 等、TTY じゃない所では const に従って自動無色化。
    """  # 目的：コンソール出力にのみ色を付与し、環境に応じて自動切替

    # フォーマット既定は引数 > const(C_LOG.CONSOLE_FORMAT_COLORED or CONSOLE_FORMAT) > ハードコード  # 優先順位を明示
    fmt = (
        fmt  # 呼び出し引数があればそれを採用
        or getattr(C_LOG, "CONSOLE_FORMAT_COLORED", None)  # 色付き向け既定
        or getattr(C_LOG, "CONSOLE_FORMAT", None)  # 色無し既定（フォールバック）
        or "%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s"  # 最終フォールバック
    )
    datefmt = datefmt or getattr(C_LOG, "CONSOLE_DATEFMT", "%H:%M:%S")  # 日付フォーマットの決定

    logger: logging.Logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()  # 対象ロガーを取得
    if level is not None:
        logger.setLevel(level)  # ロガー自体のレベルを必要に応じて設定

    # 既存のコンソール用ハンドラを外して重複回避  # 二重出力を防ぐため既存のStreamHandlerを取り除く
    for handler in list(logger.handlers):
        if isinstance(handler, logging.StreamHandler) and getattr(handler, "stream", None) in (sys.stdout, sys.stderr):
            logger.removeHandler(handler)  # stdout/stderr を使う既存ハンドラのみ除去

    output_stream = _pick_stream()  # 出力先（stdout/stderr）を選択
    handler: logging.StreamHandler = logging.StreamHandler(output_stream)  # 新しいコンソールハンドラを作成

    if _should_color(output_stream):  # 色付けを行うべき環境かを判定
        handler.setFormatter(AnsiColorFormatter(fmt=fmt, datefmt=datefmt))  # 色付きフォーマッタを適用
    else:
        handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))  # 通常のフォーマッタを適用

    if level is not None:
        handler.setLevel(level)  # ハンドラ側のレベルも必要なら指定

    logger.addHandler(handler)  # 準備できたハンドラをロガーに登録（以後の出力に反映）
