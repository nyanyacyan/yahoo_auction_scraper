# ==========================================================
# import（標準、プロジェクト内モジュール）  # ここから必要なモジュールを読み込む

import os  # OSの環境変数（os.environ）を扱うための標準ライブラリ
from pathlib import Path  # パス操作用（app_root() が Path を返す想定のため補助的に読み込み）
from .paths import app_root  # プロジェクトのルートディレクトリ（Path）を返すヘルパー関数
    # 空行: ここからGoogle認証環境の初期化関数を定義する


# ==========================================================
# 関数定義

def ensure_google_credentials() -> None:  # Google関連の認証環境変数を安全に用意する（副作用のみで戻り値なし）
    """
    GOOGLE_* 環境変数が未設定なら、config/credentials.json を既定で使う。
    既に設定済みなら何もしない（冪等）。
    """  # 関数の目的と動作方針（既に設定済みならスキップ）を説明するdocstring

    if (  # いずれかの方法で認証情報が既に提供されているかをまとめて確認
        "GOOGLE_CREDENTIALS_JSON" in os.environ  # 生のJSON文字列を環境変数で渡す方式が設定済みか
        or "GOOGLE_CREDENTIALS_JSON_B64" in os.environ  # base64エンコードされたJSONが設定済みか
        or "GOOGLE_APPLICATION_CREDENTIALS" in os.environ  # 認証ファイルパスの環境変数が設定済みか
    ):
        return  # どれかが見つかったら何もせず終了（冪等性を担保）

    # 空行: 上記で未設定だった場合のみ、既定ファイルの存在を確認して設定する

    cred_path = app_root() / "config" / "credentials.json"  # 既定の認証ファイル（<app_root>/config/credentials.json）へのPathを組み立て
    if cred_path.exists():  # そのファイルが実在するかを確認
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(cred_path)  # 環境変数にパスを設定（gspread等のSDKが自動参照する）
