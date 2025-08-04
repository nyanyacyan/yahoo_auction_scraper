# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$%$$$$$$$$$$$$$$$$$$$
# import
# ★ 各種標準ライブラリ・外部ライブラリをインポート（動作に必須）
import time                # スリープ・タイミング調整用
import re                  # 正規表現（未使用だがテンプレとして用意されている）
import logging             # ログ出力用（開発・運用・障害解析で重要）
import random              # ランダム値生成（人間らしい挙動のため）
import time                # 再インポート（上記と重複だがバグではない。整理する場合は片方だけでOK）

# Selenium関連。Webブラウザ自動操作に使う
from selenium.webdriver.remote.webdriver import WebDriver      # Chromeなどのドライバ型ヒント用
from selenium.webdriver.remote.webelement import WebElement    # 要素型ヒント用
from selenium.common.exceptions import (
    NoSuchElementException,  # 要素が存在しない場合の例外
    TimeoutException,        # タイムアウト時の例外
    WebDriverException,      # Selenium全般の異常を表す例外
)
from selenium.webdriver.support.ui import WebDriverWait        # 明示的な待機用
from selenium.webdriver.support import expected_conditions as EC # 出現条件の指定
from selenium.webdriver.common.by import By                    # 検索方法の定数

# ロガーのセットアップ（エラーや進捗を出力するため。呼び出し元でlevel設定推奨）
logger = logging.getLogger(__name__)
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
<<<<<<< HEAD
=======

# ------------------------------------------------------------------------------
# 関数定義
def random_sleep(min_seconds=0.5, max_seconds=1.5):
    """人間らしさを出すためのランダムスリープ

    :param min_seconds: 最小スリープ秒（float）
    :param max_seconds: 最大スリープ秒（float）
    :return: なし（time.sleepを呼ぶだけ）
    """
    sleep_time = random.uniform(min_seconds, max_seconds)  # min〜max間の小数で乱数生成
    logger.debug(f"ランダムスリープ: {sleep_time:.2f}秒")  # デバッグ用にスリープ秒をログ出力
    time.sleep(sleep_time)  # 指定秒数スリープ。ボット対策＆サーバー負荷分散

>>>>>>> feature/#10-spreadsheet_writer
# **********************************************************************************
# class定義
# Seleniumによるスクレイピング操作をラップするクラス（全ブラウザ共通の操作を集約）
class Selenium:

    # ------------------------------------------------------------------------------
    # 関数定義
    # コンストラクタ（chromeインスタンスを受け取る）
    def __init__(self, chrome: WebDriver):
        """
        Seleniumユーティリティクラスの初期化
        :param chrome: 事前に生成済みのwebdriver.Chromeインスタンス
        """
        self.chrome = chrome  # クラス全体で使うためインスタンス変数へ保存

    # ========================
    # 基底メソッド（全画面で共通利用できる操作）
    # ========================

    # ------------------------------------------------------------------------------
    # 関数定義
    # ページ内から単一要素を取得
    def find_one(self, by, value, timeout=10) -> WebElement:
        """
        Seleniumで指定セレクタの要素を1つだけ取得
        :param by: 検索方法（By.ID, By.CSS_SELECTORなど）
        :param value: セレクタ値（CSS, XPATH, ID, ...）
        :param timeout: 待機タイムアウト（秒）
        :return: WebElement（取得できなければ例外）
        """
        try:
            # ページの読み込み完了まで待機（JSやAjaxで非同期にロードされるケース対応）
            self.wait_for_page_complete()

            # 指定された検索方法・値の要素が出現するまで最大timeout秒間待つ
            element = WebDriverWait(self.chrome, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            if not element:  # 万が一取得できなかった場合
                logger.error(f"要素が見つかりません: by={by}, value={value}")
                raise ValueError(f"要素が見つかりません: by={by}, value={value}")
            return element
        except Exception as e:
            # あらゆる取得失敗時、例外をログに出して呼び出し元に再送出
            logger.error(f"要素取得失敗: by={by}, value={value}, error={e}")
            raise

    # ------------------------------------------------------------------------------
    # 関数定義
    # ページ内から複数要素を取得
    def find_many(self, by, value, timeout=10) -> list:
        """
        指定セレクタの要素を複数取得。最低1件出現するまで最大timeout秒待つ
        :param by: 検索方法（By.ID, By.CSS_SELECTORなど）
        :param value: セレクタ値
        :param timeout: タイムアウト秒
        :return: List[WebElement]
        """
        try:
<<<<<<< HEAD
            # ページの読み込み完了まで待機
            self.wait_for_page_complete()
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            # 最低1つ要素が出現するまで待つ
            WebDriverWait(self.chrome, timeout).until( EC.presence_of_element_located((by, value)) )

            # 複数の要素をリストで取得
            elements = self.chrome.find_elements(by, value)
=======
            self.wait_for_page_complete()  # ページ全体のロード待ち
            WebDriverWait(self.chrome, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            elements = self.chrome.find_elements(by, value)  # 全一致要素をリスト取得
>>>>>>> feature/#10-spreadsheet_writer
            if not elements:
                logger.error(f"要素リストが空: by={by}, value={value}")
                raise ValueError(f"要素リストが空: by={by}, value={value}")
            return elements
        except Exception as e:
            logger.error(f"複数要素取得失敗: by={by}, value={value}, error={e}")
            raise

    # ------------------------------------------------------------------------------
    # 関数定義
    # 任意の要素をクリック
    def click(self, by, value, timeout=10):
        """
        指定セレクタで要素を取得し、その要素をクリック。人間ぽくランダムスリープ付き
        :param by: 検索方法
        :param value: セレクタ値
        :param timeout: タイムアウト秒
        """
        try:
            element = self.find_one(by, value, timeout)  # 指定要素を取得
            element.click()                              # クリック操作
            logger.debug(f"クリック成功: by={by}, value={value}")
            random_sleep()  # クリック後に一瞬止める（不自然な連打を防ぐ）
        except Exception as e:
            logger.error(f"クリック失敗: by={by}, value={value}, error={e}")
            raise

    # ------------------------------------------------------------------------------
    # 関数定義
    # ページのロード（読み込み）が終わるまで待機
    def wait_for_page_complete(self, timeout=10):
        """
        JavaScript上のreadyStateが"complete"になるまで待つ（画面描画＆DOM構築終了を判定）
        :param timeout: タイムアウト秒
        :return: なし（例外発生時はraise）
        """
        try:
            WebDriverWait(self.chrome, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            logger.debug("ページロード完了")
        except TimeoutException:
            logger.error("ページのロードがタイムアウトしました")
            raise
        except Exception as e:
            logger.error(f"wait_for_page_complete失敗: error={e}")
            raise

    # ------------------------------------------------------------------------------
    # 関数定義
    # 商品一覧画面：各商品の終了日（落札日）を取得
    def get_auction_end_dates(self) -> list:
        """
        商品一覧画面から終了日時（例: ["7/14 23:55", ...]）を全て抽出
        :return: List[str]（該当要素がなければ例外）
        """
        try:
            # 終了日時のセレクタで全要素取得（クラス名: .Product__time）
            elements = self.find_many(By.CSS_SELECTOR, ".Product__time")
            # 各要素からテキストのみ抽出しリスト化。空文字は除外
            end_dates = [el.text.strip() for el in elements if el.text.strip()]
            if not end_dates:
                logger.error("終了日が取得できませんでした")
                raise ValueError("終了日が取得できませんでした")
            logger.debug(f"終了日リスト: {end_dates}")
            return end_dates
        except Exception as e:
            logger.error(f"get_auction_end_dates失敗: {e}")
            raise

    # ------------------------------------------------------------------------------
    # 関数定義
    # 商品一覧画面：各商品の詳細ページのURLを取得
    def get_auction_urls(self) -> list:
        """
        商品一覧画面から詳細ページURLを全て抽出
        :return: List[str]
        """
        try:
            # 商品タイトルのリンク要素を全て取得（CSS: a.Product__titleLink）
            elements = self.find_many(By.CSS_SELECTOR, "a.Product__titleLink")
            # それぞれのhref属性（URL）だけをリスト化
            urls = [el.get_attribute("href") for el in elements if el.get_attribute("href")]
            if not urls:
                logger.error("商品URLが取得できませんでした")
                raise ValueError("商品URLが取得できませんでした")
            logger.debug(f"商品URLリスト: {urls}")
            return urls
        except Exception as e:
            logger.error(f"get_auction_urls失敗: {e}")
            raise

    # ------------------------------------------------------------------------------
    # 関数定義
    # 商品詳細画面：タイトル取得
    def get_title(self) -> str:
        """
        詳細画面から商品タイトルを抽出
        :return: タイトル文字列（見つからない場合は例外）
        """
        try:
            # h1要素（指定クラス名）で商品タイトル取得
            el = self.find_one(By.CSS_SELECTOR, "h1.gv-u-fontSize16--_aSkEz8L_OSLLKFaubKB")
            title = el.text.strip()
            if not title:
                logger.error("タイトルが取得できませんでした")
                raise ValueError("タイトルが取得できませんでした")
            logger.debug(f"タイトル取得: {title}")
            return title
        except Exception as e:
            logger.error(f"get_title失敗: {e}")
            raise

    # ------------------------------------------------------------------------------
    # 関数定義
    # 商品詳細画面：価格取得
    def get_price(self) -> int:
        """
        詳細画面から商品価格を抽出（int型で返す）
        :return: 価格（int）
        """
        try:
            # 指定セレクタ（span.sc-1f0603b0-2.kxUAXU）で価格要素取得
            el = self.find_one(By.CSS_SELECTOR, "span.sc-1f0603b0-2.kxUAXU")
            price_text = el.text.strip().replace(",", "").replace("円", "")  # カンマ・"円"除去
            if not price_text:
                logger.error("価格が取得できませんでした")
                raise ValueError("価格が取得できませんでした")
            price = int(price_text)  # 数値化
            logger.debug(f"価格取得: {price}")
            return price
        except Exception as e:
            logger.error(f"get_price失敗: {e}")
            raise

    # ------------------------------------------------------------------------------
    # 関数定義
    # 商品詳細画面：画像URL取得（優先サイズあり／旧方式fallbackあり）
    def get_image_url(self) -> str:
        """
        詳細画面から商品画像のURLを取得（1200x900サイズを優先的に選択）
        :return: 画像URL（str）
        """
        try:
            img_elements = self.chrome.find_elements(By.TAG_NAME, "img")  # ページ上の全imgタグ取得
            for el in img_elements:
                src = el.get_attribute("src")
                logger.debug(f"チェック中の画像URL: {src}")  # 各imgタグのsrcをデバッグ出力
                # "i-img1200x900"を含む画像があれば優先して返す（高解像度優先）
                if src and "i-img1200x900" in src:
                    logger.info(f"✅ 優先画像URL取得(1200x900): {src}")  # ログ記録
                    return src
            # fallback: 上記で取得できなければ、従来のimgセレクタで一つ取得
            el = self.find_one(By.CSS_SELECTOR, "img.sc-7f8d3a42-4.gOFKtZ")
            fallback_src = el.get_attribute("src")
            logger.warning(f"⚠️ fallback画像URL取得: {fallback_src}")
            return fallback_src
        except Exception as e:
            logger.error(f"get_image_url失敗: {e}")
            raise

    # ------------------------------------------------------------------------------
    # 関数定義
    # 商品詳細画面：タイトル・価格・画像URLをまとめて辞書で返す
    def get_item_info(self) -> dict:
        """
        詳細画面から商品情報（タイトル・価格・画像URL）を辞書形式でまとめて取得
        :return: {"title": str, "price": int, "image_url": str}
        """
        try:
            # それぞれの専用メソッドで個別情報を取得しdict化
            item = {
                "title": self.get_title(),
                "price": self.get_price(),
                "image_url": self.get_image_url(),
            }
            logger.debug(f"商品情報取得: {item}")  # 辞書をログ出力
            return item
        except Exception as e:
            logger.error(f"get_item_info失敗: {e}")
            raise

    # ------------------------------------------------------------------------------
    # 関数定義
    # 商品詳細画面：終了日取得（例: "06/27 22:13"）
    def get_detail_end_date(self) -> str:
        """
        詳細画面から商品の終了日時を抽出（例: "7月6日（日）22時8分 終了"）
        :return: 終了日時の文字列
        """
        try:
            # 指定クラス名のspan要素を全て取得
            elements = self.chrome.find_elements(
                By.CSS_SELECTOR,
                "span.gv-u-fontSize12--s5WnvVgDScOXPWU7Mgqd.gv-u-colorTextGray--OzMlIYwM3n8ZKUl0z2ES"
            )
            # 複数要素のうち「終了」や「時」を含むものだけ返す
            for el in elements:
                text = el.text.strip()
                if "終了" in text or "時" in text:  # キーワードでフィルタ
                    logger.debug(f"終了日取得: {text}")
                    return text
            logger.error("終了日が取得できませんでした")
            raise ValueError("終了日が取得できませんでした")
        except Exception as e:
            logger.error(f"get_detail_end_date失敗: {e}")
            raise