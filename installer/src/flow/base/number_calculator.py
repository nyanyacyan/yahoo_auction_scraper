# ==========================================================
# import（標準、プロジェクト内モジュール）  # 以降で使うモジュール群を読み込む

import logging  # ログ出力用（情報/警告/エラーの記録に使う）
from typing import Optional, Pattern  # Optionalは「省略可」、Patternは正規表現パターン型のための型ヒント
from installer.src.const import price as C_PRICE  # ★ 料率・正規表現・下限ctなどの既定値をまとめた定数を参照
    # 空行: ロガー設定セクションへの切り替え


# ==========================================================
# ログ設定  # このモジュール専用のロガーを取得し、以降のログ出力で利用

logger = logging.getLogger(__name__)  # モジュール名付きロガー（ハンドラ/レベルは上位側で設定想定）
# 空行: クラス定義セクションへ移るための区切り


# ==========================================================
# class定義

class PriceCalculator:  # 価格とタイトルから1ct単価を算出する責務を持つクラス
    """
    役割:
        タイトル文字列からカラット数(ct)を抽出し、(価格/ct) に控除率を掛けて 1ct 単価を算出する。

    設定:
        - 料率や正規表現は installer.src.const.price の定数を既定値として使用。
        - 環境変数で上書き可能（FEE_RATE / TAX_RATE / CT_REGEX_PATTERN / MIN_CT）。
    """
        # 空行: docstringでクラスの概要を説明。以下で初期化やメソッドを定義


    # ==========================================================
    # コンストラクタ

    def __init__(
        self,  # インスタンス生成時に呼ばれる初期化処理
        *,
        fee_rate: Optional[float] = None,  # 手数料控除率（未指定なら定数の既定値を使用）
        tax_rate: Optional[float] = None,  # 税抜換算率（未指定なら定数の既定値を使用）
        pattern: Optional[Pattern[str]] = None,  # ct抽出に使う正規表現（未指定なら既定パターン）
    ) -> None:
        # None の時は const の既定を使う  # 明示指定が無ければC_PRICEの値を採用するポリシー
        self.fee_rate: float = float(C_PRICE.FEE_RATE if fee_rate is None else fee_rate)  # 手数料率をfloatで保持
        self.tax_rate: float = float(C_PRICE.TAX_RATE if tax_rate is None else tax_rate)  # 税率をfloatで保持
        self.ct_pattern: Pattern[str] = pattern if pattern is not None else C_PRICE.CT_PATTERN  # ct抽出用の正規表現
        self.min_ct: float = float(C_PRICE.MIN_CT)  # ctの下限（0や極小値を弾くしきい値）


    # ==========================================================
    # メソッド定義

    def _extract_carat(self, title: str) -> float:  # タイトルからct数値を取り出す内部メソッド
        """
        タイトルから ct を抽出して返す。失敗時は ValueError。
        """
        match_obj = self.ct_pattern.search(title or "")  # 正規表現でct候補を検索（None対策で空文字を許容）
        if not match_obj:  # マッチしない＝ct記載が見つからない場合
            logger.error("タイトルからカラット数が抽出できません: %r", title)  # 原因追跡用にタイトルを記録
            raise ValueError("カラット数抽出エラー")  # 呼び出し側に不正を通知

        carat_str = match_obj.group(1) or match_obj.group(2)  # キャプチャのどちらか（小数/整数など）を取り出す
        try:
            carat_value = float(carat_str)  # 文字列を数値に変換（小数を想定）
            if carat_value <= self.min_ct:  # 0または閾値以下は不正値として扱う
                # 0 もしくはしきい値以下は不正  # 極端に小さいctはノイズ/誤抽出の可能性が高い
                raise ValueError(f"不正なct値（{carat_value} <= {self.min_ct}）")  # 詳細付きで例外化
            return carat_value  # 妥当なctを返す
        except Exception as e:  # 変換失敗やその他例外をまとめて捕捉
            logger.error("カラット数の変換に失敗: '%s' エラー: %s", carat_str, e)  # 失敗値と例外を記録
            raise ValueError("カラット数変換エラー")  # 呼び出し側へ統一的なエラーを投げ直す


    # ==========================================================
    # メソッド定義

    def _calculate_price_per_carat(self, title: str, price: int) -> int:  # 1ct単価を算出して整数で返す
        """
        (price / ct) * fee_rate * tax_rate を四捨五入して int で返す。
        """
        try:
            carat_value = self._extract_carat(title)  # まずタイトルからctを抽出（ここで検証も済む）
            price_per_carat_raw = price / carat_value  # 素の1ct単価 = 価格÷ct（小数）
            price_per_carat_adjusted = price_per_carat_raw * self.fee_rate * self.tax_rate  # 手数料/税率で調整
            price_per_carat_int = int(round(price_per_carat_adjusted))  # 四捨五入して整数化（スプレッド用途に合わせる）

            if price_per_carat_int <= 0:  # 調整後に0以下は異常（入力か設定の不備を疑う）
                logger.error(
                    "計算結果が不正: title=%r price=%r ct=%r result=%r",
                    title, price, carat_value, price_per_carat_int
                )  # 異常時は入力と結果をすべて記録
                raise ValueError("算出単価が不正です")  # 不正値として明示的に失敗させる

            return price_per_carat_int  # 妥当な整数単価を返す
        except Exception as e:  # 抽出/計算いずれの段階の例外も包含して扱う
            logger.error("単価計算処理で例外発生: title=%r price=%r error=%s", title, price, e)  # 失敗の概要を記録
            raise  # ここでは包み直さず再送出（上位でハンドリング可能にする）


    # ==========================================================
    # メソッド定義

    @classmethod  # インスタンスを作らずに呼べるクラスメソッドとして提供
    def extract_carat(cls, title: str) -> float:  # 旧API：タイトルからctのみ取得
        return cls()._extract_carat(title)  # 既定設定のインスタンスを作り内部実装に委譲


    # ==========================================================
    # メソッド定義

    @classmethod  # 同様にクラスメソッドで提供
    def calculate_price_per_carat(  # 旧API：引数で料率を上書き可能な単価計算窓口
        cls,
        title: str,  # 商品タイトル（ctの表記が含まれる想定）
        price: int,  # 落札価格などの整数金額
        fee_rate: Optional[float] = None,  # 呼び出しごとに手数料率を上書き可能
        tax_rate: Optional[float] = None,  # 呼び出しごとに税率を上書き可能
    ) -> int:
        calculator_instance = cls(fee_rate=fee_rate, tax_rate=tax_rate)  # 上書き値を反映した計算器を生成
        return calculator_instance._calculate_price_per_carat(title=title, price=price)  # 内部実装へ委譲し結果を返す
