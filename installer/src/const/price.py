# ==========================================================
# import（標準、プロジェクト内モジュール）  # ここから必要なモジュールを読み込む

from typing import Final  # 定数としての意図を示す型ヒント（再代入防止の目安）
import os as _os  # 環境変数読み取り用に os を短縮名でインポート
import re as _re  # 正規表現モジュールを短縮名でインポート
    # 空行: 環境変数→float 変換の補助関数定義


# ==========================================================
# 関数定義

def _env_float(name: str, default: float) -> float:  # 文字列の環境変数を float に変換し、失敗時は既定値を返す
    v = _os.environ.get(name)  # 指定名の環境変数を取得（存在しない場合は None）
    if v is None or v.strip() == "":  # 未設定または空文字は既定値で返す
        return default  # ここで関数を終了
    try:
        return float(v)  # 数値に変換できればその値を返す
    except ValueError:
        return default  # 数値でなければ既定値にフォールバック
    # 空行: ここから定数定義（環境変数で上書き可能な値）

# 係数（環境変数で上書き可能）  # 手数料率/税相当率を 0.0〜1.0 の係数として扱う
FEE_RATE: Final[float] = _env_float("FEE_RATE", 0.9)  # FEE_RATE が未設定/不正なら 0.9 を使用
TAX_RATE: Final[float] = _env_float("TAX_RATE", 0.9)  # TAX_RATE が未設定/不正なら 0.9 を使用
# 空行: ct 抽出用の正規表現パターンを定義（大小文字無視）

# ct 抽出パターン（大文字小文字を無視）  # "1.23ct" や "ct 0.5" などの数値を取り出す想定
CT_REGEX_PATTERN: Final[str] = _os.environ.get(  # 文字列としてパターンを環境変数から取得（未設定なら既定）
    "CT_REGEX_PATTERN",  # 環境変数名
    r'(?:ct\s*([0-9.]{1,5})|([0-9.]{1,5})\s*ct)'  # 片側のグループに数値が入るよう設計
)  # ここまででパターン文字列の確定
CT_PATTERN: Final[_re.Pattern[str]] = _re.compile(CT_REGEX_PATTERN, _re.IGNORECASE)  # IGNORECASE でコンパイル
# 空行: ct の最小許容値を定義（検証時に使用）

# 許容最小 ct（0 以下は不正扱いにしたい場合は >0 を推奨）  # 抽出後のフィルタ条件に利用する想定
MIN_CT: Final[float] = _env_float("MIN_CT", 0.0)  # MIN_CT 未設定/不正時は 0.0（実運用では >0 を推奨）
