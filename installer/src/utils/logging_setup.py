# ==========================================================
# import（標準、プロジェクト内モジュール）  # ここから必要なモジュールを読み込む

import logging  # 標準のロギング機能を使うためのモジュールを読み込む
from typing import Optional  # 関数引数で None 許容などを明示するための型ヒント
from installer.src.utils.log_trimmer import install_log_trimmer  # ライブラリ由来の冗長ログを抑える初期化関数
from installer.src.utils.logger_color import enable_colored_console  # コンソール出力に色を付けるハンドラ設定関数


# ==========================================================
# class定義

class HideDateParseDebug(logging.Filter):  # 特定メッセージを除外するためのログフィルタを定義
    """特定のDEBUGログを抑止"""  # 目的：終了日時パース関連の DEBUG を見えなくする


    # ==========================================================
    # メソッド定義

    def filter(self, record: logging.LogRecord) -> bool:  # 各ログレコードに対して表示可否(True/False)を返す
        return not (  # 条件に一致したら False を返す＝ログを落とす
            record.levelno == logging.DEBUG  # DEBUG レベルのときに対象とする
            and record.name == "installer.src.flow.base.utils"  # 対象ロガー名を限定
            and "終了日時パース" in record.getMessage()  # メッセージに特定文言が含まれているか
        )

_BOOTSTRAPPED_LOG = False  # 初期化の二重実行を防ぐフラグ（True なら再初期化しない）


# ==========================================================
# 関数定義

def configure_logging(level: int = logging.INFO,  # ルートのログレベル既定（INFO）
                    hide_date_parse_debug: bool = True,  # 日付パースのDEBUGを隠すか
                    mute_ready_state: bool = True,  # SeleniumのreadyStateポーリングなどを抑制するか
                    console_level: Optional[int] = None) -> None:  # コンソール専用の最低レベル（未指定なら level を流用）
    """
    ログの初期化（冪等）。多重ハンドラを避ける。  # 何度呼んでも安全に初期化されることを保証
    """
    global _BOOTSTRAPPED_LOG  # モジュールスコープのフラグを更新するために global 宣言
    if _BOOTSTRAPPED_LOG:  # 既に初期化済みなら何もしない
        return  # 早期リターンで二重設定を回避

    # ベース設定 + 既存ハンドラ除去  # force=True で basicConfig を強制適用し既存ハンドラをクリア
    logging.basicConfig(level=level, force=True)  # 以後のログ出力の基礎設定を行う

    # 冗長ログ抑止（requests等）  # ライブラリの成功時ノイズ（2xxなど）をまとめてミュート
    install_log_trimmer(console_level=console_level or level,  # ルート/コンソールの最低レベルを設定
                        mute_ready_state=mute_ready_state)  # readyState系ログの抑制設定を反映

    # カラー出力（既存のStreamHandlerは付け替え）  # StreamHandler を外し色付きハンドラに差し替える
    root = logging.getLogger()  # ルートロガーを取得
    for h in list(root.handlers):  # 現在付いているハンドラを列挙
        if isinstance(h, logging.StreamHandler):  # コンソール出力用のハンドラが対象
            root.removeHandler(h)  # 重複出力を避けるため一旦外す

    enable_colored_console(  # コンソール向けに色付きのフォーマッタを設定
        level=console_level or level,  # ハンドラ側のレベルを指定（未指定なら level を使用）
        fmt="%(levelname)s - %(name)s:%(lineno)d - %(message)s",  # 簡潔で見やすい出力フォーマット
    )

    if hide_date_parse_debug:  # 指定がある場合のみフィルタを適用
        for h in root.handlers:  # すべてのハンドラに対して
            h.addFilter(HideDateParseDebug())  # 終了日時パース系の DEBUG を抑止するフィルタを付与

    _BOOTSTRAPPED_LOG = True  # 初期化済みフラグを立て、次回以降の再設定を防ぐ
