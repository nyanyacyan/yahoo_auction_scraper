# ==========================================================
# import（標準、プロジェクト内モジュール）  # ここから必要なモジュールを読み込む

from typing import Final
import os as _os
    # 空行: ここから環境変数を安全に数値へ変換する補助関数を定義


# ==========================================================
# 関数定義

def _env_float(name: str, default: float) -> float:
    v = _os.environ.get(name)  # 環境変数を取得（存在しなければ None）
    if v is None or v.strip() == "":  # 未設定や空文字なら既定値を使用
        return default
    try:
        return float(v)  # 数値文字列を float に変換
    except ValueError:
        return default  # 不正な値は安全側で既定値にフォールバック


# ==========================================================
# 関数定義

def _env_int(name: str, default: int) -> int:
    v = _os.environ.get(name)  # 環境変数を取得
    if v is None or v.strip() == "":  # 未設定・空なら既定値
        return default
    try:
        return int(v)  # 数値文字列を int に変換
    except ValueError:
        return default  # 変換できない場合は既定値
    # 空行: ここから実際のタイムアウト定数を定義

# ページロード完了（document.readyState 完了など）を待つ上限秒
PAGE_COMPLETE_TIMEOUT: Final[int] = _env_int("PAGE_COMPLETE_TIMEOUT", 10)

# find_one / find_many で要素探索にかける待機秒（単一/複数）
FIND_TIMEOUT: Final[int] = _env_int("FIND_TIMEOUT", 10)
MULTI_FIND_TIMEOUT: Final[int] = _env_int("MULTI_FIND_TIMEOUT", 10)

# ページャ操作やボタンのクリック応答待機の目安秒数
NEXT_TIMEOUT: Final[int] = _env_int("NEXT_TIMEOUT", 8)
PAST_AUCTION_TIMEOUT: Final[int] = _env_int("PAST_AUCTION_TIMEOUT", 6)

# 画像の読み込み・探索のための短い待機秒
IMAGE_WAIT_SECONDS: Final[int] = _env_int("IMAGE_WAIT_SECONDS", 2)
# 空行: 実行ごとに少し待つランダムスリープの範囲（人間らしい間隔を再現）

# ランダムスリープの最小/最大秒（MIN ≤ sleep ≤ MAX になるように使用側で乱数化）
RANDOM_SLEEP_MIN_SECONDS: Final[float] = _env_float("RANDOM_SLEEP_MIN_SECONDS", 0.5)
RANDOM_SLEEP_MAX_SECONDS: Final[float] = _env_float("RANDOM_SLEEP_MAX_SECONDS", 1.5)
# 空行: ナビゲーション直後、DOM が安定するまでの微小待機（クリック後のチラつき対策）

# クリックやページ遷移後に行う短い安定化待機の下限/上限秒
POST_NAV_MIN_SECONDS: Final[float] = _env_float("POST_NAV_MIN_SECONDS", 0.6)
POST_NAV_MAX_SECONDS: Final[float] = _env_float("POST_NAV_MAX_SECONDS", 1.2)
