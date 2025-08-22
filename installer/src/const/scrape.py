# ==========================================================
# import（標準、プロジェクト内モジュール）  # ここから必要なモジュールを読み込む

from typing import Final, Tuple  # 型ヒント用の型をインポート。Finalは「定数意図」、Tupleはタプル型注釈に使う

# 一覧ページ  # ここから一覧（検索結果）ページに関する定数定義
PAST_AUCTION_BUTTON_CSS: Final[str] = ".Auction__pastAuctionBtn"  # 過去オークション（落札相場）ボタンのCSSセレクタ

# 空行: ここから「結果が0件」の判定に使うページ内文言をまとめる
NO_RESULT_TEXTS: Final[Tuple[str, ...]] = (  # ページ本文のメッセージで結果なしを検出するための候補タプル
    "条件に一致する商品は見つかりませんでした",  # パターン1: 一般的な未検出メッセージ
    "該当する商品はありません",               # パターン2: 別表現
    "該当するオークションはありません",       # パターン3: オークション向け表現
)  # タプル終端
# 空行: ここから「結果が0件」の判定に使うDOM要素（CSSセレクタ）をまとめる

NO_RESULT_SELECTORS: Final[Tuple[str, ...]] = (  # 特定要素の有無で0件と判断するためのセレクタ候補
    ".Module__noResult",  # 共通モジュールの「結果なし」表現
    ".NoResult",          # 別名クラス
    "#NoResult",          # ID指定の「結果なし」要素
    ".Search__noItems",   # 検索ページ特有の「アイテム無し」表現
)  # タプル終端
# 空行: ここから待機時間（秒）の既定値。WebDriverWait等のタイムアウトに利用

# 待機秒（明示的待機の既定）  # 画面操作や遷移の安定化を待つ基準時間
WAIT_PAST_BTN_CLICK_SEC: Final[int] = 5  # 過去オークションボタンのクリック完了待ち秒数
WAIT_DOC_READY_SEC:      Final[int] = 2  # document.readyStateがcompleteになるまでの待ち秒数
WAIT_NEXT_PAGE_SEC:      Final[int] = 3  # 次ページ遷移後の読み込み安定までの待ち秒数
