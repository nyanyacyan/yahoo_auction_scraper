# ==========================================================
# import（標準、プロジェクト内モジュール）  # ここから必要なモジュールを読み込む

import os  # 環境変数からIDなどを取得するために使用
import os as _os  # 別名でも参照できるようにして関数内で明示する用途向け
from typing import Final  # 「変更しない定数」の意図を型ヒントで表す
from typing import Final, Tuple  # タプル型の定数を定義するために使用
from typing import Final, List, Any  # リストや任意型の型ヒントに使用
from pathlib import Path  # ファイルパス操作（認証ファイルの既定パス生成に使用）


SPREADSHEET_ID: Final[str] = os.getenv(  # 使うスプレッドシートのIDを環境変数から取得（無ければ既定値）
    "GSS_ID_MAIN",  # 参照する環境変数名
    "1nRJh0BqQazHe8qgT2YTZbMaZ9osPX835CbM3KkUjkcE"  # ログに出ているID（必要なら.envで上書き）  # 既定値
)  # os.getenvの閉じ括弧

TAB_MASTER: Final[str] = "Master"  # 条件入力などのマスタ情報を置くタブ名
TAB_FMT:    Final[str] = "FMT"  # 形式定義やテンプレート用のタブ名

# 出力列（並びの定義を1か所に）  # スプレッドシートへ書き込むカラム順を固定
COLS: Final[list[str]] = [  # 出力時の列順リストを定数化
    "input_date", "date", "title", "price", "ct", "1ct_price", "image", "url",  # 各列名（文字列）
]  # リスト終端

# 日付表示用のフォーマット（Python側）  # 文字列化に使うstrftimeの形式
DATE_FMT:       Final[str] = "%Y-%m-%d"  # 終了日などの日付だけを表すフォーマット
INPUT_DATE_FMT: Final[str] = "%Y/%m/%d %H:%M"  # 取得日時などの日時形式（分まで）
TEXT_PREFIX:    Final[str] = "'"  # 先頭に付けて「文字列扱い」にするためのプレフィックス

# 新規ワークシート作成時のサイズ  # タブ自動生成時の行数・列数の既定
DEFAULT_WS_ROWS: Final[int] = 1000  # 既定行数
DEFAULT_WS_COLS: Final[int] = 26  # 既定列数（A〜Zの想定）

# gspread の更新オプション  # 値の入力方式（ユーザー入力として扱う）
VALUE_INPUT_OPTION: Final[str] = "USER_ENTERED"  # 数式・日付などをスプレッドシート側解釈に任せる

# 追記の起点となる列（アンカー）  # 追記開始行を判定するため、どの列を埋まり具合の基準にするか
APPEND_ANCHOR_COLUMN: Final[str] = "A"  # A列を起点とする
APPEND_ANCHOR_COLUMN_INDEX: Final[int] = 1  # gspread.col_values で使う 1 始まりの列番号

# URL 列の判定に使うヘッダ候補（正規マッチ）  # ヘッダ名がこれらならURL列とみなす
URL_HEADER_CANDIDATES: Final[Tuple[str, ...]] = (  # 厳密一致用の候補群
    "url", "detail_url", "link", "リンク",  # 英語/日本語の代表的な列名
)  # タプル終端

# あいまい系（全角など）  # 全角などゆるい一致でURL列と判定したい場合
URL_HEADER_FUZZY: Final[Tuple[str, ...]] = (  # ゆるい候補群
    "url", "ｕｒｌ",  # 全角/半角違いを許容
)  # タプル終端


# ==========================================================
# 関数定義

def _env_int(name: str, default: int) -> int:  # 整数の環境変数を安全に読み取るヘルパー
    v = _os.environ.get(name)  # 文字列で取得
    if v is None or v.strip() == "":  # 未設定や空なら
        return default  # 既定値を返す
    try:
        return int(v)  # 正常なら整数化して返す
    except ValueError:
        return default  # 変換失敗時も既定値にフォールバック

SHEET_IMAGE_FUNCTION_NAME: Final[str] = _os.environ.get("SHEET_IMAGE_FUNCTION_NAME", "IMAGE")  # 画像貼付に使う関数名
SHEET_IMAGE_MODE: Final[int]           = _env_int("SHEET_IMAGE_MODE", 4)                 # 4 = カスタム  # IMAGE関数のモード
SHEET_IMAGE_WIDTH_PX: Final[int]       = _env_int("SHEET_IMAGE_WIDTH_PX", 80)  # 画像の幅（ピクセル）
SHEET_IMAGE_HEIGHT_PX: Final[int]      = _env_int("SHEET_IMAGE_HEIGHT_PX", 80)  # 画像の高さ（ピクセル）

# 文字列テンプレート。{url}/{mode}/{width}/{height} を埋め込みます。  # =IMAGE() の式フォーマット
SHEET_IMAGE_TEMPLATE: Final[str] = _os.environ.get(  # 画像セルに挿入する式のテンプレ文字列
    "SHEET_IMAGE_TEMPLATE",  # 環境変数で上書き可能
    '=IMAGE("{url}", {mode}, {width}, {height})'  # 既定テンプレート（プレースホルダを後でformat）
)  # os.environ.get の閉じ括弧

# 空行: ここから Master 関連の列名・シート名などの定義
# ---- シート名（Masterタブ名を環境から差し替え可能） ----  # デプロイ先でタブ名が違う場合に対応
MASTER_SHEET_NAME: Final[str] = _os.environ.get("MASTER_SHEET_NAME", "Master")  # 既定は "Master"

# ---- 列名（Master のヘッダに合わせる）----  # 取り出す列キー名の既定
COL_START_DATE: Final[str] = _os.environ.get("COL_START_DATE", "start_date")  # 開始日の列名
COL_END_DATE:   Final[str] = _os.environ.get("COL_END_DATE", "end_date")  # 終了日の列名
COL_CHECK:      Final[str] = _os.environ.get("COL_CHECK", "check")  # 処理対象フラグの列名

# ---- 認証情報の入力元（環境変数キー）----  # 認証JSONをどこから読むかをキー名で定義
ENV_JSON: Final[str] = "GOOGLE_CREDENTIALS_JSON"       # JSON文字列そのものを渡す場合の環境変数名
ENV_B64:  Final[str] = "GOOGLE_CREDENTIALS_JSON_B64"   # base64エンコードしたJSONの環境変数名
ENV_FILE: Final[str] = "GOOGLE_APPLICATION_CREDENTIALS" # 認証ファイルパスの環境変数名

# ---- Google API スコープ ----  # gspread/Drive APIで必要な権限スコープ
GSPREAD_SCOPES: Final[List[str]] = [  # 認可時に使用するスコープ一覧
    "https://www.googleapis.com/auth/spreadsheets",  # スプレッドシート操作
    "https://www.googleapis.com/auth/drive",  # ファイル作成/共有などDrive操作
]  # リスト終端


# ==========================================================
# 関数定義

def default_credentials_path() -> Path:  # 既定のcredentials.jsonの絶対パスを返す
    # const からの相対位置で {repo_root}/config/credentials.json を指す  # リポジトリ直下config配下を想定
    return Path(__file__).resolve().parents[3] / "config" / "credentials.json"  # 実在すればそのまま使用


# ==========================================================
# 関数定義

def is_true_only(v: Any) -> bool:  # ブールTrueまたは文字列"TRUE"のみを真として扱う
    if isinstance(v, bool):  # Pythonの真偽値そのものなら
        return v is True  # Trueのみ通す（Falseは不可）
    return str(v).strip() == "TRUE"  # 文字列の場合は大文字TRUEに厳密一致
    # 空行: ここから追記系のヘルパー定数（開始行やヘッダ行数）

# 追記: 追記開始行の判定に使う定数  # 追記位置を決めるための基準列とヘッダ行数
APPEND_BASE_COLUMN_INDEX: int = 1   # 最初に埋まり具合を見る列（A列=1）  # 追記開始行の計算に使用
HEADER_ROWS: int = 1                 # 見出し行数（データ開始は HEADER_ROWS+1 行目）  # 1行目がヘッダ前提
