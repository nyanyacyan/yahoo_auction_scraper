# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$%$$$$$$$$$$$$$$$$$$$
# import
import re
import logging
from datetime import datetime, date
# ロガーのセットアップ（エラーや進捗を出力するため）
logger = logging.getLogger(__name__)
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

# **********************************************************************************
# クラス定義: DateConverter
# ヤフオク終了日時（例: '06/27 22:13'）から年月日を抽出し、
# datetime.date 型で返すユーティリティクラス
# **********************************************************************************
# class定義
class DateConverter:

    # ------------------------------------------------------------------------------
    # メソッド定義: convert
    # 終了日時文字列を date 型に変換
    # ------------------------------------------------------------------------------
    # 関数定義
    @staticmethod
    def convert(date_str: str) -> date:
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
            # パターン1: 日本語（例: "7月15日（火）23時0分 終了"）
            m1 = re.search(r"(\d{1,2})月(\d{1,2})日.*?(\d{1,2})時(\d{1,2})分", date_str)
            if m1:
                month, day, hour, minute = map(int, m1.groups())
                year = datetime.now().year
                dt = datetime(year, month, day, hour, minute)
                logger.info(f"終了日時パース: {date_str} → {dt}")
                return dt.date()

            # パターン2: 数字スラッシュ形式（例: "06/27 22:13"）
            m2 = re.search(r"(\d{1,2})/(\d{1,2}) (\d{1,2}):(\d{1,2})", date_str)
            if m2:
                month, day, hour, minute = map(int, m2.groups())
                year = datetime.now().year
                dt = datetime(year, month, day, hour, minute)
                logger.info(f"終了日時パース: {date_str} → {dt}")
                return dt.date()

            # どちらもマッチしない場合
            logger.error(f"終了日時パース失敗: {date_str}")
            raise ValueError(f"終了日時パース失敗: {date_str}")

        except Exception as e:
            logger.error(f"終了日時変換エラー: {date_str} → {e}")
            raise ValueError(f"無効な終了日時フォーマット: {date_str}") from e
# **********************************************************************************



