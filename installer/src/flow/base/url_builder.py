# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$%$$$$$$$$$$$$$$$$$$$
# import
import logging                   # ログ出力用。進捗・エラー管理に必須
from urllib.parse import quote   # URLパラメータを安全にエンコードするための標準関数
from typing import List, Union   # 型ヒント用（静的解析・IDE支援向け）
import pandas as pd              # DataFrameデータ処理用

# ロガー取得（アプリの初期化部でlevel等を設定して使う。ここではクラス用に最小構成）
logger = logging.getLogger(__name__)
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

# **********************************************************************************
# class定義
class UrlBuilder:
    """
    Yahoo!オークションの落札済み検索URLを動的に生成するクラス。
    - 1キーワード単位、もしくはDataFrame（複数キーワード一括）対応
    - URL生成失敗時はエラーログ＆例外スロー
    """
    BASE_URL = "https://auctions.yahoo.co.jp/closedsearch/closedsearch"   # 検索ページのベースURL
    URL_TEMPLATE = BASE_URL + "?p={kw}&va={kw}&b=1&n=50"                  # パラメータ埋め込み用テンプレ

    # ------------------------------------------------------------------------------
    # 関数定義
    def __init__(self):
        pass  # 初期化は何もせず（logger.infoは実行されない位置なので意味なし）
        logger.info("UrlBuilderインスタンスを初期化しました。")  # ←この行は実際には実行されません

    # ------------------------------------------------------------------------------
    # 関数定義
    # UrlBuilder クラス内のメソッド差し替え
    def build_url(self, keyword: str, per_page: int = 100) -> str:
        """
        検索URLを生成。1ページの件数 n を可変に（デフォルト100）。
        ヤフオク側の上限があるため、100を指定しても50になる可能性はありますが、
        ここでは"最大を要求"する方針です。
        """
        from urllib.parse import quote_plus

        q = quote_plus(keyword)
        # ベースURLは既存仕様に合わせてください
        base = "https://auctions.yahoo.co.jp/closedsearch/closedsearch"
        # b=1: 先頭、 n=per_page: 1ページ件数
        n = int(per_page) if per_page and int(per_page) > 0 else 50
        return f"{base}?p={q}&va={q}&b=1&n={n}"

    # ------------------------------------------------------------------------------
    # 関数定義
    def build_urls_from_dataframe(self, df: pd.DataFrame, keyword_column: str = "keyword") -> List[str]:
        """
        DataFrameからキーワード列を抽出し、URLリストを生成する。
        - 指定列がなければ、search_1～search_5の連結列を自動生成
        - 欠損行・空行は除外
        - 生成したURLのリストを返却

        Args:
            df (pd.DataFrame): キーワード情報を含むDataFrame
            keyword_column (str): キーワードが格納された列名（既定値は"keyword"）

        Returns:
            List[str]: 検索URLのリスト

        Raises:
            Exception: DataFrame不正時や生成失敗時はエラー詳細ごと上位へ投げる
        """
        try:
            logger.info(f"DataFrameから一括でURL生成処理を開始：レコード数 = {len(df)}")
        
            # 指定キーワード列がなければ、search_1～search_5の各カラムをスペース連結してkeyword列を生成
            if keyword_column not in df.columns:
                logger.warning(f"指定したキーワード列（{keyword_column}）がDataFrameにありません。search_1～search_5を連結してkeyword列を自動生成します。")
                search_cols = [col for col in df.columns if col.startswith("search_")]
                if not search_cols:
                    raise ValueError("search_1～search_5のようなカラムが見つかりません。キーワード情報が取得できません。")
                # 欠損値(NaN)は空文字にし、行ごとにスペース区切りで連結
                df[keyword_column] = df[search_cols].fillna('').agg(' '.join, axis=1).str.strip()

            # 欠損または空白行は除外（.dropnaでNaN除外、==""で空文字も除外）
            keywords = df[keyword_column].dropna().astype(str)
            keywords = keywords[keywords != ""]

            logger.debug(f"キーワード抽出完了: {keywords.tolist()}")

            urls = []
            for kw in keywords:  # 有効キーワードごとに個別URL生成
                url = self.build_url(kw)
                urls.append(url)
                logger.debug(f"URL追加済み: {url}")
        
            logger.info(f"全URL生成完了: 件数={len(urls)}")
            return urls  # URLリスト返却
    
        except Exception as e:
            logger.error(f"DataFrameからのURL一括生成に失敗: {e}")
            raise