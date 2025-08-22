# ==========================================================
# import（標準、プロジェクト内モジュール）  # ここから必要なモジュールを読み込む

from decimal import Decimal, ROUND_HALF_UP  # 高精度計算用のDecimal型と丸めモード定数を読み込む
import decimal as _decimal  # decimalモジュール別名（未使用だが既存互換のため残す）
import logging  # ログ出力に使う標準ライブラリ
from typing import Any, Optional  # 型ヒント（任意型と省略可能型）を使うためのインポート
try:  # 例外が出なければプロジェクト側の定数を採用
    # 例: installer/src/const/calc.py に以下の定数を用意すると上書きされます  # 定義例の説明（実際の読み込みは下行）
    # FEE_RATE = 0.10  # 手数料率（例）
    # TAX_EX_RATE = 0.10  # 税控除率（例、税込→税抜に相当する係数）
    # ROUNDING = ROUND_HALF_UP  # または "ROUND_HALF_UP" などの文字列でも可  # 丸めモード指定
    # LOG_LEVEL = logging.INFO  # 計算ログを出すレベル
    from installer.src.const import calc as C_CALC  # type: ignore  # プロジェクト側の定数モジュールを読み込む
except Exception:  # 読み込みに失敗した場合はこちらの既定値を使う


    # ==========================================================
    # class定義  # ChromeDriver生成を簡略化するラッパークラスを定義する

    class _FallbackCalcConst:  # フォールバック既定  # 外部定数が無い環境向け
        FEE_RATE = 0.10  # 手数料率のデフォルト（10%）
        TAX_EX_RATE = 0.10  # 税控除率のデフォルト（10%）
        ROUNDING = ROUND_HALF_UP  # 丸めモードのデフォルト（四捨五入）
        LOG_LEVEL = logging.DEBUG  # 既定のログ出力レベル（詳細に見る想定）
    C_CALC = _FallbackCalcConst()  # type: ignore  # フォールバック定数を実際に使う
    # 空行: ここからユーティリティ関数の定義


# ==========================================================
# ログ設定  # このモジュール専用のロガーを取得して以降の情報出力に用いる

logger: logging.Logger = logging.getLogger(__name__)  # このモジュール専用のロガーを取得（名前はファイルパス）


# ==========================================================
# 関数定義

def _to_rounding(mode: Any) -> str:  # 任意の丸め指定をDecimal.quantizeが受け取れる文字列へ正規化する
    """
    const の ROUNDING が:
    - 文字列（"ROUND_HALF_UP" など）
    - decimal モジュールの定数（ROUND_HALF_UP など）
    のどちらでも受付、quantize に渡せる値（文字列）へ正規化する。
    """  # 受け取り可能な形式と出力形式の方針を説明するdocstring
    if isinstance(mode, str):  # 既に文字列ならそのまま返す（未知値は呼び出し時にdecimal側で検証される）
        # 文字列 → decimal 定数存在チェック（無ければそのまま文字列を返す）  # 厳密な検証はここでは行わない
        return mode  # 文字列のまま返す
    # decimal の定数は実体が文字列なので、そのまま返す  # Decimal.quantizeに直接渡せる
    return str(mode)  # 定数（例: ROUND_HALF_UP）を文字列にして返す
    # 空行: ここから計算クラス本体


# ==========================================================
# class定義

class PriceCalculator:  # 1ct単価の計算を担当するクラス（手数料・税控除・丸めを一括管理）
    """1ct単価計算（ヤフオク手数料・税抜換算の2段控除に対応 / constで既定値を上書き可能）"""  # クラスの目的を要約

    fee_rate: Decimal  # 手数料率（0〜1の係数）をDecimalで保持
    tax_ex_rate: Decimal  # 税控除率（0〜1の係数）をDecimalで保持
    log_level: int  # 計算過程を出力するログレベル
    rounding: str  # Decimal.quantize に渡す丸めモード（"ROUND_HALF_UP" 等）


    # ==========================================================
    # コンストラクタ

    def __init__(  # 設定値を初期化。引数がNoneならconst側の既定を採用する
        self,
        fee_rate: Optional[float] = None,  # 手数料率（省略可）
        tax_ex_rate: Optional[float] = None,  # 税控除率（省略可）
        log_level: Optional[int] = None,  # ログレベル（省略可）
        rounding: Optional[Any] = None,  # 丸め指定（文字列 or decimal定数）（省略可）
    ) -> None:
        # const を優先的に使い、引数指定があればそれで上書き  # 利用側で柔軟に設定できる
        fee_rate_value = C_CALC.FEE_RATE if fee_rate is None else fee_rate  # 手数料率の決定
        tax_ex_rate_value = C_CALC.TAX_EX_RATE if tax_ex_rate is None else tax_ex_rate  # 税控除率の決定
        self.fee_rate = Decimal(str(fee_rate_value))  # 浮動小数の誤差回避のため文字列経由でDecimal化
        self.tax_ex_rate = Decimal(str(tax_ex_rate_value))  # 同上（Decimalで安定した計算）

        self.log_level = int(C_CALC.LOG_LEVEL if log_level is None else log_level)  # ログレベルの決定
        self.rounding = _to_rounding(C_CALC.ROUNDING if rounding is None else rounding)  # 丸めモードを正規化して保持


    # ==========================================================
    # メソッド定義

    def calculate_1ct_price(self, price: int, ct: float) -> int:  # 総価格とctから1ct単価（丸め後のint）を計算して返す
        try:  # エラーを捕捉し、内容をログ出力して再送出する
            if price is None or ct is None:  # 必須引数のチェック（Noneなら計算できない）
                raise ValueError("price/ct is None")  # 不正入力として例外

            price_decimal: Decimal = Decimal(price)  # 価格は整数想定のためそのままDecimal化
            carat_decimal: Decimal = Decimal(str(ct))  # ctは浮動小数のため文字列経由でDecimal化
            if carat_decimal <= 0:  # 0以下は割り算不可能かつ意味の無い入力
                raise ValueError(f"ct must be > 0, got {ct}")  # 不正ctとして例外

            # 中間値  # ここから計算式。読みやすさのため段階的に変数へ格納
            gross_price_per_carat: Decimal = price_decimal / carat_decimal  # まずは単純な(価格/ct)で原単価を出す
            fee_deduction_factor: Decimal = Decimal("1") - self.fee_rate  # 手数料控除係数（1 - 手数料率）
            tax_deduction_factor: Decimal = Decimal("1") - self.tax_ex_rate  # 税抜換算係数（1 - 税率相当）
            net_price_per_carat: Decimal = gross_price_per_carat * fee_deduction_factor * tax_deduction_factor  # 2段控除後の単価

            # 丸め（const の ROUNDING を反映）  # 指定の丸め規則で整数へ
            rounded_price: int = int(net_price_per_carat.quantize(Decimal("1"), rounding=self.rounding))  # 1の位へ量子化→int

            # 中間値＋式を1行で出力  # 計算過程をまとめてログに出す（レベルは設定値）
            logger.log(
                self.log_level,  # 出力レベル（INFO/DEBUGなど）
                "1ct計算: %(price)s ÷ %(ct)s = %(raw)s → ×%(fee)s ×%(tax)s = %(net)s → %(rounding)s = %(rounded)s",  # メッセージテンプレ
                {
                    "price": f"{price:,}",  # 価格（3桁区切り）
                    "ct": f"{ct}",  # ct表示
                    "raw": f"{gross_price_per_carat:,.2f}",  # 原単価（小数点2桁表示）
                    "fee": f"{fee_deduction_factor.normalize()}",  # 手数料係数
                    "tax": f"{tax_deduction_factor.normalize()}",  # 税控除係数
                    "net": f"{net_price_per_carat:,.2f}",  # 控除後単価
                    "rounding": self.rounding,  # 丸めルール名
                    "rounded": f"{rounded_price:,}",  # 丸め後の整数値
                },
            )  # ログ出力で計算の透明性を確保

            return rounded_price  # 最終結果（整数の1ct単価）を返す

        except Exception as err:  # どこかで例外が起きた場合
            logger.error(  # 入力値と設定を含めたエラーログを出す（原因追跡用）
                "1ct計算エラー: price=%s, ct=%s, fee=%.2f, tax_ex=%.2f, rounding=%s : %s",
                price, ct, float(self.fee_rate), float(self.tax_ex_rate), self.rounding, err
            )
            raise  # 例外は再送出して呼び出し側に判断を委ねる
