# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$%$$$$$$$$$$$$$$$$$$$
# import
import re                                  # 正規表現操作（複数フォーマットの日時文字列を抽出するのに利用）
import logging                             # ログ出力（進捗・障害解析・デバッグで重要）
from datetime import datetime, date         # 日付・時刻操作および返り値の型定義

# ロガーのセットアップ（このモジュール内のログ出力用。呼び出し元でレベル等の設定が必要）
logger = logging.getLogger(__name__)
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

# **********************************************************************************
# class定義
class DateConverter:

    # ------------------------------------------------------------------------------
    # 関数定義
    @staticmethod
    def convert(date_str: str) -> date:
        """
        ヤフオク終了日時文字列から日付（datetime.date型）を抽出して返す

        Args:
            date_str (str): 終了日時の文字列（例: '06/27 22:13'や'7月15日（火）23時0分 終了'）

        Returns:
            datetime.date: 年月日だけ（時刻情報は捨てる）

        Raises:
            ValueError: フォーマットに合致しなかった場合や変換失敗時
        """
        try:
            # パターン1: 日本語表記（例: "7月15日（火）23時0分 終了"など）
            m1 = re.search(r"(\d{1,2})月(\d{1,2})日.*?(\d{1,2})時(\d{1,2})分", date_str)
            if m1:
                # マッチした場合はグループ（1=月, 2=日, 3=時, 4=分）を抽出
                month, day, hour, minute = map(int, m1.groups())
                year = datetime.now().year          # 年は今年で固定（未来日対応不要ならこれでOK）
                dt = datetime(year, month, day, hour, minute)  # 日時オブジェクト生成
                logger.info(f"終了日時パース: {date_str} → {dt}")  # 変換結果をログ出力
                return dt.date()                    # 年月日部分だけ返す

            # パターン2: スラッシュ表記（例: "06/27 22:13"など）
            m2 = re.search(r"(\d{1,2})/(\d{1,2}) (\d{1,2}):(\d{1,2})", date_str)
            if m2:
                month, day, hour, minute = map(int, m2.groups())
                year = datetime.now().year
                dt = datetime(year, month, day, hour, minute)
                logger.info(f"終了日時パース: {date_str} → {dt}")
                return dt.date()

            # 上記どちらのパターンにも合致しなかった場合（不正なフォーマット）
            logger.error(f"終了日時パース失敗: {date_str}")
            raise ValueError(f"終了日時パース失敗: {date_str}")

        except Exception as e:
            # 何らかの例外（数値変換失敗・不正日付・型違い等）もログ出力し、詳細付きで再スロー
            logger.error(f"終了日時変換エラー: {date_str} → {e}")
            raise ValueError(f"無効な終了日時フォーマット: {date_str}") from e
# **********************************************************************************