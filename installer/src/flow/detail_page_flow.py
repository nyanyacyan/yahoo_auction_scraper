# 簡潔に、どのような順序で動いているか出力して+1行プチ解説
# ==========================================================
# import（標準、プロジェクト内モジュール）

import logging
from installer.src.flow.base.number_calculator import PriceCalculator
from installer.src.utils.text_utils import NumExtractor
from installer.src.flow.base.utils import DateConverter


# ==========================================================
# ログ設定

logger = logging.getLogger(__name__)



# ==========================================================
# class


class DetailPageFlow:


    # ==========================================================
    # 関数
    def __init__(self, driver, selenium_util):

        self.driver = driver  # 実際のページ操作を担うWebDriver
        self.selenium_util = selenium_util  # 各種取得メソッドを持つユーティリティ
        self.price_calculator = PriceCalculator()  # 1カラット単価計算インスタンス
        self.num_extractor = NumExtractor()        # カラット数抽出インスタンス
        self.date_converter = DateConverter()      # 日付変換インスタンス


    # ==========================================================
    # 関数
    def extract_detail(self, url: str) -> dict:

        logger.info(f"詳細ページにアクセス: {url}")  # 開始ログ

        try:
            # 詳細ページへ移動（driver.getでページ遷移）
            self.driver.get(url)

            # 商品タイトルを取得（h1などの要素をラッパー経由で抽出）
            title = self.selenium_util.get_title()
            logger.debug(f"件名取得: {title}")

            # 商品価格を取得（価格要素からint型で取得）
            price = self.selenium_util.get_price()
            logger.debug(f"価格取得: {price}")

            # 商品画像URLを取得（1枚目・最大解像度優先などの工夫をselenium_util側で実装）
            image_url = self.selenium_util.get_image_url()
            logger.debug(f"画像URL取得: {image_url}")

            # 商品タイトルからカラット数を抽出（正規表現ベースでタイトルから数値を抜き出し）
            ct = self.num_extractor.extract_ct_value(title)
            logger.debug(f"カラット数抽出: {ct}")

            # 1カラット単価計算（落札価格÷カラット数→ヤフオク手数料・税控除も考慮）
            price_per_ct = self.price_calculator.calculate_price_per_carat(title, price)
            logger.debug(f"1カラット単価計算: {price_per_ct}")

            # 終了日（落札日）取得（終了日時の要素テキスト→date型に変換）
            end_date_str = self.selenium_util.get_detail_end_date()
            date = self.date_converter.convert(end_date_str)
            logger.debug(f"終了日取得: {date}")

            # スプレッドシート用の画像埋め込み用IMAGE関数（セル内で画像を表示するGoogle Sheets標準式）
            image_formula = f'=IMAGE("{image_url}", 4, 80, 80)'

            # 結果をまとめて辞書形式で返却
            result = {
                "date": f"'{date}",         # 文字列として日付を明示（'付きで日付変換を防止）
                "title": title,             # 商品タイトル
                "price": price,             # 落札価格
                "ct": ct,                   # カラット数
                "1ct_price": price_per_ct,  # 1ct単価
                "image": image_formula      # 画像セル用IMAGE式
            }

            logger.info(f"抽出結果: {result}")  # 成功ログ
            return result

        except Exception as e:
            # 例外発生時は詳細ログ（exc_infoでtracebackも出力）
            logger.error(f"詳細ページデータ抽出中にエラー: {e}", exc_info=True)
            raise  # 例外をそのまま呼び出し元に伝播







# ==============
# 実行の順序
# ==============
# 1. import各種モジュール
# → 標準（logging）とプロジェクト内の必要クラスを読み込む。

# 2. logger設定
# → このファイル専用のロガーを用意（出力レベルやフォーマットは上位設定に従う）。

# 3. DetailPageFlow クラス定義
# → 詳細ページから商品データを抽出する処理のまとまりを持つクラス。

# 4. __init__ 初期化
# → WebDriverやユーティリティクラスのインスタンスを受け取り、属性として保持。

# 5. extract_detail(url) 呼び出し開始
# → 指定URLの詳細ページにアクセスし、抽出作業を順に実施。