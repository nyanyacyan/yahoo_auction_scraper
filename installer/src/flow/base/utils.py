# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$%$$$$$$$$$$$$$$$$$$$
# import
import logging
from datetime import datetime, date

# ロガーを設定
logger = logging.getLogger(__name__)
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

# **********************************************************************************
# クラス定義: DateConverter
# ヤフオク終了日時（例: '06/27 22:13'）から年月日を抽出し、
# datetime.date 型で返すユーティリティクラス
# **********************************************************************************
# class定義
class DateConverter:
    """
    ヤフオク終了日時（例: '06/27 22:13'）から
    年月日を抽出し datetime.date 型で返すユーティリティクラス
    """

    # ------------------------------------------------------------------------------
    # メソッド定義: convert
    # 終了日時文字列を date 型に変換
    # ------------------------------------------------------------------------------
    # 関数定義
    @staticmethod
    def convert(end_time_str: str) -> date:
        """
        終了日時文字列から date 型を生成

        Args:
            end_time_str (str): ヤフオク終了日時（例: '06/27 22:13'）

        Returns:
            datetime.date: 年月日のみの date 型

        Raises:
            ValueError: フォーマット不正時
        """
        try:
            # 現在の年を取得（例: 2025）
            current_year = datetime.now().year

            # 入力文字列に現在の年を補完
            # '06/27 22:13' → '2025/06/27 22:13'
            datetime_str = f"{current_year}/{end_time_str}"

            # 補完した文字列を datetime に変換
            dt = datetime.strptime(datetime_str, "%Y/%m/%d %H:%M")

            # デバッグログに変換成功を記録
            logger.debug(f"変換成功: {dt.date()} (元: '{end_time_str}')")

            # 年月日のみ（date型）を返却
            return dt.date()
        except Exception as e:

            # エラー発生時はロギングして例外を再スロー
            logger.error(f"終了日時変換エラー: {end_time_str} → {e}")
            raise ValueError(f"無効な終了日時フォーマット: {end_time_str}") from e
# **********************************************************************************