# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$%$$$$$$$$$$$$$$$$$$$
# import
import time
import re
import logging
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
# ロガーのセットアップ（エラーや進捗を出力するため）
logger = logging.getLogger(__name__)
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# **********************************************************************************
# class定義
# Seleniumによるスクレイピング操作をラップするクラス
class Selenium:

    # ------------------------------------------------------------------------------
    # 関数定義
    # コンストラクタ（chromeインスタンスを受け取る）
    def __init__(self, chrome: WebDriver):
        """
        Seleniumユーティリティクラス
        :param chrome: 事前に生成済みのwebdriver.Chromeインスタンス
        """
        self.chrome = chrome

    # ========================
    # 基底メソッド（全画面で共通利用できる操作）
    # ========================

    # ------------------------------------------------------------------------------
    # 関数定義
    # ページ内から単一要素を取得
    def find_one(self, by, value, timeout=10) -> WebElement:
        """
        要素を1つ取得（なければエラーをraise）
        :param by: 検索方法（By.ID, By.CSS_SELECTORなど）
        :param value: セレクタ値
        :param timeout: タイムアウト秒
        :return: WebElement
        """
        try:
            # ページの読み込み完了まで待機
            self.wait_for_page_complete()
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            # 指定セレクタの要素が現れるまで待つ
            element = WebDriverWait(self.chrome, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            if not element:
                logger.error(f"要素が見つかりません: by={by}, value={value}")
                raise ValueError(f"要素が見つかりません: by={by}, value={value}")
            return element
        except Exception as e:
            logger.error(f"要素取得失敗: by={by}, value={value}, error={e}")
            raise

    # ------------------------------------------------------------------------------
    # 関数定義
    # ページ内から複数要素を取得
    def find_many(self, by, value, timeout=10) -> list:
        """
        要素を複数取得（1件もなければエラーをraise）
        :return: List[WebElement]
        """
        try:
            # ページの読み込み完了まで待機
            self.wait_for_page_complete()
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            # 最低1つ要素が出現するまで待つ
            WebDriverWait(self.chrome, timeout).until( EC.presence_of_element_located((by, value)) )

            # 複数の要素をリストで取得
            elements = self.chrome.find_elements(by, value)
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
        指定要素をクリック
        """
        try:
            # 対象要素を取得してクリック
            element = self.find_one(by, value, timeout)
            element.click()
            logger.debug(f"クリック成功: by={by}, value={value}")
        except Exception as e:
            logger.error(f"クリック失敗: by={by}, value={value}, error={e}")
            raise

    # ------------------------------------------------------------------------------
    # 関数定義
    # ページのロード（読み込み）が終わるまで待機
    def wait_for_page_complete(self, timeout=10):
        """
        ページロードがcompleteになるまで待つ
        """
        try:
            from selenium.webdriver.support.ui import WebDriverWait

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

    # ========================
    # 利用メソッド（各画面）
    # ========================

    # ---- 一覧画面 ----

    # ------------------------------------------------------------------------------
    # 関数定義
    # 商品一覧画面：各商品の終了日（落札日）を取得
    def get_auction_end_dates(self) -> list:
        """
        商品一覧画面から各商品の終了日を抽出（例: ["7/14 23:55", ...]）
        :return: List[str]
        """
        try:
            from selenium.webdriver.common.by import By

            # 終了日を示す要素（クラス名で指定）
            elements = self.find_many(By.CSS_SELECTOR, ".Product__time")
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
        商品一覧画面から詳細ページURLを抽出
        :return: List[str]
        """
        try:
            from selenium.webdriver.common.by import By

            # 商品タイトルのリンク要素を全て取得
            elements = self.find_many(By.CSS_SELECTOR, "a.Product__titleLink")
            # それぞれのhref属性（URL）を抽出
            urls = [el.get_attribute("href") for el in elements if el.get_attribute("href")]
            if not urls:
                logger.error("商品URLが取得できませんでした")
                raise ValueError("商品URLが取得できませんでした")
            logger.debug(f"商品URLリスト: {urls}")
            return urls
        except Exception as e:
            logger.error(f"get_auction_urls失敗: {e}")
            raise

    # ---- 詳細画面 ----

    # ------------------------------------------------------------------------------
    # 関数定義
    # 商品詳細画面：タイトル取得
    def get_title(self) -> str:
        """
        詳細画面から商品タイトル取得
        """
        try:
            from selenium.webdriver.common.by import By

            # 商品タイトルのh1要素を取得
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
        詳細画面から商品価格取得
        """
        try:
            from selenium.webdriver.common.by import By

            # 価格のspan要素を取得
            el = self.find_one(By.CSS_SELECTOR, "span.sc-1f0603b0-2.kxUAXU")
            price_text = el.text.strip().replace(",", "").replace("円", "")
            if not price_text:
                logger.error("価格が取得できませんでした")
                raise ValueError("価格が取得できませんでした")
            price = int(price_text)
            logger.debug(f"価格取得: {price}")
            return price
        except Exception as e:
            logger.error(f"get_price失敗: {e}")
            raise

    # ------------------------------------------------------------------------------
    # 関数定義
    # 商品詳細画面：画像URL取得
    def get_image_url(self) -> str:
        """
        詳細画面から商品画像のURLを取得
        """
        try:
            from selenium.webdriver.common.by import By

            # 商品画像のimg要素を取得
            el = self.find_one(By.CSS_SELECTOR, "img.sc-7f8d3a42-4.gOFKtZ")
            image_url = el.get_attribute("src")
            if not image_url:
                logger.error("画像URLが取得できませんでした")
                raise ValueError("画像URLが取得できませんでした")
            logger.debug(f"画像URL取得: {image_url}")
            return image_url
        except Exception as e:
            logger.error(f"get_image_url失敗: {e}")
            raise

    # ------------------------------------------------------------------------------
    # 関数定義
    # 商品詳細画面：タイトル・価格・画像URLをまとめて辞書で返す
    # ======== 任意: 辞書形式でまとめて取得 ========
    def get_item_info(self) -> dict:
        """
        詳細画面から商品情報（タイトル・価格・画像URL）を辞書形式で取得
        """
        try:
            item = {
                "title": self.get_title(),
                "price": self.get_price(),
                "image_url": self.get_image_url(),
            }
            logger.debug(f"商品情報取得: {item}")
            return item
        except Exception as e:
            logger.error(f"get_item_info失敗: {e}")
            raise

    # ------------------------------------------------------------------------------
    # 関数定義
    # 商品詳細画面：終了日取得（例: "06/27 22:13"）
    def get_detail_end_date(self) -> str:
        """
        詳細画面から商品の終了日時を取得（例: "7月6日（日）22時8分 終了"）
        """
        try:
            from selenium.webdriver.common.by import By
            elements = self.chrome.find_elements(
                By.CSS_SELECTOR,
                "span.gv-u-fontSize12--s5WnvVgDScOXPWU7Mgqd.gv-u-colorTextGray--OzMlIYwM3n8ZKUl0z2ES"
            )
            # 終了日時らしいテキストのみ抽出
            for el in elements:
                text = el.text.strip()
                if "終了" in text or "時" in text:  # ←この判定でフィルタ
                    logger.debug(f"終了日取得: {text}")
                    return text
            logger.error("終了日が取得できませんでした")
            raise ValueError("終了日が取得できませんでした")
        except Exception as e:
            logger.error(f"get_detail_end_date失敗: {e}")
            raise
