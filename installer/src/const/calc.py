# ==========================================================
# import（標準、プロジェクト内モジュール）  # ここから必要なモジュールを読み込む

from decimal import ROUND_HALF_UP   # Decimalの丸めモード定数（文字列指定でもOKな設計に合わせて利用）
import logging  # ログ出力のレベル指定に使う標準ライブラリ
    # 空行: ここから実際に計算で参照される定数群の宣言ブロック（プロジェクト全体からimport想定）

FEE_RATE = 0.10  # 手数料率（例: 10%）。計算時は (1 - FEE_RATE) で控除する
TAX_EX_RATE = 0.10  # 税抜換算の控除率（例: 消費税10%を外す → (1 - TAX_EX_RATE)）
ROUNDING = ROUND_HALF_UP   # 端数処理の既定（四捨五入）。文字列 "ROUND_HALF_UP" を渡しても動く設計
LOG_LEVEL = logging.INFO  # 中間計算を出す際のログレベル（INFO=通常、DEBUG=詳細表示）
