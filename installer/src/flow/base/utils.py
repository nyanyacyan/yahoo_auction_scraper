# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$%$$$$$$$$$$$$$$$$$$$
# import
import re                                  # 正規表現操作（複数フォーマットの日時文字列を抽出）
import logging                             # ログ出力用
from datetime import datetime, date       # 日付・時刻操作

# ロガーセットアップ（このモジュール用）
logger = logging.getLogger(__name__)
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

# **********************************************************************************
# class定義
class DateConverter:
    """
    ヤフオク終了日時文字列から日付（datetime.date型）を抽出して返すユーティリティクラス。

    対応フォーマット例：
    - "7月15日（火）23時0分 終了"
    - "06/27 22:13"
    """

    @staticmethod
    def convert(date_str: str, base_year: int = None) -> date:
        if not date_str or not isinstance(date_str, str):
            logger.error(f"終了日時入力が無効です: {date_str!r}")
            raise ValueError(f"無効な終了日時フォーマット: {date_str}")

        try:
            year_now = base_year if base_year is not None else datetime.now().year

            # yyyy/mm/dd
            m0 = re.search(r"(\d{4})/(\d{1,2})/(\d{1,2})", date_str)
            if m0:
                year, month, day = map(int, m0.groups())
                dt = datetime(year, month, day)
                logger.info(f"終了日時パース成功（yyyy/mm/dd）: {date_str} → {dt}")
                return dt.date()

            # 日本語表記
            m1 = re.search(r"(\d{1,2})月(\d{1,2})日.*?(\d{1,2})時(\d{1,2})分", date_str)
            if m1:
                month, day, hour, minute = map(int, m1.groups())
                dt = datetime(year_now, month, day, hour, minute)
                # 年跨ぎ判定（例：12月の次に1月は翌年扱い）
                if dt < datetime.now():
                    dt = dt.replace(year=year_now + 1)
                logger.info(f"終了日時パース成功（日本語）: {date_str} → {dt}")
                return dt.date()

            # mm/dd hh:mm
            m2 = re.search(r"(\d{1,2})/(\d{1,2}) (\d{1,2}):(\d{1,2})", date_str)
            if m2:
                month, day, hour, minute = map(int, m2.groups())
                dt = datetime(year_now, month, day, hour, minute)
                if dt < datetime.now():
                    dt = dt.replace(year=year_now + 1)
                logger.info(f"終了日時パース成功（スラッシュ）: {date_str} → {dt}")
                return dt.date()

            logger.error(f"終了日時パース失敗（フォーマット不一致）: {date_str}")
            raise ValueError(f"終了日時パース失敗: {date_str}")

        except Exception as e:
            logger.error(f"終了日時変換エラー: 入力={date_str} → {e}", exc_info=True)
            raise ValueError(f"無効な終了日時フォーマット: {date_str}") from e













# # $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$%$$$$$$$$$$$$$$$$$$$
# # import
# import re                                  # 正規表現操作（複数フォーマットの日時文字列を抽出するのに利用）
# import logging                             # ログ出力（進捗・障害解析・デバッグで重要）
# from datetime import datetime, date         # 日付・時刻操作および返り値の型定義

# # ロガーのセットアップ（このモジュール内のログ出力用。呼び出し元でレベル等の設定が必要）
# logger = logging.getLogger(__name__)
# # $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

# # **********************************************************************************
# # class定義
# class DateConverter:

#     # ------------------------------------------------------------------------------
#     # 関数定義
#     @staticmethod
#     def convert(date_str: str) -> date:
#         """
#         ヤフオク終了日時文字列から日付（datetime.date型）を抽出して返す

#         Args:
#             date_str (str): 終了日時の文字列（例: '06/27 22:13'や'7月15日（火）23時0分 終了'）

#         Returns:
#             datetime.date: 年月日だけ（時刻情報は捨てる）

#         Raises:
#             ValueError: フォーマットに合致しなかった場合や変換失敗時
#         """
#         try:
#             # パターン1: 日本語表記（例: "7月15日（火）23時0分 終了"など）
#             m1 = re.search(r"(\d{1,2})月(\d{1,2})日.*?(\d{1,2})時(\d{1,2})分", date_str)
#             if m1:
#                 # マッチした場合はグループ（1=月, 2=日, 3=時, 4=分）を抽出
#                 month, day, hour, minute = map(int, m1.groups())
#                 year = datetime.now().year          # 年は今年で固定（未来日対応不要ならこれでOK）
#                 dt = datetime(year, month, day, hour, minute)  # 日時オブジェクト生成
#                 logger.info(f"終了日時パース: {date_str} → {dt}")  # 変換結果をログ出力
#                 return dt.date()                    # 年月日部分だけ返す

#             # パターン2: スラッシュ表記（例: "06/27 22:13"など）
#             m2 = re.search(r"(\d{1,2})/(\d{1,2}) (\d{1,2}):(\d{1,2})", date_str)
#             if m2:
#                 month, day, hour, minute = map(int, m2.groups())
#                 year = datetime.now().year
#                 dt = datetime(year, month, day, hour, minute)
#                 logger.info(f"終了日時パース: {date_str} → {dt}")
#                 return dt.date()

#             # 上記どちらのパターンにも合致しなかった場合（不正なフォーマット）
#             logger.error(f"終了日時パース失敗: {date_str}")
#             raise ValueError(f"終了日時パース失敗: {date_str}")

#         except Exception as e:
#             # 何らかの例外（数値変換失敗・不正日付・型違い等）もログ出力し、詳細付きで再スロー
#             logger.error(f"終了日時変換エラー: {date_str} → {e}")
#             raise ValueError(f"無効な終了日時フォーマット: {date_str}") from e
# # **********************************************************************************