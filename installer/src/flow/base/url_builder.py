# ==========================================================
# import（標準、プロジェクト内モジュール）  # ここから必要なモジュールを読み込む

import logging  # ログ出力のための標準ライブラリ
from typing import List  # 型ヒント用。リストの要素型指定などで可読性が上がる
import pandas as pd  # 表形式データを扱うためのライブラリ（DataFrame）
from urllib.parse import urlencode, quote, quote_plus  # URLクエリ組み立てとエンコード関数
try:  # まずは本来の定数モジュールを読み込む
    from installer.src.const import url as C_URL  # ベースURLやパラメータ名などの定数群
except Exception:  # 読み込みに失敗した場合のフォールバック定義
    class _FallbackURL:  # 代替の定数コンテナ（最小限の値で安全に動かす）
        BASE_URL = "https://auctions.yahoo.co.jp/closedsearch/closedsearch"  # 既定の検索ベースURL
        PARAM_P = "p"  # 検索語パラメータ名（p）
        PARAM_VA = "va"  # 検索語の別名パラメータ（va）
        PARAM_BEGIN = "b"  # 先頭位置パラメータ（何件目から）
        PARAM_NUM = "n"  # 1ページあたり件数のパラメータ
        DEFAULT_BEGIN = 1  # beginの既定値（1始まり）
        DEFAULT_PER_PAGE = 100  # 1ページの既定件数
        MAX_PER_PAGE = 100  # 1ページの最大件数（上限ガード）
        MIN_PER_PAGE = 1  # 1ページの最小件数（下限ガード）
        ENCODER = "quote_plus"  # キーワードのエンコード方式（スペースを+に）
        KEYWORD_COLUMN = "keyword"  # DataFrameでキーワードが入る列名
        SEARCH_PREFIX = "search_"  # 複数列を連結する際の列名プレフィックス
        SEARCH_COL_COUNT = 5  # 連結対象列の最大数（search_1..search_5）
    C_URL = _FallbackURL()  # type: ignore  # 実運用の定数が無くても動くよう代替を代入
    # 空行: import/定数準備とログ設定の区切り（可読性のため）


# ==========================================================
# ログ設定  # このモジュールで使うロガーを取得（レベル/ハンドラは上位で設定想定）

logger: logging.Logger = logging.getLogger(__name__)  # モジュール名に紐づくロガーを取得
# 空行: ここからクラス定義に切り替えるための区切り


# ==========================================================
# class定義

class UrlBuilder:  # 検索パラメータからYahoo!オークションの検索URLを生成する責務を持つ
    """
    Yahoo!オークションの検索URLを動的に作る。
    - ベースURLやパラメータ名、件数制限などは const/url.py で集中管理
    - const が無い環境でもフォールバックで動作
    """
        # 空行: docstringはクラスの目的を説明（実行には影響しない）


    # ==========================================================
    # コンストラクタ

    def __init__(self) -> None:  # インスタンス初期化。特別な状態は持たない
        logger.debug("UrlBuilder initialized (const/url.py loaded)")  # 初期化完了をデバッグログに残す


    # ==========================================================
    # メソッド定義

    def _clamp_per_page(self, per_page_count: int | None) -> int:  # 件数をMIN/MAXの範囲に丸める
        if per_page_count is None:  # 未指定なら既定値を用いる
            per_page_count = int(getattr(C_URL, "DEFAULT_PER_PAGE", 100))  # 定数が無ければ100にフォールバック
        per_page_count = int(per_page_count)  # 数値化しておく（文字列入力への保険）
        per_page_count = max(int(getattr(C_URL, "MIN_PER_PAGE", 1)), per_page_count)  # 下限を適用
        per_page_count = min(int(getattr(C_URL, "MAX_PER_PAGE", 100)), per_page_count)  # 上限を適用
        return per_page_count  # 調整後の件数を返す


    # ==========================================================
    # メソッド定義

    def _sanitize_begin(self, begin_index: int | None) -> int:  # 先頭位置（bパラメータ）を1以上に整える
        if begin_index is None:  # 未指定時は既定値
            return int(getattr(C_URL, "DEFAULT_BEGIN", 1))  # 既定の開始位置（1）
        begin_index = int(begin_index)  # 数値化
        return begin_index if begin_index >= 1 else 1  # 1未満は1に引き上げ


    # ==========================================================
    # メソッド定義

    def _quote_via(self):  # 使用するエンコード関数（quote or quote_plus）を定数から選ぶ
        encoder = str(getattr(C_URL, "ENCODER", "quote_plus")).lower()  # エンコーダ名を取得し小文字化
        return quote_plus if encoder == "quote_plus" else quote  # 指定がquote_plusなら+、それ以外は%20等のquote


    # ==========================================================
    # メソッド定義

    def build_url(self, keyword: str, per_page: int | None = None, begin: int | None = None) -> str:  # 単一キーワードでURL生成
        """
        指定キーワードで closedsearch の検索URLを生成。
        - per_page: 件数（MIN/MAX を const で制御）
        - begin   : 先頭位置（b=）
        """
        base_url = str(getattr(C_URL, "BASE_URL", "https://auctions.yahoo.co.jp/closedsearch/closedsearch"))  # ベースURL取得
        per_page_count = self._clamp_per_page(per_page)  # 件数を範囲内に丸める
        begin_index = self._sanitize_begin(begin)  # 先頭位置を1以上に補正
        quote_func = self._quote_via()  # キーワードのエンコード関数を選択

        query_params = {  # クエリパラメータを辞書で組み立てる
            getattr(C_URL, "PARAM_P", "p"): keyword,  # p= キーワード
            getattr(C_URL, "PARAM_VA", "va"): keyword,  # va= キーワード（別名パラメータ）
            getattr(C_URL, "PARAM_BEGIN", "b"): begin_index,  # b= 先頭位置
            getattr(C_URL, "PARAM_NUM", "n"): per_page_count,  # n= 1ページ件数
        }
        # urlencode 側で quote_via を指定し、二重エンコードを避ける  # スペースの扱い等を統一
        query_string = urlencode(query_params, doseq=True, quote_via=quote_func)  # 指定エンコーダでクエリ文字列化
        built_url = f"{base_url}?{query_string}"  # ベースURLと連結して最終URLに
        logger.debug(f"build_url: kw='{keyword}', n={per_page_count}, b={begin_index} -> {built_url}")  # 生成内容を記録
        return built_url  # 完成したURLを返す


    # ==========================================================
    # メソッド定義

    def build_urls_from_dataframe(self, df: pd.DataFrame, keyword_column: str | None = None) -> List[str]:  # 複数行からURLを作成
        """
        DataFrame から一括でURLを作る。
        - keyword_column が無ければ search_1..search_5 を連結して作成（数は const で制御）
        """
        if df is None or df.empty:  # 入力が空なら何もせず終了
            logger.info("DataFrameが空のためURL生成なし")  # 生成件数0をログ
            return []  # 空リストを返す

        keyword_col_name = keyword_column or getattr(C_URL, "KEYWORD_COLUMN", "keyword")  # 使用するキーワード列名を決定
        if keyword_col_name not in df.columns:  # 指定列が無ければ複数列の連結を試みる
            search_col_prefix = getattr(C_URL, "SEARCH_PREFIX", "search_")  # 連結対象の列プレフィックス
            search_col_count = int(getattr(C_URL, "SEARCH_COL_COUNT", 5))  # 最大列数（search_1..N）
            search_col_names = [  # 実在する search_i 列だけを抽出
                f"{search_col_prefix}{i}" for i in range(1, search_col_count + 1) if f"{search_col_prefix}{i}" in df.columns
            ]
            if not search_col_names:  # どちらの形式の列も無い場合はエラー
                raise ValueError(
                    f"'{keyword_col_name}' 列も {search_col_prefix}1..{search_col_prefix}{search_col_count} も見つかりません。"
                )
            df = df.copy()  # 元のDataFrameを壊さないようコピーして加工
            df[keyword_col_name] = (  # search_i 列を連結してキーワード列を生成
                df[search_col_names]
                .fillna("")  # 欠損は空文字に
                .agg(" ".join, axis=1)  # 行方向に結合（スペース区切り）
                .str.replace(r"\s+", " ", regex=True)  # 連続空白を1つに圧縮
                .str.strip()  # 先頭末尾の空白を除去
            )

        keyword_series = df[keyword_col_name].dropna().astype(str)  # NaNを除去し文字列化
        keyword_series = keyword_series[keyword_series.str.strip() != ""]  # 空文字行を除外
        url_list: List[str] = [self.build_url(kw) for kw in keyword_series]  # 各キーワードからURLを生成
        logger.info(f"URL生成完了: {len(url_list)} 件")  # 生成された件数を情報ログ
        return url_list  # URLのリストを返す
