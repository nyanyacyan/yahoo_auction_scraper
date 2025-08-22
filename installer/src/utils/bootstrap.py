# ==========================================================
# import（標準、プロジェクト内モジュール）  # ここから必要なモジュールを読み込む

import logging  # ログレベル（INFO/DEBUGなど）や基本的なログ機能を使うための標準ライブラリを読み込む
from installer.src.utils.logging_setup import configure_logging  # プロジェクト共通のログ設定関数をインポート
from installer.src.utils.credentials import ensure_google_credentials  # Google認証情報の準備関数をインポート

_BOOTSTRAPPED = False  # 初期化（bootstrap）が既に実行済みかを示すフラグ。冪等性の担保に使う


# ==========================================================
# 関数定義

def bootstrap(debug: bool = False) -> None:  # アプリ起動時の共通初期化を行う関数。debug=Trueで詳細ログに切替
    """
    アプリ起動時の共通初期化。冪等。
    """  # 上のdocstringは関数の目的（初期化を一度だけ実施）を説明する

    global _BOOTSTRAPPED  # モジュールスコープのフラグを書き換えるためにglobal宣言
    if _BOOTSTRAPPED:  # 既に初期化済みなら何もせず即return（重複初期化を防止）
        return  # 冪等性: 二重実行時の副作用を避ける

    configure_logging(level=(logging.DEBUG if debug else logging.INFO),  # ログ出力の基本設定。debug引数でレベルを切替
                    hide_date_parse_debug=True,  # 日付パースの細かいデバッグログを非表示にするオプション
                    mute_ready_state=True)  # readyState関連の冗長ログを抑制するオプション

    ensure_google_credentials()  # 必要なGoogle認証情報（環境変数/ファイル等）を確認・設定する

    _BOOTSTRAPPED = True  # 初期化済みフラグを立てる。以後この関数は処理をスキップする
