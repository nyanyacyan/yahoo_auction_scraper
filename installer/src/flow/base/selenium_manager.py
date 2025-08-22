# ==========================================================
# import（標準、プロジェクト内モジュール）  # この下で必要なモジュールを読み込む

import time  # スリープや時間待機に使用
import logging  # ログ出力（情報/警告/エラーの記録）に使用
import random  # ランダム値生成（アクセス間隔のばらつきに利用）
from typing import Any, Optional, List  # 型ヒント用（可読性と保守性向上）
from selenium.webdriver.remote.webdriver import WebDriver  # SeleniumのWebDriver型
from selenium.webdriver.remote.webelement import WebElement  # 取得したHTML要素の型
from selenium.common.exceptions import (  # Seleniumで発生しうる代表的な例外群
    NoSuchElementException,  # 要素が見つからない場合に発生
    TimeoutException,  # 待機処理が規定時間内に完了しない場合に発生
    WebDriverException,  # WebDriverに関する一般的な例外
    ElementClickInterceptedException,  # 別要素に遮られてクリックできない場合
)
from selenium.webdriver.support.ui import WebDriverWait  # 条件成立まで待つためのユーティリティ
from selenium.webdriver.support import expected_conditions as EC  # 代表的な待機条件を提供
from selenium.webdriver.common.by import By  # 検索方法の定数（CSS_SELECTOR, XPATH 等）
from installer.src.const import timing as C_TIME  # 待機時間やスリープ秒などの定数定義
from installer.src.const import selectors as C_SEL  # 画面要素のセレクタや関連定数
    # 空行: import群とログ設定の区切り（読みやすさのため）


# ==========================================================
# ログ設定  # このモジュールで使用するロガーを取得

logger = logging.getLogger(__name__)  # モジュール名に紐づくロガー（ハンドラ/レベルは上位設定を想定）
# 空行: ユーティリティ関数群の定義に切り替えるための区切り


# ==========================================================
# 関数定義

def _log_fallback_image(url: str) -> None:  # フォールバック画像URLのサイズ目安に応じてログ出力レベルを変える
    try:  # ヒント参照時の例外に備える
        has_large_hint = any(hint in url for hint in C_SEL.LARGE_IMAGE_HINTS)  # 大画像ヒントを含むか判定
        if has_large_hint:  # 大サイズが期待できる場合
            logger.info(f"fallback画像URL取得(大サイズ確保): {url}")  # 情報ログとして記録
        else:  # ヒントが無い＝小サイズの可能性
            logger.warning(f"fallback画像URL取得(小サイズの可能性): {url}")  # 警告ログとして記録
    except Exception:  # 何らかの例外があっても致命ではない
        logger.info(f"fallback画像URL取得: {url}")  # 最低限URLのみ記録


# ==========================================================
# 関数定義

def random_sleep(min_seconds: Optional[float] = None, max_seconds: Optional[float] = None) -> None:  # アクセス間隔をランダム化する
    """
    アクセス間隔をランダム化（範囲は const/timing で変更可能）
    """
    if min_seconds is None:  # 下限指定が無ければ既定値を使用
        min_seconds = C_TIME.RANDOM_SLEEP_MIN_SECONDS  # 乱数下限（定数）
    if max_seconds is None:  # 上限指定が無ければ既定値を使用
        max_seconds = C_TIME.RANDOM_SLEEP_MAX_SECONDS  # 乱数上限（定数）
    sleep_time: float = random.uniform(float(min_seconds), float(max_seconds))  # 指定範囲で実数の乱数を生成
    logger.debug(f"ランダムスリープ: {sleep_time:.2f}秒")  # 実際に待機する秒数を記録
    time.sleep(sleep_time)  # スリープしてアクセスを間引く


# ==========================================================
# 関数定義

def _is_large_image_url(url: str) -> bool:  # URLが大きい画像のヒントを含むかの判定
    if not url:  # Noneや空文字はFalse
        return False  # 無効URL扱い
    return any(hint in url for hint in C_SEL.LARGE_IMAGE_HINTS)  # ヒント群のいずれかを含めばTrue


# ==========================================================
# 関数定義

def _locators_to_by_tuple(locator_tuple: tuple[str, str]) -> tuple[str, str]:  # 自前の(種別, セレクタ)をSeleniumの(By, 値)へ変換
    kind, selector = locator_tuple  # 先頭要素が種別、後続がセレクタ文字列
    if kind.lower() == "css":  # CSSセレクタ指定の場合
        return (By.CSS_SELECTOR, selector)  # CSSとして返却
    if kind.lower() == "xpath":  # XPath指定の場合
        return (By.XPATH, selector)  # XPathとして返却
    # デフォルトはCSS扱い  # 不正/未知の種別はCSSとみなす
    return (By.CSS_SELECTOR, selector)  # フォールバックの戻り値
    # 空行: クラス定義セクションに切り替えるための区切り


# ==========================================================
# class定義

class Selenium:  # Selenium WebDriverをラップして安全な操作を提供するユーティリティ
    """
    WebDriver操作ユーティリティ（セレクタや待機時間は const で一元管理）
    """
        # 空行: docstringでクラスの役割を説明。以下に初期化と各操作メソッドを定義


    # ==========================================================
    # コンストラクタ

    def __init__(self, chrome: WebDriver) -> None:  # コンストラクタ：使用するWebDriverを受け取り保持
        self.chrome: WebDriver = chrome  # メインで用いるWebDriverインスタンス
        # 互換のため任意に driver 属性を使う場面がある  # 旧コード互換のための別名
        self.driver: WebDriver = chrome  # driverという属性でも同じインスタンスにアクセス可能にする


    # ==========================================================
    # メソッド定義

    def wait_for_page_complete(self, timeout: Optional[int] = None) -> None:  # DOM読み込み完了(complete)まで待機
        timeout = int(C_TIME.PAGE_COMPLETE_TIMEOUT if timeout is None else timeout)  # 未指定なら既定値を使用
        try:  # 例外を捕捉してログに残す
            WebDriverWait(self.chrome, timeout).until(  # 指定秒数内に条件を満たすまで待つ
                lambda d: d.execute_script("return document.readyState") == "complete"  # readyStateがcompleteになる条件
            )
            logger.debug("ページロード完了")  # 成功時のデバッグログ
        except TimeoutException:  # 所定時間を超えた場合
            logger.error("ページのロードがタイムアウトしました")  # エラーログを出力
            raise  # そのまま上位へ例外を伝える
        except Exception as e:  # その他の予期せぬ例外
            logger.error(f"wait_for_page_complete失敗: error={e}")  # 例外内容を記録
            raise  # 例外を再送出


    # ==========================================================
    # メソッド定義

    def find_one(self, by: str, value: str, timeout: Optional[int] = None) -> WebElement:  # 条件に一致する要素を1つ取得
        timeout = int(C_TIME.FIND_TIMEOUT if timeout is None else timeout)  # 待機時間の決定
        try:  # 要素取得の前にページ完了を保証
            self.wait_for_page_complete()  # ページの読み込み完了を待つ
            element: Optional[WebElement] = WebDriverWait(self.chrome, timeout).until(  # 要素の存在を待機
                EC.presence_of_element_located((by, value))  # (by, value)に一致する要素がDOMに存在
            )
            if not element:  # 念のためのNoneチェック
                raise ValueError(f"要素が見つかりません: by={by}, value={value}")  # 明確なエラーにする
            return element  # 見つかった要素を返す
        except Exception as e:  # 取得に失敗した場合
            logger.error(f"要素取得失敗: by={by}, value={value}, error={e}")  # 詳細をログ
            raise  # 例外を上位へ


    # ==========================================================
    # メソッド定義

    def find_many(self, by: str, value: str, timeout: Optional[int] = None) -> List[WebElement]:  # 複数要素の取得
        timeout = int(C_TIME.MULTI_FIND_TIMEOUT if timeout is None else timeout)  # 複数取得用の待機時間
        try:  # まずページ完了を待つ
            self.wait_for_page_complete()  # 読み込み完了を保証
            WebDriverWait(self.chrome, timeout).until(  # 少なくとも1つ存在する状態まで待機
                EC.presence_of_element_located((by, value))  # 要素存在条件
            )
            elements: List[WebElement] = self.chrome.find_elements(by, value)  # 条件に一致する全要素を取得
            if not elements:  # 空リストなら異常
                raise ValueError(f"要素リストが空: by={by}, value={value}")  # 明示的に失敗とする
            return elements  # 取得した要素リストを返す
        except Exception as e:  # 例外発生時
            logger.error(f"複数要素取得失敗: by={by}, value={value}, error={e}")  # 詳細ログ
            raise  # 再送出


    # ==========================================================
    # メソッド定義

    def click(self, by: str, value: str, timeout: Optional[int] = None) -> None:  # 指定要素をクリック
        timeout = int(C_TIME.FIND_TIMEOUT if timeout is None else timeout)  # クリック前の探索待機時間
        try:  # 要素取得とクリックを試みる
            element = self.find_one(by, value, timeout)  # クリック対象の要素を取得
            try:  # 通常のクリック
                element.click()  # 直接クリック
            except ElementClickInterceptedException:  # 別要素に遮られている場合
                self.chrome.execute_script("arguments[0].click();", element)  # JSで強制クリックにフォールバック
            logger.debug(f"クリック成功: by={by}, value={value}")  # 成功ログ
            random_sleep()  # 操作間隔をランダム化（検出回避/負荷低減）
        except Exception as e:  # 失敗時
            logger.error(f"クリック失敗: by={by}, value={value}, error={e}")  # 詳細ログ
            raise  # 例外を上位へ


    # ==========================================================
    # メソッド定義

    def get_auction_end_dates(self) -> list[str]:  # 複数の商品終了日を文字列リストで返す
        try:  # 簡易なロード完了待機
            WebDriverWait(self.chrome, 1.5).until(  # 最大1.5秒待つ
                lambda d: d.execute_script("return document.readyState") == "complete"  # DOM完成の確認
            )
        except Exception:  # 多少の失敗は無視
            pass  # 後続のfindで改めて探索する

        for kind, sel in C_SEL.AUCTION_END_DATE_SELECTORS:  # 用意された複数セレクタを順に試す
            by, value = _locators_to_by_tuple((kind, sel))  # 自前表現を(By, 値)に変換
            try:  # 各セレクタでの探索
                elements: List[WebElement] = self.chrome.find_elements(by, value)  # 一致する要素一覧を取得
                texts: list[str] = [element.text.strip() for element in elements if element.text and element.text.strip()]  # 空を除去
                if texts:  # 1件以上見つかったら
                    logger.debug(f"終了日リスト({kind}:{sel}): {texts}")  # 取得結果を記録
                    return texts  # その時点で返す
            except Exception:  # セレクタ毎の失敗は続行
                continue  # 次候補へ

        logger.debug("終了日セレクタに一致する要素が見つからず（空配列で継続）")  # 最終的に見つからなかった
        return []  # 空リストを返す


    # ==========================================================
    # メソッド定義

    def collect_image_src_candidates(self) -> list[str]:  # 複数のXPATH候補からimg URLを集める
        driver: Optional[WebDriver] = getattr(self, "driver", None)  # 互換属性driverを優先的に参照
        if driver is None:  # WebDriver未設定の場合
            raise RuntimeError("Seleniumユーティリティに driver が設定されていません。")  # 明確な失敗を通知

        candidates: list[str] = []  # 収集したURLのリスト
        seen: set[str] = set()  # 重複排除用セット
        for xpath_expr in C_SEL.IMAGE_CANDIDATE_XPATHS:  # 候補XPATHを順に試す
            try:  # 候補ごとの例外は握りつぶす
                element: Optional[WebElement] = WebDriverWait(driver, 1).until(  # 最長1秒で存在を待機
                    EC.presence_of_element_located((By.XPATH, xpath_expr))  # 要素の存在条件
                )
                url: str = (element.get_attribute("src") or "").strip()  # src属性からURLを取得
                if url and url not in seen:  # 有効かつ未収集なら
                    candidates.append(url)  # 候補に追加
                    seen.add(url)  # 既出セットに追加
            except Exception:  # 見つからない等の失敗
                continue  # 次の候補へ

        return candidates  # 集めたURL一覧を返す


    # ==========================================================
    # メソッド定義

    def get_auction_urls(self) -> list[str]:  # 一覧画面から各商品のリンクURLを収集
        try:  # 簡易ロード完了待機
            WebDriverWait(self.chrome, 1.5).until(  # 最大1.5秒待機
                lambda d: d.execute_script("return document.readyState") == "complete"  # DOM完成を確認
            )
        except Exception:  # 失敗は致命でない
            pass  # 後続で取得を試みる

        for kind, sel in C_SEL.AUCTION_URL_SELECTORS:  # 複数のリンクセレクタを順に試す
            by, value = _locators_to_by_tuple((kind, sel))  # (By, 値)に変換
            try:  # セレクタごとの探索
                elements: List[WebElement] = self.chrome.find_elements(by, value)  # 一致要素を全取得
                urls: list[str] = []  # 結果格納用リスト
                for element in elements:  # 各要素からhrefを取り出す
                    href = element.get_attribute("href")  # リンク先URL
                    if href:  # 空でなければ
                        urls.append(href)  # 収集
                if urls:  # 1件以上取得できたら
                    logger.debug(f"商品URLリスト({kind}:{sel}): {len(urls)}件")  # 件数をログ
                    return urls  # 結果を返す
            except Exception:  # セレクタ失敗
                continue  # 次の候補へ

        logger.debug("商品URLセレクタに一致する要素が見つからず（空配列で継続）")  # いずれも失敗
        return []  # 空配列を返す


    # ==========================================================
    # メソッド定義

    def click_next(self, timeout: Optional[int] = None) -> bool:  # 次ページリンクを探して遷移する
        timeout = int(C_TIME.NEXT_TIMEOUT if timeout is None else timeout)  # タイムアウト秒の決定
        try:  # 一連の操作を例外に強く実行
            self.wait_for_page_complete()  # 現在ページの読み込み完了を待機

            next_element: Optional[WebElement] = None  # 見つかった「次へ」要素の保持用
            for locator_tuple in C_SEL.NEXT_BUTTON_LOCATORS:  # 複数の候補ロケータを順に試す
                by, sel = _locators_to_by_tuple(locator_tuple)  # (By, 値)へ変換
                try:  # 各候補で探索・待機
                    next_element = WebDriverWait(self.chrome, timeout).until(  # 存在するまで待機
                        EC.presence_of_element_located((by, sel))  # DOM存在条件
                    )
                    if next_element:  # 見つかれば
                        break  # 以降の候補は不要
                except Exception:  # 見つからなければ
                    continue  # 次候補へ

            if not next_element:  # どの候補でも見つからなかった場合
                logger.debug("次ページのリンクが見つかりませんでした")  # 情報ログ
                return False  # 遷移不可

            before_url: str = self.chrome.current_url  # 遷移前URLを控えておく（遷移確認用）
            self.chrome.execute_script(  # 対象要素を画面中央にスクロールして表示
                "arguments[0].scrollIntoView({block:'center', inline:'nearest'});",
                next_element
            )
            time.sleep(0.2)  # スクロール後の描画安定を少し待つ
            self.chrome.execute_script("window.scrollBy(0, -60);")  # 固定ヘッダ等で隠れないよう微調整
            time.sleep(0.1)  # わずかに待機

            try:  # クリック前に可視/有効を待機して通常クリック
                WebDriverWait(self.chrome, timeout).until(  # クリック可能状態を待つ
                    lambda d: next_element.is_displayed() and next_element.is_enabled()  # 表示かつ有効
                )
                next_element.click()  # 通常クリック
            except Exception as click_err:  # 通常クリック不可の場合
                logger.debug(f"通常クリック不可: {click_err} → JSクリックにフォールバック")  # フォールバックを記録
                self.chrome.execute_script("arguments[0].click();", next_element)  # JSで強制クリック

            try:  # 遷移完了の検知（要素の無効化で判断）
                WebDriverWait(self.chrome, timeout).until(EC.staleness_of(next_element))  # 旧要素がstaleになるまで待機
            except Exception:  # staleが検知できない場合はURL変化で代替
                WebDriverWait(self.chrome, timeout).until(  # URLが変わるまで待機
                    lambda d: d.current_url != before_url  # 遷移の確認
                )

            self.wait_for_page_complete()  # 遷移先ページの読み込み完了を待機
            random_sleep(C_TIME.POST_NAV_MIN_SECONDS, C_TIME.POST_NAV_MAX_SECONDS)  # 遷移直後も間隔をばらす
            return True  # 遷移成功

        except TimeoutException:  # 待機タイムアウト
            logger.debug("次ページリンク待機タイムアウト")  # 情報ログ
            return False  # 失敗としてFalse
        except Exception as e:  # その他の例外
            logger.warning(f"click_next 失敗: {e}")  # 警告ログ
            return False  # 失敗としてFalse


    # ==========================================================
    # メソッド定義

    @staticmethod  # インスタンス不要で利用できるヘルパー
    def _pick_src(element: WebElement) -> Optional[str]:  # 要素から適切な画像URLを抽出
        """
        要素から src / data-src / srcset の順でURLを抽出して返す。
        見つからない場合は None。
        """
        src: Optional[str] = element.get_attribute("src")  # まずは通常のsrc属性を参照
        if src:  # 取得できればそれを返す
            return src  # src優先
        data_src: Optional[str] = element.get_attribute("data-src")  # 遅延読み込みで使われるdata-src
        if data_src:  # あれば採用
            return data_src  # data-srcを返す
        srcset: Optional[str] = element.get_attribute("srcset")  # 複数解像度のURLリスト
        if srcset:  # 文字列があれば最初のURLを抽出
            first: str = srcset.split(",")[0].strip().split(" ")[0]  # "URL 1x"形式からURL部分を取得
            return first or None  # 空でなければ返す
        return None  # いずれの属性にもURLが無い場合


    # ==========================================================
    # メソッド定義

    def get_title(self) -> str:  # 詳細ページのタイトル文字列を取得
        last_exception: Optional[Exception] = None  # 最後に遭遇した例外を保持
        for kind, sel in C_SEL.TITLE_SELECTORS:  # 複数のセレクタ候補を順に試す
            by, value = _locators_to_by_tuple((kind, sel))  # (By, 値)に変換
            try:  # 取得を試みる
                element: WebElement = self.find_one(by, value, timeout=C_TIME.FIND_TIMEOUT)  # 要素を待って取得
                title = element.text.strip()  # 文字列を整形（前後空白除去）
                if title:  # 非空であれば成功
                    logger.debug(f"タイトル取得({kind}:{sel}): {title}")  # デバッグログ
                    return title  # タイトルを返す
            except Exception as e:  # 失敗した場合
                last_exception = e  # 例外を更新
                continue  # 次の候補へ
        logger.error(f"get_title失敗: {last_exception}")  # すべて失敗時のエラー記録
        raise last_exception if last_exception else ValueError("タイトルが取得できませんでした")  # 適切な例外を投げる


    # ==========================================================
    # メソッド定義

    def get_price(self) -> int:  # 詳細ページの価格を整数で取得
        last_exception: Optional[Exception] = None  # 直近の例外を保持
        for kind, sel in C_SEL.PRICE_SELECTORS:  # 価格用の複数セレクタを試す
            by, value = _locators_to_by_tuple((kind, sel))  # (By, 値)に変換
            try:  # 取得試行
                element: WebElement = self.find_one(by, value, timeout=C_TIME.FIND_TIMEOUT)  # 要素を取得
                price_text = element.text.strip()  # 価格テキストを整形
                for token in C_SEL.PRICE_STRIP_TOKENS:  # 通貨記号/カンマ等の除去対象
                    price_text = price_text.replace(token, "")  # 不要文字を除去
                if not price_text:  # 空なら次候補へ
                    continue  # ループ継続
                price = int(price_text)  # 整数へ変換（失敗時は例外）
                logger.debug(f"価格取得({kind}:{sel}): {price}")  # 取得結果を記録
                return price  # 価格を返す
            except Exception as e:  # 個別候補の失敗
                last_exception = e  # 例外を記録
                continue  # 次候補へ
        logger.error(f"get_price失敗: {last_exception}")  # 全候補で失敗
        raise last_exception if last_exception else ValueError("価格が取得できませんでした")  # 例外を送出


    # ==========================================================
    # メソッド定義

    def get_image_url(self, driver: Optional[WebDriver] = None, wait_seconds: Optional[int] = None) -> str:  # 商品画像のURLを1つ返す
        if driver is None:  # 呼び出し側でdriver未指定なら
            driver = self.chrome  # 内部保持のWebDriverを使用
        if driver is None:  # 念のため二重チェック
            raise RuntimeError("WebDriver is not initialized.")  # 初期化漏れを明示

        wait_seconds = int(C_TIME.IMAGE_WAIT_SECONDS if wait_seconds is None else wait_seconds)  # 待機秒の決定

        last_error: Optional[Exception] = None  # 最後に起きた例外を保持（ログ用）

        for candidate in C_SEL.IMAGE_XPATH_CANDIDATES:  # 定義済みのXPATH候補を順に試す
            try:  # 各候補について要素群の存在を待機
                elements: List[WebElement] = WebDriverWait(driver, wait_seconds).until(  # 指定秒内に要素が現れるか
                    EC.presence_of_all_elements_located((By.XPATH, candidate["xpath"]))  # 一致要素の存在条件
                )
                for element in elements:  # 見つかった要素ごとにURL抽出
                    url = self._pick_src(element)  # src/data-src/srcsetの順でURLを取り出す
                    if not url:  # URLが取れない要素はスキップ
                        continue  # 次の要素へ
                    if candidate.get("is_fallback_small"):  # 小さめ画像のフォールバック候補か
                        _log_fallback_image(url)  # フォールバックである旨をログ記録
                    else:  # 優先候補の場合
                        if _is_large_image_url(url):  # 大サイズが期待できるかを判定
                            logger.debug(f"優先画像URL取得(1200x900相当): {url}")  # 大サイズの旨を記録
                        else:  # ヒントなし
                            logger.debug(f"優先画像URL取得: {url}")  # 通常の優先候補として記録
                    return url  # 最初に得られた有効URLを返す
                last_error = RuntimeError(f"{candidate['label']}: img は見つかったが src なし。")  # 要素はあるがURLなし
            except TimeoutException as e:  # 要素が現れずタイムアウト
                last_error = e  # 例外を保持
            except Exception as e:  # その他の予期せぬ失敗
                last_error = e  # 例外を保持

        if last_error:  # 全候補で失敗した場合は詳細を出す
            logger.debug(f"画像候補の全探索が失敗: {last_error}")  # 直近の例外を含めて記録
        raise RuntimeError("画像URLを取得できませんでした。")  # 呼び出し側へ失敗を通知


    # ==========================================================
    # メソッド定義

    def get_item_info(self) -> dict[str, Any]:  # 商品情報をまとめて辞書で返す
        try:  # いずれかの取得が失敗する可能性に備える
            item_info: dict[str, Any] = {  # 結果を辞書にまとめる
                "title": self.get_title(),  # タイトル文字列
                "price": self.get_price(),  # 価格（int）
                "image_url": self.get_image_url(),  # 画像URL（str）
            }
            logger.debug(f"商品情報取得: {item_info}")  # 取得結果の全体像を記録
            return item_info  # 辞書を返す
        except Exception as e:  # どこかで例外が発生した場合
            logger.error(f"get_item_info失敗: {e}")  # 失敗内容を記録
            raise  # 例外を再送出


    # ==========================================================
    # メソッド定義

    def get_detail_end_date(self) -> str:  # 詳細ページの「終了日」表記を取得する
        try:  # セレクタ候補を順に試す
            for kind, sel in C_SEL.DETAIL_END_DATE_SPANS:  # span等の候補セレクタ群
                by, value = _locators_to_by_tuple((kind, sel))  # (By, 値)へ変換
                elements: List[WebElement] = self.chrome.find_elements(by, value)  # 一致要素を全取得
                for element in elements:  # 各要素のテキストを確認
                    text: str = (element.text or "").strip()  # Noneガード＋前後空白除去
                    if text and any(key in text for key in C_SEL.DETAIL_END_DATE_KEYWORDS):  # キーワードを含むか
                        logger.debug(f"終了日取得({kind}:{sel}): {text}")  # 取得できた値を記録
                        return text  # 最初に見つかったものを返す
            raise ValueError("終了日が取得できませんでした")  # 全候補失敗時
        except Exception as e:  # 例外が出た場合
            logger.error(f"get_detail_end_date失敗: {e}")  # 失敗内容を記録
            raise  # 例外を上位へ


    # ==========================================================
    # メソッド定義

    def click_past_auction_button(self, timeout: Optional[int] = None) -> bool:  # 落札相場ボタンを探してクリックする
        timeout = int(C_TIME.PAST_AUCTION_TIMEOUT if timeout is None else timeout)  # 待機時間の決定
        try:  # 一連の操作を例外に強く実施
            self.wait_for_page_complete()  # 現在ページの読み込み完了を確認
            past_auction_button: Optional[WebElement] = None  # ボタン参照の初期化
            for locator_tuple in C_SEL.PAST_AUCTION_BUTTON_LOCATORS:  # 候補ロケータを順に試す
                by, sel = _locators_to_by_tuple(locator_tuple)  # (By, 値)へ変換
                try:  # クリック可能になるまで待機
                    past_auction_button = WebDriverWait(self.chrome, timeout).until(  # 指定時間内にクリック可能に
                        EC.element_to_be_clickable((by, sel))  # 表示かつ有効が条件
                    )
                    if past_auction_button:  # 見つかったら
                        break  # 以降の候補は不要
                except Exception:  # その候補での失敗
                    continue  # 次候補へ

            if not past_auction_button:  # どの候補でも見つからない場合
                logger.debug("落札相場ボタンが見つかりませんでした")  # 情報ログ
                return False  # 失敗としてFalse

            try:  # まず通常クリックを試みる
                past_auction_button.click()  # クリック実行
            except ElementClickInterceptedException:  # 別要素で遮られた場合
                self.chrome.execute_script("arguments[0].click();", past_auction_button)  # JSクリックでフォロー

            logger.debug("落札相場ボタンをクリック")  # 成功ログ
            random_sleep(0.4, 0.9)  # 画面変化の安定待ち
            return True  # 成功

        except Exception as e:  # 予期しない失敗
            logger.warning(f"落札相場ボタン押下失敗: {e}")  # 警告ログを記録
            return False  # 失敗としてFalseを返す
        