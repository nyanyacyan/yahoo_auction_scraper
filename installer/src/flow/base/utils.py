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





# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$%$$$$$$$$$$$$$$$$$$$
# import
import re                                  # 正規表現操作（複数フォーマットの日時文字列を抽出するのに利用）
import logging                              # ログ出力（進捗・障害解析・デバッグで重要）
from datetime import datetime, date, datetime as dt_type  # 日付・時刻操作および返り値の型定義

# ロガーのセットアップ（このモジュール内のログ出力用。呼び出し元でレベル等の設定が必要）
logger = logging.getLogger(__name__)
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

# 統一ログ関数（成功はDEBUG、失敗はWARNING/ERROR）
def log_parse_success(kind: str, src: str, parsed) -> None:
    """成功時ログ（DEBUG）"""
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("終了日時パース（%s）: %s → %s", kind, src, parsed)

def log_parse_failure(kind: str, src: str, err: Exception, level: int = logging.WARNING) -> None:
    """失敗時ログ（WARNING/ERROR）"""
    logger.log(level, "終了日時パース失敗（%s）: %s (%s: %s)", kind, src, type(err).__name__, err)

# **********************************************************************************
# class定義
class DateConverter:
    """
    日付/終了日時の文字列から「日付（datetime.date）」を取り出して返すユーティリティ。
    - スプレッドシートの値（YYYY/MM/DD, YYYY-MM-DD, date/datetime/Timestamp 等）
    - ヤフオク画面の終了日時（例: '06/27 22:13', '7月21日（月）22時7分 終了'）
    の両方に対応します。
    """

    # 事前コンパイルしておく正規表現
    _RE_YMD_SLASH = re.compile(r"^\d{4}/\d{1,2}/\d{1,2}$")     # 2025/06/27
    _RE_YMD_DASH  = re.compile(r"^\d{4}-\d{1,2}-\d{1,2}$")     # 2025-06-27
    _RE_MD_HM     = re.compile(r"(\d{1,2})/(\d{1,2}) (\d{1,2}):(\d{1,2})")  # 06/27 22:13
    _RE_JP_FULL   = re.compile(r"(\d{1,2})月(\d{1,2})日.*?(\d{1,2})時(\d{1,2})分")  # 7月21日（月）22時7分

    @staticmethod
    def _to_date_if_datetime(v) -> date | None:
        """datetimeならdateに、すでにdateならそのまま返す。該当しなければNone。"""
        if isinstance(v, date) and not isinstance(v, dt_type):
            return v
        if isinstance(v, dt_type):
            return v.date()
        # pandas.Timestamp 等に緩やか対応
        if hasattr(v, "to_pydatetime"):
            try:
                return v.to_pydatetime().date()
            except Exception:
                pass
        if hasattr(v, "date") and callable(getattr(v, "date")):
            try:
                d = v.date()
                if isinstance(d, date):
                    return d
            except Exception:
                pass
        return None

    # ------------------------------------------------------------------------------
    # 関数定義
    @staticmethod
    def convert(value) -> date:
        """
        値から datetime.date を返す統一変換メソッド。

        Args:
            value: 文字列 or date/datetime/Timestamp 等

        Returns:
            datetime.date

        Raises:
            ValueError: フォーマット不一致や変換失敗時
        """
        # すでに日付型・日時型ならそのまま処理
        d = DateConverter._to_date_if_datetime(value)
        if d is not None:
            log_parse_success("既に日付/日時型", str(value), d)
            return d

        s = str(value).strip()

        # ---------- 1) YYYY/MM/DD 形式 ----------
        if DateConverter._RE_YMD_SLASH.fullmatch(s):
            try:
                d = datetime.strptime(s, "%Y/%m/%d").date()
                log_parse_success("YYYY/MM/DD", s, d)
                return d
            except Exception as e:
                log_parse_failure("YYYY/MM/DD", s, e, level=logging.ERROR)

        # ---------- 2) YYYY-MM-DD 形式 ----------
        if DateConverter._RE_YMD_DASH.fullmatch(s):
            try:
                d = datetime.strptime(s, "%Y-%m-%d").date()
                log_parse_success("YYYY-MM-DD", s, d)
                return d
            except Exception as e:
                log_parse_failure("YYYY-MM-DD", s, e, level=logging.ERROR)

        # ---------- 3) 日本語表記: 7月21日（月）22時7分 終了 ----------
        m_jp = DateConverter._RE_JP_FULL.search(s)
        if m_jp:
            try:
                month, day, hour, minute = map(int, m_jp.groups())
                year = datetime.now().year  # 年が明示されないため、基本は当年扱い
                dt = datetime(year, month, day, hour, minute)
                log_parse_success("日本語", s, dt)
                return dt.date()
            except Exception as e:
                log_parse_failure("日本語", s, e, level=logging.ERROR)

        # ---------- 4) スラッシュ + 時刻: 06/27 22:13 ----------
        m_md = DateConverter._RE_MD_HM.search(s)
        if m_md:
            try:
                month, day, hour, minute = map(int, m_md.groups())
                year = datetime.now().year
                dt = datetime(year, month, day, hour, minute)
                log_parse_success("MM/DD HH:MM", s, dt)
                return dt.date()
            except Exception as e:
                log_parse_failure("MM/DD HH:MM", s, e, level=logging.ERROR)

        # すべてのパターンに当てはまらなかった
        err = ValueError("フォーマット不一致")
        log_parse_failure("全形式", s, err, level=logging.ERROR)
        raise ValueError(f"無効な終了日時フォーマット: {s}")