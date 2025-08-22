# ==========================================================
# import（標準、プロジェクト内モジュール）  # ここから必要なモジュールを読み込む

import re  # 正規表現のパターン作成やマッチに使用
import logging  # ログ出力（デバッグ/警告/エラー）に使用
from datetime import datetime, date, datetime as dt_type, timedelta  # 日付/日時型と時間差計算に使用
from typing import Any  # 任意型を表す型ヒント
try:  # まずは本来の定数を読み込む
    from installer.src.const import date as C_DATE  # 日付解析に用いる正規表現やポリシーを集約した定数
except Exception:  # 読み込み失敗時はローカルの簡易定義で代替
    class _FallbackDateConst:  # フォールバック用の定数クラス（必要最小限の設定）
        RE_YMD_SLASH = r"^\d{4}/\d{1,2}/\d{1,2}$"  # 例: 2025/8/1 の形式にマッチ
        RE_YMD_DASH  = r"^\d{4}-\d{1,2}-\d{1,2}$"  # 例: 2025-08-01 の形式にマッチ
        RE_MD_HM     = r"(\d{1,2})/(\d{1,2}) (\d{1,2}):(\d{1,2})"  # 月/日 時:分 を抽出
        RE_JP_FULL   = r"(\d{1,2})月(\d{1,2})日.*?(\d{1,2})時(\d{1,2})分"  # 日本語の「○月○日○時○分」を抽出
        ENABLE_YMD_SLASH = True  # スラッシュ形式の解析を有効化
        ENABLE_YMD_DASH  = True  # ダッシュ形式の解析を有効化
        ENABLE_MD_HM     = True  # 月/日 時:分 形式の解析を有効化
        ENABLE_JP_FULL   = True  # 日本語形式の解析を有効化
        YEAR_POLICY = "current"  # 年の補完方針（current=常に今年）
        SMART_ROLLOVER_THRESHOLD_DAYS = 45  # ロールオーバー判定に使う閾値（日数）
    C_DATE = _FallbackDateConst()  # type: ignore  # 実運用の定数が無くても動くよう代入


# ==========================================================
# ログ設定  # このモジュールで使うロガーを用意する

logger: logging.Logger = logging.getLogger(__name__)  # モジュール名付きのロガー（上位設定を継承）


# ==========================================================
# 関数定義

def log_parse_success(kind: str, src: str, parsed: Any) -> None:  # 解析成功時の詳細ログを出す
    if logger.isEnabledFor(logging.DEBUG):  # デバッグレベルが有効な場合のみ冗長ログ
        logger.debug("終了日時パース（%s）: %s → %s", kind, src, parsed)  # どの形式で何をどう解釈したかを記録


# ==========================================================
# 関数定義

def log_parse_failure(kind: str, src: str, err: Exception, level: int = logging.WARNING) -> None:  # 解析失敗時のログ
    logger.log(level, "終了日時パース失敗（%s）: %s (%s: %s)", kind, src, type(err).__name__, err)  # 形式・元文字列・例外種別を出力
    # 空行: ここからクラス定義に切り替えるための区切り


# ==========================================================
# class定義

class DateConverter:  # 多様な入力（文字列/日付/日時）を date に揃える
    """任意の値を datetime.date に正規化（フォーマット/型差異を吸収）。"""  # クラスの責務を説明

    # ---- 正規表現（const から注入）----  # 解析で使うパターンを事前にコンパイル
    _RE_YMD_SLASH: re.Pattern[str] = re.compile(getattr(C_DATE, "RE_YMD_SLASH", r"^\d{4}/\d{1,2}/\d{1,2}$"))  # YYYY/MM/DD
    _RE_YMD_DASH:  re.Pattern[str] = re.compile(getattr(C_DATE, "RE_YMD_DASH",  r"^\d{4}-\d{1,2}-\d{1,2}$"))  # YYYY-MM-DD
    _RE_MD_HM:     re.Pattern[str] = re.compile(getattr(C_DATE, "RE_MD_HM",     r"(\d{1,2})/(\d{1,2}) (\d{1,2}):(\d{1,2})"))  # MM/DD HH:MM
    _RE_JP_FULL:   re.Pattern[str] = re.compile(getattr(C_DATE, "RE_JP_FULL",   r"(\d{1,2})月(\d{1,2})日.*?(\d{1,2})時(\d{1,2})分"))  # 日本語表記

    # ---- 有効/無効 ----  # どの形式の解析を有効にするかフラグで制御
    _EN_YMD_SLASH: bool = bool(getattr(C_DATE, "ENABLE_YMD_SLASH", True))  # スラッシュ形式を使うか
    _EN_YMD_DASH:  bool = bool(getattr(C_DATE, "ENABLE_YMD_DASH",  True))  # ダッシュ形式を使うか
    _EN_MD_HM:     bool = bool(getattr(C_DATE, "ENABLE_MD_HM",     True))  # MM/DD HH:MM を使うか
    _EN_JP_FULL:   bool = bool(getattr(C_DATE, "ENABLE_JP_FULL",   True))  # 日本語形式を使うか

    # ---- 年ポリシー ----  # 年の補完方法（今年固定/スマートロールオーバー等）
    _YEAR_POLICY: str = str(getattr(C_DATE, "YEAR_POLICY", "current")).lower()  # 年の解釈方針（小文字化して比較）
    _ROLLOVER_DAYS: int = int(getattr(C_DATE, "SMART_ROLLOVER_THRESHOLD_DAYS", 45))  # スマートロールオーバーの閾値


    # ==========================================================
    # コンストラクタ

    def __init__(self) -> None:  # 特に状態は持たないため処理なし
        pass  # 将来的な拡張に備えたプレースホルダ


    # ==========================================================
    # メソッド定義

    @staticmethod  # インスタンス化せずに利用可能
    def _to_date_if_datetime(value: Any) -> date | None:  # 値がdate/datetime系ならdateに変換して返す
        if isinstance(value, date) and not isinstance(value, dt_type):  # 既にdate（ただしdatetimeを除く）
            return value  # そのまま返す
        if isinstance(value, dt_type):  # datetimeなら
            return value.date()  # date部分に変換して返す
        if hasattr(value, "to_pydatetime"):  # pandas.Timestamp等の互換APIに対応
            try:  # 変換が失敗しても全体処理に影響しないようtry
                return value.to_pydatetime().date()  # pandas型→datetime→date
            except Exception:  # 失敗時は無視して後続へ
                pass  # 無視
        if hasattr(value, "date") and callable(getattr(value, "date")):  # 独自型でdate()を持つ場合
            try:  # 呼び出してdate型を取得できるか試す
                parsed_date = value.date()  # メソッド呼び出し
                if isinstance(parsed_date, date):  # 返り値がdate型か確認
                    return parsed_date  # 有効なら返す
            except Exception:  # 呼び出し失敗は無視
                pass  # 無視
        return None  # dateに寄せられない場合はNone


    # ==========================================================
    # メソッド定義

    @classmethod  # クラス変数（ポリシー）参照のためclassmethod
    def _decide_year(cls, month_num: int, day_num: int) -> int:  # 月日から補完する年を決める
        today_date = datetime.now().date()  # 今日の日付を基準にする
        base_year = today_date.year  # 今年の年を取得
        year_policy = cls._YEAR_POLICY  # 現在の年補完ポリシー
        if year_policy == "smart_rollover":  # スマートロールオーバー指定時
            try:  # 無効な月日でも例外で落ちないようにする
                candidate_date = date(base_year, month_num, day_num)  # 今年の該当月日を作る
                if candidate_date < (today_date - timedelta(days=cls._ROLLOVER_DAYS)):  # 閾値より十分過去なら
                    return base_year + 1  # 来年扱いにロールオーバー
            except Exception:  # 日付生成の失敗は今年扱いにフォールバック
                # 不正日付は上位で弾かれるのでここでは黙って今年扱い
                return base_year  # 今年を返す
        return base_year  # デフォルトは今年


    # ==========================================================
    # メソッド定義

    @staticmethod  # インスタンス不要で利用できる
    def convert(value: Any) -> date:  # 任意の値をdateに正規化して返す（失敗時は例外）
        # 1) 既に date/datetime 系なら早期 return  # まずは簡単に判定できるパスを処理
        parsed_date = DateConverter._to_date_if_datetime(value)  # 事前変換を試す
        if parsed_date is not None:  # 変換できた場合
            log_parse_success("既に日付/日時型", str(value), parsed_date)  # 成功ログ
            return parsed_date  # そのまま返す

        value_str = str(value).strip()  # 文字列として扱い、前後の空白を除去

        # 2) 形式ごとの判定（const の有効/無効に従う）  # 各形式を優先順位なしで順に試す

        if DateConverter._EN_YMD_SLASH and DateConverter._RE_YMD_SLASH.fullmatch(value_str):  # YYYY/MM/DDに完全一致か
            try:  # 解析を試行
                parsed_date = datetime.strptime(value_str, "%Y/%m/%d").date()  # パターンに沿ってパース
                log_parse_success("YYYY/MM/DD", value_str, parsed_date)  # 成功ログ
                return parsed_date  # 結果を返す
            except Exception as err:  # パース失敗
                log_parse_failure("YYYY/MM/DD", value_str, err, level=logging.ERROR)  # 詳細をエラーログ

        if DateConverter._EN_YMD_DASH and DateConverter._RE_YMD_DASH.fullmatch(value_str):  # YYYY-MM-DDに完全一致か
            try:  # 解析を試行
                parsed_date = datetime.strptime(value_str, "%Y-%m-%d").date()  # パターンに沿ってパース
                log_parse_success("YYYY-MM-DD", value_str, parsed_date)  # 成功ログ
                return parsed_date  # 結果を返す
            except Exception as err:  # パース失敗
                log_parse_failure("YYYY-MM-DD", value_str, err, level=logging.ERROR)  # エラーログ

        if DateConverter._EN_JP_FULL:  # 日本語形式の解析が有効なら試す
            jp_match = DateConverter._RE_JP_FULL.search(value_str)  # パターンにヒットする部分を検索
            if jp_match:  # 見つかった場合
                try:  # グループから月日時分を取得して日時を構築
                    month_num, day_num, hour_num, minute_num = map(int, jp_match.groups())  # 文字→数値へ
                    base_year = DateConverter._decide_year(month_num, day_num)  # 補完する年を決定
                    datetime_obj = datetime(base_year, month_num, day_num, hour_num, minute_num)  # datetime生成
                    log_parse_success("日本語", value_str, datetime_obj)  # 成功ログ
                    return datetime_obj.date()  # dateにして返す
                except Exception as err:  # 生成に失敗した場合
                    log_parse_failure("日本語", value_str, err, level=logging.ERROR)  # エラーログ

        if DateConverter._EN_MD_HM:  # MM/DD HH:MM 形式の解析が有効なら試す
            mdhm_match = DateConverter._RE_MD_HM.search(value_str)  # パターンにヒットする部分を検索
            if mdhm_match:  # 見つかった場合
                try:  # 月日と時分から日時を構成
                    month_num, day_num, hour_num, minute_num = map(int, mdhm_match.groups())  # 数値に変換
                    base_year = DateConverter._decide_year(month_num, day_num)  # 年を補完
                    datetime_obj = datetime(base_year, month_num, day_num, hour_num, minute_num)  # datetime生成
                    log_parse_success("MM/DD HH:MM", value_str, datetime_obj)  # 成功ログ
                    return datetime_obj.date()  # dateにして返す
                except Exception as err:  # 生成失敗
                    log_parse_failure("MM/DD HH:MM", value_str, err, level=logging.ERROR)  # エラーログ

        err = ValueError("フォーマット不一致")  # いずれの形式にも当てはまらない場合のエラー
        log_parse_failure("全形式", value_str, err, level=logging.ERROR)  # どの形式でも失敗した旨を記録
        raise ValueError(f"無効な終了日時フォーマット: {value_str}")  # 呼び出し側へ例外を送出
    