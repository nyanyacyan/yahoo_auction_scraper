# ==========================================================
# import（標準、プロジェクト内モジュール）  # ここから必要なモジュールを読み込む

from typing import Final  # 定数（変更しない値）を型として表すためのヒント

# Yahoo!オークション検索URLのページング  # ここからページング関連の基本パラメータ
PER_PAGE: Final[int] = 100  # 1ページで取得する件数の既定値
PARAM_PAGE_OFFSET: Final[str] = "b"   # 何件目から取得を開始するかを示すクエリキー（例: b=101）
PARAM_PER_PAGE:   Final[str] = "n"   # 1ページあたりの件数を示すクエリキー（例: n=100）

# Yahoo!オークション検索URL用の定数を一元管理  # 以下は検索URL構築に使う定数群のまとめ

# ベースURL  # 検索の土台となるエンドポイント
BASE_URL: str = "https://auctions.yahoo.co.jp/closedsearch/closedsearch"  # 過去の落札検索ページのベースURL

# クエリパラメータ名  # URLに付与する各種クエリキーの定義
PARAM_P: str = "p"  # 検索キーワード（例: p=ダイヤ）
PARAM_VA: str = "va"  # 補助的な検索語（バリエーション）に使われるパラメータ
PARAM_BEGIN: str = "b"  # 取得開始オフセット（上の PARAM_PAGE_OFFSET と同義）
PARAM_NUM: str = "n"  # 1ページ件数（上の PARAM_PER_PAGE と同義）

# 既定値  # クエリに指定が無い場合に用いるデフォルト
DEFAULT_BEGIN: int = 1  # 先頭から取得開始（1始まり）
DEFAULT_PER_PAGE: int = 100  # 1ページで最大100件を要求

# 制約  # 値の上限・下限を明示（API/サイト仕様のガードに使用）
MAX_PER_PAGE: int = 100  # ヤフオク側の許容最大件数
MIN_PER_PAGE: int = 1  # 最低でも1件

# エンコード方針: "quote_plus" or "quote"  # キーワードのURLエンコード方式
ENCODER: str = "quote_plus"  # スペースは %20 でなく + にする方式を採用

# DataFrame→キーワード生成時の既定列名など  # データ表から検索語を作るときの列名規約
KEYWORD_COLUMN: str = "keyword"   # 既に keyword 列がある場合はそれを使う
SEARCH_PREFIX: str = "search_"    # 無ければ search_1..search_5 を連結してキーワードを作る
SEARCH_COL_COUNT: int = 5  # 連結対象の search_* 列数（1〜5列を想定）
