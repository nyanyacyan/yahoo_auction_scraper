# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$%$$$$$$$$$$$$$$$$$$$
# import
import time
import logging
import random
import re

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
    ElementClickInterceptedException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException



logger = logging.getLogger(__name__)
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$


def _log_fallback_image(url: str) -> None:
    """
    fallback画像URLをログ出力するヘルパー関数
    大サイズの場合はINFO、小サイズの可能性があればWARNING
    """
    try:
        is_large = ("i-img1200x900" in url) or ("=w=1200" in url) or ("&w=1200" in url)
        if is_large:
            logger.info(f"fallback画像URL取得(大サイズ確保): {url}")
        else:
            logger.warning(f"fallback画像URL取得(小サイズの可能性): {url}")
    except Exception:
        logger.info(f"fallback画像URL取得: {url}")


# ------------------------------------------------------------------------------
# 関数定義
def random_sleep(min_seconds: float = 0.5, max_seconds: float = 1.5) -> None:
    """人間らしさを出すためのランダムスリープ"""
    sleep_time = random.uniform(min_seconds, max_seconds)
    logger.debug(f"ランダムスリープ: {sleep_time:.2f}秒")
    time.sleep(sleep_time)

# ------------------------------------------------------------------------------
# 関数定義
def _is_large_image_url(url: str) -> bool:
    """1200x900等の大きい画像URLかを手掛かりで判定"""
    if not url:
        return False
    return (
        "i-img1200x900" in url
        or "=w=1200" in url
        or "&w=1200" in url
        or "i-img" in url and ("1200" in url or "900" in url)
    )



# **********************************************************************************
# class定義
class Selenium:
    """Selenium操作のユーティリティ（一覧・詳細の両方で使う共通操作を集約）"""

    # ------------------------------------------------------------------------------
    def __init__(self, chrome: WebDriver):
        """コンストラクタ"""
        self.chrome = chrome

    # ------------------------------------------------------------------------------
    # 基本ユーティリティ
    def wait_for_page_complete(self, timeout: int = 10) -> None:
        """document.readyState が complete になるまで待機"""
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

    def find_one(self, by, value, timeout: int = 10) -> WebElement:
        """単一要素を待って取得"""
        try:
            self.wait_for_page_complete()
            element = WebDriverWait(self.chrome, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            if not element:
                raise ValueError(f"要素が見つかりません: by={by}, value={value}")
            return element
        except Exception as e:
            logger.error(f"要素取得失敗: by={by}, value={value}, error={e}")
            raise

    def find_many(self, by, value, timeout: int = 10) -> list[WebElement]:
        """複数要素を待って取得（最低1件出現まで待機）"""
        try:
            self.wait_for_page_complete()
            WebDriverWait(self.chrome, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            elements = self.chrome.find_elements(by, value)
            if not elements:
                raise ValueError(f"要素リストが空: by={by}, value={value}")
            return elements
        except Exception as e:
            logger.error(f"複数要素取得失敗: by={by}, value={value}, error={e}")
            raise

    def click(self, by, value, timeout: int = 10) -> None:
        """要素をクリック（軽いスリープ付き）"""
        try:
            el = self.find_one(by, value, timeout)
            try:
                el.click()
            except ElementClickInterceptedException:
                # 表示はあるが重なりなどでクリックできない場合はJSクリックで代替
                self.chrome.execute_script("arguments[0].click();", el)
            logger.debug(f"クリック成功: by={by}, value={value}")
            random_sleep()
        except Exception as e:
            logger.error(f"クリック失敗: by={by}, value={value}, error={e}")
            raise

    def get_auction_end_dates(self) -> list[str]:
        """一覧から終了日時の文字列を全件取得。見つからなければ空配列を返して続行。"""
        # ページの描画完了を軽く待つ（最大1.5秒）
        try:
            WebDriverWait(self.chrome, 1.5).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except Exception:
            pass

        # セレクタの揺れに対応（候補を順番に試す）
        selectors = [
            ".Product__time",                 # 既存
            ".Product__closedTime",           # 代替1
            "li.Product__item .Product__time" # 代替2
        ]

        for css in selectors:
            try:
                els = self.chrome.find_elements(By.CSS_SELECTOR, css)
                texts = [el.text.strip() for el in els if el.text and el.text.strip()]
                if texts:
                    logger.debug(f"終了日リスト({css}): {texts}")
                    return texts
            except Exception:
                # 次の候補へ
                continue

        # どれも取れなかったら空配列を返す（ここで例外は投げない）
        logger.debug("終了日セレクタに一致する要素が見つからず（空配列で継続）")
        return []









# =============だめなら消す
    def collect_image_src_candidates(self) -> list[str]:
        """詳細ページから順序付きの画像URL候補を収集する"""
        driver = getattr(self, "driver", None)
        if driver is None:
            raise RuntimeError("Seleniumユーティリティに driver が設定されていません。")

        xpaths_in_priority = [
            # 第1候補: 1200x900 などの大サイズ
            '//img[contains(@src,"i-img1200x900")]',
            # 第2候補: 1200 を含む大きめ i-img
            '//img[contains(@src,"i-img") and (contains(@src,"1200") or contains(@src,"900"))]',
            # 第3候補: auc-pctr（Yahoo側の大きめ画像CDN）
            '//img[contains(@src,"auc-pctr.c.yimg.jp") or contains(@src,"images.auctions.yahoo.co.jp/image")]',
            # 第4候補: 通常の auctions.c.yimg.jp（やや小さめのことが多い）
            '//img[contains(@src,"auctions.c.yimg.jp")]',
        ]

        candidates: list[str] = []
        seen = set()

        for xp in xpaths_in_priority:
            try:
                el = WebDriverWait(driver, 1).until(
                    EC.presence_of_element_located((By.XPATH, xp))
                )
                url = el.get_attribute("src") or ""
                if url and url not in seen:
                    candidates.append(url)
                    seen.add(url)
            except Exception:
                continue

        return candidates
# =============だめなら消す











    def get_auction_urls(self) -> list[str]:
        """一覧から商品URLを全件取得。見つからなければ空配列を返して続行。"""
        # 軽く描画待ち（最大1.5秒）
        try:
            WebDriverWait(self.chrome, 1.5).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except Exception:
            pass

        selectors = [
            "a.Product__titleLink",           # 既存
            "a.Product__title",               # 代替1
            "li.Product__item a[href*='auction']"  # 代替2（保険）
        ]

        for css in selectors:
            try:
                els = self.chrome.find_elements(By.CSS_SELECTOR, css)
                urls = [el.get_attribute("href") for el in els if el.get_attribute("href")]
                if urls:
                    logger.debug(f"商品URLリスト({css}): {len(urls)}件")
                    return urls
            except Exception:
                continue

        logger.debug("商品URLセレクタに一致する要素が見つからず（空配列で継続）")
        return []

    def click_next(self, timeout: int = 8) -> bool:
        """
        検索結果の「次へ」へ進む。
        - 複数候補セレクタから要素探索
        - 中央までスクロールし、オフセットで被り回避
        - 通常 click → 失敗時は JS click
        - staleness または URL 変化で遷移完了を待機
        見つからなければ False、押せたら True。
        """
        try:
            self.wait_for_page_complete()

            candidates = [
                (By.CSS_SELECTOR, "a.Pager__link[data-cl_link='next']"),  # Yahoo固有
                (By.CSS_SELECTOR, "a[aria-label='次へ']"),
                (By.CSS_SELECTOR, "a[rel='next']"),
                (By.XPATH, "//a[contains(@class,'Pager__link') and (@data-cl-params or @href) and (contains(.,'次') or contains(.,'次の'))]"),
                (By.XPATH, "//a[normalize-space()='次へ' or normalize-space()='次の50件']"),
            ]

            next_el = None
            for by, sel in candidates:
                try:
                    next_el = WebDriverWait(self.chrome, timeout).until(
                        EC.presence_of_element_located((by, sel))
                    )
                    if next_el:
                        break
                except Exception:
                    continue

            if not next_el:
                logger.debug("次ページのリンクが見つかりませんでした")
                return False

            before_url = self.chrome.current_url

            # 画面中央→少し上にずらして被り回避
            self.chrome.execute_script(
                "arguments[0].scrollIntoView({block:'center', inline:'nearest'});",
                next_el
            )
            time.sleep(0.2)
            self.chrome.execute_script("window.scrollBy(0, -60);")
            time.sleep(0.1)

            # クリック可能状態になるまで待機（ロケータでなく要素状態を確認）
            try:
                WebDriverWait(self.chrome, timeout).until(
                    lambda d: next_el.is_displayed() and next_el.is_enabled()
                )
                next_el.click()
            except Exception as click_err:
                logger.debug(f"通常クリック不可: {click_err} → JSクリックにフォールバック")
                self.chrome.execute_script("arguments[0].click();", next_el)

            # 遷移完了待機：staleness か URL 変化
            try:
                WebDriverWait(self.chrome, timeout).until(EC.staleness_of(next_el))
            except Exception:
                WebDriverWait(self.chrome, timeout).until(
                    lambda d: d.current_url != before_url
                )

            self.wait_for_page_complete()
            random_sleep(0.6, 1.2)
            return True

        except TimeoutException:
            logger.debug("次ページリンク待機タイムアウト")
            return False
        except Exception as e:
            logger.warning(f"click_next 失敗: {e}")
            return False

    # ------------------------------------------------------------------------------
    # 詳細ページ系
    def get_title(self) -> str:
        """詳細ページ: タイトル取得"""
        try:
            el = self.find_one(By.CSS_SELECTOR, "h1.gv-u-fontSize16--_aSkEz8L_OSLLKFaubKB")
            title = el.text.strip()
            if not title:
                raise ValueError("タイトルが取得できませんでした")
            logger.debug(f"タイトル取得: {title}")
            return title
        except Exception as e:
            logger.error(f"get_title失敗: {e}")
            raise

    def get_price(self) -> int:
        """詳細ページ: 価格取得（int）"""
        try:
            el = self.find_one(By.CSS_SELECTOR, "span.sc-1f0603b0-2.kxUAXU")
            price_text = el.text.strip().replace(",", "").replace("円", "")
            if not price_text:
                raise ValueError("価格が取得できませんでした")
            price = int(price_text)
            logger.debug(f"価格取得: {price}")
            return price
        except Exception as e:
            logger.error(f"get_price失敗: {e}")
            raise




# 置き換え推奨
    def get_image_url(self, driver=None, wait_seconds: int = 2) -> str:
        # driver が渡されていなければ self.chrome を使う
        if driver is None:
            driver = self.chrome
        if driver is None:
            raise RuntimeError("WebDriver is not initialized. Call create_chrome() first.")
        # ここから下は既存の処理（_wait, _find, pick_src, 候補ループなど）をそのまま
            # raise TypeError("get_image_url(driver): driver が None です。")

        # 上から順に試す（失敗したら次へ）
        # 1) 明示の1200x900（優先）
        # 2) auc-pctr CDN（大サイズ想定）
        # 3) auctions.c.yimg.jp（小サイズ fallback）
        candidates = [
            {
                "label": "1200x900",
                "xpath": '//img[contains(@src, "i-img1200x900")]',
                "is_fallback_small": False,
            },
            {
                "label": "auc-pctr CDN",
                "xpath": '//img[contains(@src, "auc-pctr.c.yimg.jp") and contains(@src, "/i/")]',
                "is_fallback_small": False,
            },
            {
                "label": "fallback small",
                "xpath": '//img[contains(@src, "auctions.c.yimg.jp")]',
                "is_fallback_small": True,
            },
        ]

        def pick_src(el) -> str | None:
            # 取得優先順位: src -> data-src -> srcset(先頭)
            src = el.get_attribute("src")
            if src:
                return src
            data_src = el.get_attribute("data-src")
            if data_src:
                return data_src
            srcset = el.get_attribute("srcset")
            if srcset:
                # "url1 1x, url2 2x" のような場合は先頭を採用
                first = srcset.split(",")[0].strip().split(" ")[0]
                return first or None
            return None

        last_error = None

        for c in candidates:
            try:
                # 候補の img を待ち、複数あれば先頭から見る
                elems = WebDriverWait(driver, wait_seconds).until(
                    EC.presence_of_all_elements_located((By.XPATH, c["xpath"]))
                )
                for el in elems:
                    url = pick_src(el)
                    if not url:
                        continue

                    # ログは既存出力に合わせる
                    if c["is_fallback_small"]:
                        logger.warning(f"fallback画像URL取得(小サイズの可能性): {url}")
                    else:
                        # 1200x900 らしい or auc-pctr なら優先ログ
                        if "1200x900" in url or "auc-pctr.c.yimg.jp" in url:
                            logger.info(f"優先画像URL取得(1200x900): {url}")
                        else:
                            logger.info(f"優先画像URL取得: {url}")
                    return url

                # 見つかったが src 取れなかった → 次候補へ
                last_error = RuntimeError(f"{c['label']}: img は見つかったが src なし。")
            except TimeoutException as e:
                # この候補はタイムアウト → 次候補へ
                last_error = e
            except Exception as e:
                # 予期しないエラー → 次候補へ
                last_error = e

        # どの候補でもダメだった
        if last_error:
            logger.debug(f"画像候補の全探索が失敗: {last_error}")
        raise RuntimeError("画像URLを取得できませんでした。")



    def get_item_info(self) -> dict:
        """詳細ページ: タイトル・価格・画像URLをまとめて返す"""
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

    def get_detail_end_date(self) -> str:
        """詳細ページ: 終了日時文字列を取得（例: '7月21日（月）22時7分 終了' など）"""
        try:
            elements = self.chrome.find_elements(
                By.CSS_SELECTOR,
                "span.gv-u-fontSize12--s5WnvVgDScOXPWU7Mgqd.gv-u-colorTextGray--OzMlIYwM3n8ZKUl0z2ES",
            )
            for el in elements:
                text = el.text.strip()
                if text and ("終了" in text or "時" in text):
                    logger.debug(f"終了日取得: {text}")
                    return text
            raise ValueError("終了日が取得できませんでした")
        except Exception as e:
            logger.error(f"get_detail_end_date失敗: {e}")
            raise

    # ------------------------------------------------------------------------------
    # 便利メソッド（必要なら使用）
    def click_past_auction_button(self, timeout: int = 6) -> bool:
        """
        検索一覧で「落札相場」ボタンがあればクリックする。
        見つからなければ False、押せたら True（失敗しても致命ではない想定）。
        """
        try:
            self.wait_for_page_complete()
            candidates = [
                (By.CSS_SELECTOR, ".Auction__pastAuctionBtn"),
                (By.XPATH, "//button[contains(., '落札相場') or contains(., '過去の落札')]"),
                (By.XPATH, "//a[contains(., '落札相場') or contains(., '過去の落札')]"),
            ]

            btn = None
            for by, sel in candidates:
                try:
                    btn = WebDriverWait(self.chrome, timeout).until(
                        EC.element_to_be_clickable((by, sel))
                    )
                    if btn:
                        break
                except Exception:
                    continue

            if not btn:
                logger.debug("落札相場ボタンが見つかりませんでした")
                return False

            try:
                btn.click()
            except ElementClickInterceptedException:
                self.chrome.execute_script("arguments[0].click();", btn)

            logger.debug("落札相場ボタンをクリック")
            random_sleep(0.4, 0.9)
            return True

        except Exception as e:
            logger.warning(f"落札相場ボタン押下失敗: {e}")
            return False