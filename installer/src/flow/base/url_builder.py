# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$%$$$$$$$$$$$$$$$$$$$
# import
import logging
from urllib.parse import quote
from typing import List, Union
import pandas as pd

# ロガー取得（本来はアプリの初期化部で構成するが、ここでは最小構成）
logger = logging.getLogger(__name__)
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

# **********************************************************************************
# class定義
class UrlBuilder:
    """
    Yahoo!オークションの落札済み検索URLを動的に生成するクラス。
    """
    BASE_URL = "https://auctions.yahoo.co.jp/closedsearch/closedsearch"
    URL_TEMPLATE = BASE_URL + "?p={kw}&va={kw}&b=1&n=50"

    # ------------------------------------------------------------------------------
    # 関数定義
    def __init__(self):
        pass
        logger.info("UrlBuilderインスタンスを初期化しました。")

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
            if not isinstance(keyword, str):
                raise TypeError(f"キーワードは文字列である必要があります（受信: {type(keyword)}）")
            
            encoded_kw = quote(keyword)
            logger.debug(f"キーワードをURLエンコード済み：\n{encoded_kw}")

            url = self.URL_TEMPLATE.format(kw=encoded_kw)
            # logger.info(f"URL生成完了：{url}")
            # logger.info("URL生成完了")
            return url
        
        except Exception as e:
            logger.error(f"URL生成に失敗しました（keyword: {keyword}）: {e}")
            raise

    # ------------------------------------------------------------------------------
    # 関数定義
    def build_urls_from_dataframe(self, df: pd.DataFrame, keyword_column: str = "keyword") -> List[str]:
        """
        DataFrameからキーワード列を抽出し、URLリストを生成する。
        """
        try:
            logger.info(f"DataFrameから一括でURL生成処理を開始：レコード数 = {len(df)}")
        
            # keyword列が無い場合は、search_1～search_5を連結してkeyword列を自動生成
            if keyword_column not in df.columns:
                logger.warning(f"指定したキーワード列（{keyword_column}）がDataFrameにありません。search_1～search_5を連結してkeyword列を自動生成します。")
                search_cols = [col for col in df.columns if col.startswith("search_")]
                if not search_cols:
                    raise ValueError("search_1～search_5のようなカラムが見つかりません。キーワード情報が取得できません。")
                # 空欄は空文字にし、スペースで連結
                df[keyword_column] = df[search_cols].fillna('').agg(' '.join, axis=1).str.strip()

            # 空欄行は除外
            keywords = df[keyword_column].dropna().astype(str)
            keywords = keywords[keywords != ""]

            logger.debug(f"キーワード抽出完了: {keywords.tolist()}")

            urls = []
            for kw in keywords:
                url = self.build_url(kw)
                urls.append(url)
                logger.debug(f"URL追加済み: {url}")
        
            logger.info(f"全URL生成完了: 件数={len(urls)}")
            return urls
    
        except Exception as e:
            logger.error(f"DataFrameからのURL一括生成に失敗: {e}")
            raise





    # # ------------------------------------------------------------------------------
    # # 関数定義
    # def build_urls_from_list(self, keywords: List[str]) -> List[str]:
    #     """
    #     キーワードリストから一括でURLを生成する（DataFrameを使わない場合）。
    #     Args:
    #         keywords (List[str]): 検索ワードのリスト
    #     Returns:
    #         List[str]: URLリスト
    #     Raises:
    #         Exception: エラー時
    #     """
    #     try:
    #         logger.info(f"キーワードリストからURL生成処理を開始: 件数={len(keywords)}")
    #         urls = [self.build_url(kw) for kw in keywords]
    #         logger.info(f"全URL生成完了: 件数={len(urls)}")
    #         return urls
    #     except Exception as e:
    #         logger.error(f"リストからのURL生成に失敗: {e}")
    #         raise
    # # ------------------------------------------------------------------------------
