# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$%$$$$$$$$$$$$$$$$$$$
# import
import re
import logging
logger = logging.getLogger(__name__)
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

# **********************************************************************************
# class定義
class NumExtractor:
    @staticmethod

    # ------------------------------------------------------------------------------
    # 関数定義
    def extract_ct_value(text: str) -> float:
        """
        商品タイトルなどの文字列から「ct」直前の数値（小数を含む）を抽出し、float型で返す。

        Args:
            text (str): 対象文字列

        Returns:
            float: 抽出した数値

        Raises:
            ValueError: 数値が抽出できなかった場合
        """
        try:
            # 「ct」直前の数値（例: 0.52ct, 1.08 ct, 【0.4ct】）を抽出する正規表現パターン
            pattern = r'([0-9]+(?:\.[0-9]+)?)\s*ct'
            # パターンにマッチするすべての数値をリストで取得（大文字・小文字区別なし）
            matches = re.findall(pattern, text, re.IGNORECASE)
            # 1つも見つからなかった場合は例外を発生させる
            if not matches:
                raise ValueError(f"'ct'直前の数値が見つかりません: {text}")

            # 最初に見つかった値をfloatに変換して返す
            ct_value = float(matches[-1])
            return ct_value

        except Exception as e:
            logger.error(f"ct数値抽出エラー: {e} | text='{text}'")
            raise



