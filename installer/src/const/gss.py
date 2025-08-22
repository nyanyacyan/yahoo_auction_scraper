# ==========================================================
# import（標準、プロジェクト内モジュール）  # ここから必要なモジュールを読み込む

from typing import Final  # Finalは「変更しない定数」を示す型ヒント（静的解析向けの宣言）
    # 空行: ここからGoogleスプレッドシート関連の定数定義ブロック


# Google Sheets  # プロジェクトで使用するスプレッドシートとタブ名の既定値をまとめておく
SPREADSHEET_ID: Final[str] = "1nRJh0BqQazHe8qgT2YTZbMaZ9osPX835CbM3KkUjkcE"  # 対象スプレッドシートのID（URL中のキー部分）
SEARCH_COND_SHEET: Final[str] = "Master"  # 検索条件を記載するタブ名（読み取り元）
DEFAULT_OUTPUT_SHEET: Final[str] = "1"  # 出力の既定タブ名（書き込み先の初期値）
# 空行: ここから認証設定の定数定義ブロック

# 認証  # Google API認証で参照する環境変数名を一元管理
ENV_GOOGLE_CREDENTIALS_VAR: Final[str] = "GOOGLE_APPLICATION_CREDENTIALS"  # 認証JSONのパスを指す環境変数名
