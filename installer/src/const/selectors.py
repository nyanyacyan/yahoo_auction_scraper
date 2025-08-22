# ==========================================================
# import（標準、プロジェクト内モジュール）  # ここから必要なモジュールを読み込む

from typing import Final  # 定数を示すための型ヒント。代入後に変更しない意図を明示する
from typing import Final, Tuple, List  # タプル/リストの型注釈に使う（セレクタの集合を表すため）
    # 空行: 一覧/詳細ページのセレクタをクラスにグルーピングして整理する


# ==========================================================
# class定義

class YJ_LISTING:  # 一覧（検索結果）ページ向けのセレクタ定義をまとめるクラス
    END_TIME_CSS: Final[str]  = ".Product__time"  # 終了時刻テキストのCSSセレクタ
    TITLE_LINK_CSS: Final[str] = "a.Product__titleLink"  # 商品タイトルリンクのCSSセレクタ


# ==========================================================
# class定義

class YJ_DETAIL:  # 詳細ページ向けのセレクタ定義をまとめるクラス
    # 必要に応じて増やす  # 将来的に要素が増えた場合はここへ追加する
    PRICE_CSS: Final[str]      = ".Price__value, .ProductDetail__price"  # 価格の候補CSS（複数サイト版対応）
    MAIN_IMAGE_XPATH: Final[str] = "//img[@id='mainImg' or contains(@class,'ProductImage')]"  # メイン画像のXPath（id/classで判定）
    TITLE_XPATH: Final[str]    = "//title"  # <title>要素からタイトルを取得（安定していればこれで十分）
# 空行: 以下は個別の抽出処理で使う候補セレクタのリスト定義

# タイトル取得（詳細ページ）  # 取得が不安定なため、複数候補を順に試す
TITLE_SELECTORS: Final[List[Tuple[str, str]]] = [  # ("種類", "セレクタ文字列") の並び
    ("css", "h1.gv-u-fontSize16--_aSkEz8L_OSLLKFaubKB"),  # 現在のUIでよく使われるh1クラス
    # フォールバック候補（必要に応じて追記）  # 上が見つからない場合の予備
    ("css", "h1"),  # 最低限のフォールバックとして素のh1
]

# 価格取得（詳細ページ）  # 価格もDOM変化しやすいため複数候補で冗長性を持たせる
PRICE_SELECTORS: Final[List[Tuple[str, str]]] = [  # CSSセレクタの候補を順に試行
    ("css", "span.sc-1f0603b0-2.kxUAXU"),  # 現行の見た目クラス（変更されやすい）
    # フォールバック候補  # 旧/別レイアウト用
    ("css", "span.Price__value"),  # 価格値の汎用クラス
]

# 価格テキストから除去する文字列  # 数値化前に取り除くトークン（桁区切りや通貨単位）
PRICE_STRIP_TOKENS: Final[List[str]] = [",", "円"]  # 例: "51,700円" → "51700" にする

# 終了日時（一覧ページ）  # 一覧で終了日を拾うための候補セレクタ
AUCTION_END_DATE_SELECTORS: Final[List[Tuple[str, str]]] = [  # 時刻表示の場所が複数ある前提で網羅
    ("css", ".Product__time"),  # 代表的な位置
    ("css", ".Product__closedTime"),  # 別名クラス
    ("css", "li.Product__item .Product__time"),  # リストアイテム内の表記
]

# 商品URL（一覧ページ）  # 一覧から詳細ページへのリンクを拾う候補セレクタ
AUCTION_URL_SELECTORS: Final[List[Tuple[str, str]]] = [  # 正しい商品リンクに到達するための候補群
    ("css", "a.Product__titleLink"),  # 代表的なタイトルリンク
    ("css", "a.Product__title"),  # 別名クラス
    ("css", "li.Product__item a[href*='auction']"),  # hrefに"auction"を含むリンクを広く拾う
]

# 「次へ」ページャ  # ページング用のnextボタン候補（ラベル/属性/テキストで多面的に検出）
NEXT_BUTTON_LOCATORS: Final[List[Tuple[str, str]]] = [  # 次ページ遷移のためのボタン/リンク検出
    ("css", "a.Pager__link[data-cl_link='next']"),  # data属性でnext指定
    ("css", "a[aria-label='次へ']"),  # アクセシビリティ用ラベル
    ("css", "a[rel='next']"),  # rel属性での次ページ指定
    ("xpath", "//a[contains(@class,'Pager__link') and (@data-cl-params or @href) and (contains(.,'次') or contains(.,'次の'))]"),  # クラスと文言の併用
    ("xpath", "//a[normalize-space()='次へ' or normalize-space()='次の50件']"),  # 正確なテキスト一致
]

# 「落札相場/過去の落札」ボタン  # 一覧ページから過去の落札（相場）へ切替えるためのUI
PAST_AUCTION_BUTTON_LOCATORS: Final[List[Tuple[str, str]]] = [  # ボタン/リンクの候補セレクタ
    ("css", ".Auction__pastAuctionBtn"),  # 代表CSS
    ("xpath", "//button[contains(., '落札相場') or contains(., '過去の落札')]"),  # ボタンの文言で検出
    ("xpath", "//a[contains(., '落札相場') or contains(., '過去の落札')]"),  # リンクの文言で検出
]

# 詳細ページ：終了日テキスト（候補のスパン）  # 終了日時が書かれた要素候補（主にスパン）
DETAIL_END_DATE_SPANS: Final[List[Tuple[str, str]]] = [  # ("種類","セレクタ") のリスト
    ("css", "span.gv-u-fontSize12--s5WnvVgDScOXPWU7Mgqd.gv-u-colorTextGray--OzMlIYwM3n8ZKUl0z2ES"),  # 現行の小さめグレー文字
]
DETAIL_END_DATE_KEYWORDS: Final[List[str]] = ["終了", "時"]  # テキスト判定のキーワード（「終了」「時」などを含むか）

# 画像候補（詳細ページ）  # 画像のsrcを複数候補から検出。大サイズ優先の戦略を取る
IMAGE_XPATH_CANDIDATES: Final[List[dict]] = [  # 候補のラベル/xpath/小サイズフラグを持つ辞書のリスト
    # 大サイズ優先（1200x900）  # 最も画質が良いパターン
    {"label": "1200x900", "xpath": '//img[contains(@src, "i-img1200x900")]', "is_fallback_small": False},  # 1200x900を含む画像
    # CDN(auc-pctr / images.auctions)の一般的なパス  # 高解像度の可能性が高いCDN
    {"label": "auc-pctr CDN", "xpath": '//img[contains(@src, "auc-pctr.c.yimg.jp") and contains(@src, "/i/")]', "is_fallback_small": False},  # CDN配下の大画像
    # 広いyimgドメイン（小さい可能性あり）  # 最後のフォールバックとしての広い条件
    {"label": "fallback small", "xpath": '//img[contains(@src, "auctions.c.yimg.jp")]', "is_fallback_small": True},  # 小さめ画像の可能性
]

# 画像の「大きめURL」判定に使うヒント  # URLに含まれるサイズを示すトークン群
LARGE_IMAGE_HINTS: Final[List[str]] = ["i-img1200x900", "=w=1200", "&w=1200", "1200", "900"]  # 「大」判定に使う目安文字列

# collect_image_src_candidates 用（src 候補の XPATH 群）  # 画像srcを広く集めるためのXPath候補
IMAGE_CANDIDATE_XPATHS: Final[List[str]] = [  # 収集時に順番に試すXPath
    '//img[contains(@src,"i-img1200x900")]',  # 明確に1200x900を示す
    '//img[contains(@src,"i-img") and (contains(@src,"1200") or contains(@src,"900"))]',  # i-imgかつサイズ指標あり
    '//img[contains(@src,"auc-pctr.c.yimg.jp") or contains(@src,"images.auctions.yahoo.co.jp/image")]',  # CDN/公式画像ドメイン
    '//img[contains(@src,"auctions.c.yimg.jp")]',  # 広いyimgドメイン（フォールバック）
]  # リスト終端
