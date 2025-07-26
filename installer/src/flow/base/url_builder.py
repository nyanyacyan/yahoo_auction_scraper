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
    def build_url(self, keyword: str) -> str:
        """
        1つの検索キーワードから、URLを生成して返す。

        Args:
            keyword (str): 検索ワード（日本語可）

        Returns:
            str: 完成した検索用URL

        Raises:
            Exception: URL生成失敗時にエラー内容をそのまま上位へ投げる
        """
        try:
            logger.info(f"URL生成開始：キーワード = {keyword}")
            # キーワードがstr型でなければ型エラー
            if not isinstance(keyword, str):
                raise TypeError(f"キーワードは文字列である必要があります（受信: {type(keyword)}）")
            
            encoded_kw = quote(keyword)  # URLで安全に扱えるようエンコード（例：空白→%20、日本語→%E3%80%82等）
            logger.debug(f"キーワードをURLエンコード済み：\n{encoded_kw}")

            url = self.URL_TEMPLATE.format(kw=encoded_kw)  # テンプレート文字列に埋め込む
            # logger.info(f"URL生成完了：{url}")
            # logger.info("URL生成完了")
            return url  # 正常時は完成した検索URLを返す
        
        except Exception as e:
            logger.error(f"URL生成に失敗しました（keyword: {keyword}）: {e}")
            raise  # 上位へ例外伝播

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
# **********************************************************************************