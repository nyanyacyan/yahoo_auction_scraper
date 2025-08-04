# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$%$$$$$$$$$$$$$$$$$$$
# import
import re                # 正規表現操作（カラット数抽出に使用）
import logging           # ロギング用（デバッグや障害時の詳細出力に必須）
# ロガーの取得（エラーや情報を記録するため。呼び出し元でlevelを設定）
logger = logging.getLogger(__name__)
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

# **********************************************************************************
# class定義
class PriceCalculator:
    """
    ヤフオク商品データからカラット単価（円/ct）を算出するクラス。

    ・落札価格とタイトルから1カラット単価を計算  
    ・ヤフオク手数料（-10%）と税抜換算（-10%）の2回控除後の値を返却  
    ・異常時はエラーログ出力&raise  
    """

    # 商品タイトル中の「ct 0.508」または「0.508ct」どちらの表記も抽出できる正規表現パターン
    CT_PATTERN = re.compile(r'(?:ct\s*([0-9.]{1,5})|([0-9.]{1,5})\s*ct)')  # 例: "ct 0.508" または "0.508ct"

    # ------------------------------------------------------------------------------
    # 関数定義
    @classmethod
    def extract_carat(cls, title: str) -> float:
        """
        商品タイトルからカラット数（float）を抽出する。
        :param title: 商品タイトル（例："天然ダイヤ 0.508ct F VS2"）
        :return: カラット数（float）
        """
        # タイトルから正規表現でカラット数にマッチする部分を探す
        match = cls.CT_PATTERN.search(title)
        if not match:
            # マッチしなかった場合はエラーログを出して例外を発生
            logger.error(f"タイトルからカラット数が抽出できません: {title}")
            raise ValueError("カラット数抽出エラー")

        # 正規表現のグループ1またはグループ2から値を取得（どちらかに数値が入る。どちらもNoneなら抽出失敗）
        value = match.group(1) or match.group(2)
        try:
            # 取得した値（str型）をfloat型に変換
            carat = float(value)
            if carat <= 0:
                # 0以下の場合も不正なのでエラー
                raise ValueError
            return carat
        except Exception as e:
            # 数値変換に失敗した場合もエラーログ＆例外発生
            logger.error(f"カラット数の変換に失敗: '{value}', エラー: {e}")
            raise ValueError("カラット数変換エラー")

    # ------------------------------------------------------------------------------
    # 関数定義
    @classmethod
    def calculate_price_per_carat(
        cls, title: str,        # 商品タイトル（例："天然ダイヤ 0.508ct F VS2"）
        price: int,             # 落札価格（円、整数）
        fee_rate: float = 0.9,  # ヤフオク手数料控除率（デフォルト0.9＝10%控除）
        tax_rate: float = 0.9   # 税抜換算控除率（デフォルト0.9＝10%控除）
    ) -> int:
        """
        タイトル・価格から1カラット単価（控除後、整数）を算出
        :param title: 商品タイトル
        :param price: 落札価格（円, int）
        :param fee_rate: ヤフオク手数料控除率（例：0.9, 10%控除したい場合）
        :param tax_rate: 税抜換算控除率（例：0.9, 10%控除したい場合）
        :return: 控除後1ct単価（円, int）
        """
        try:
            # タイトルからカラット数（小数）を抽出（例: 0.508など）
            carat = cls.extract_carat(title)

            # 1カラットあたりの落札価格を計算（手数料・税控除前）
            raw_price_per_carat = price / carat  # 例: 51700円 / 0.508ct → 1ctあたり

            # ヤフオク手数料（fee_rate）と税抜換算（tax_rate）を順に掛ける
            # 例）0.9 * 0.9 ＝ 2回10%控除（実質19%控除）
            adjusted_price = raw_price_per_carat * fee_rate * tax_rate

            # 最終的に四捨五入し、整数で返却（小数点以下は四捨五入）
            price_per_carat = int(round(adjusted_price))

            # 計算結果が0以下は異常なのでエラーを出す
            if price_per_carat <= 0:
                logger.error(
                    f"計算結果が不正: title={title}, price={price}, carat={carat}, result={price_per_carat}"
                )
                raise ValueError("算出単価が不正です")
            
            # 正常時は計算結果（1ct単価）を返す
            return price_per_carat
        except Exception as e:
            # エラー発生時は詳細をログ出力し、例外を投げ直す
            logger.error(
                f"単価計算処理で例外発生: title={title}, price={price}, エラー: {e}"
            )
            raise