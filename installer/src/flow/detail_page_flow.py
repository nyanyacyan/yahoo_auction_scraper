# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$%$$$$$$$$$$$$$$$$$$$
# import
import logging  # ロギング用。エラーや進捗の可視化・運用監視に必須
from installer.src.flow.base.number_calculator import PriceCalculator  # 1カラット単価計算ユーティリティ
from installer.src.utils.text_utils import NumExtractor                # タイトルからカラット数を抽出するためのユーティリティ
from installer.src.flow.base.utils import DateConverter               # 終了日時文字列をdate型へ変換するためのユーティリティ

# ロガーのセットアップ（このモジュール用のロガー。上位でlevelなどの設定が必要）
logger = logging.getLogger(__name__)
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

# **********************************************************************************
# class定義
class DetailPageFlow:
    """
    Yahoo!オークション詳細ページの情報をまとめて抽出し、構造化データとして返却するフロークラス

    - Selenium WebDriverと各種抽出ユーティリティを内部に保持
    - 商品タイトル、価格、画像、カラット数、1ct単価、終了日などを一括で取得可能
    - スプレッドシート連携など、後段処理のための前処理にも適合
    """

    # ------------------------------------------------------------------------------
    # 関数定義
    def __init__(self, driver, selenium_util):
        """
        コンストラクタ
        :param driver: Selenium WebDriver インスタンス（ページ遷移等の実体）
        :param selenium_util: Seleniumのヘルパークラス（ページ要素取得等のラッパー）
        """
        self.driver = driver  # 実際のページ操作を担うWebDriver
        self.selenium_util = selenium_util  # 各種取得メソッドを持つユーティリティ
        self.price_calculator = PriceCalculator()  # 1カラット単価計算インスタンス
        self.num_extractor = NumExtractor()        # カラット数抽出インスタンス
        self.date_converter = DateConverter()      # 日付変換インスタンス

    # ------------------------------------------------------------------------------
    # 関数定義
    def extract_detail(self, url: str) -> dict:
        """
        指定URLの詳細ページから必要データを抽出し、辞書形式で返却
        :param url: 詳細ページのURL（例: "https://auctions.yahoo.co.jp/..."）
        :return: 商品データ辞書（date, title, price, ct, 1ct_price, image）
        """
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