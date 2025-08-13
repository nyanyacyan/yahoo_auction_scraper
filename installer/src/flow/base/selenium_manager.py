# ==========================================================
# import（標準、プロジェクト内モジュール）

import time           # スリープ（待機）でサイト負荷や検出を避けるために使用
import logging        # 動作ログ・エラーログの出力に使用
import random         # ランダムな待機時間の生成に使用
import re             # ここでは未使用（保守の都合で残置かもしれません）
from selenium.webdriver.remote.webdriver import WebDriver     # ドライバ型ヒント
from selenium.webdriver.remote.webelement import WebElement    # 要素型ヒント
from selenium.common.exceptions import (
    NoSuchElementException,             # 要素未発見時の例外（本ファイルでは直接は未使用）
    TimeoutException,                   # 待機のタイムアウト時例外
    WebDriverException,                 # WebDriver全般の例外（本ファイルでは直接は未使用）
    ElementClickInterceptedException,   # クリックが遮られた場合の例外
)  # 例外群をタプル定義でまとめてimport
from selenium.webdriver.support.ui import WebDriverWait        # 明示的待機
from selenium.webdriver.support import expected_conditions as EC  # 待機条件
from selenium.webdriver.common.by import By                    # 検索方法（CSS/XPATH など）
from selenium.webdriver.common.by import By                    # ※重複import（機能は変えないためそのまま）
from selenium.common.exceptions import TimeoutException        # ※重複import（機能は変えないためそのまま）



# ==========================================================
# ログ設定

logger = logging.getLogger(__name__)  # このモジュール専用のロガー



# ==========================================================
# 関数定義

def _log_fallback_image(url: str) -> None:
    """
    役割：フォールバック取得した画像URLのサイズ感に応じてログレベルを切り替える。
    - 大きめ（1200x900級）なら info、小さめの可能性なら warning。
    """  # このdocstringは関数の目的を要約（実行結果に影響なし）
    try:
        is_large = ("i-img1200x900" in url) or ("=w=1200" in url) or ("&w=1200" in url)  # 文字列包含で大サイズの目安を判定
        if is_large:
            logger.info(f"fallback画像URL取得(大サイズ確保): {url}")  # 大きめと判断できた場合は情報レベルで記録
        else:
            logger.warning(f"fallback画像URL取得(小サイズの可能性): {url}")  # 小さい可能性がある場合は注意喚起
    except Exception:
        # URL解析で例外が出てもログは残す（最悪でもURL文字列は出力）
        logger.info(f"fallback画像URL取得: {url}")  # 失敗時も最低限の情報を保持



# ==========================================================
# 関数定義

def random_sleep(min_seconds: float = 0.5, max_seconds: float = 1.5) -> None:
    """
    役割：アクセス間隔をランダム化してサイトへの負荷軽減・Bot検知の回避に寄与。
    """  # 疑似人的な待機を入れるための小ユーティリティ
    sleep_time = random.uniform(min_seconds, max_seconds)  # 下限〜上限の間でランダム秒数を生成
    logger.debug(f"ランダムスリープ: {sleep_time:.2f}秒")  # 実際に何秒待つかをデバッグ出力
    time.sleep(sleep_time)  # 実際に待機してリクエスト頻度を下げる



# ==========================================================
# 関数定義

def _is_large_image_url(url: str) -> bool:
    """
    役割：URL文字列から大きめ画像（1200x900想定）かをざっくり判定。
    注意：単純な文字列包含での判定（確実性よりも手軽さを優先）。
    """  # True/False を返す純粋関数
    if not url:
        return False  # Noneや空文字は大サイズのはずがないためFalse
    return (
        "i-img1200x900" in url
        or "=w=1200" in url
        or "&w=1200" in url
        or "i-img" in url and ("1200" in url or "900" in url)
    )  # 代表的な大サイズ表記が含まれるかで判定



# ==========================================================
# class定義

class Selenium:
    """
    役割：Selenium(WebDriver)操作のユーティリティ集。
    - ページ待機、要素取得、クリック、各種情報のスクレイピングを提供。
    - 例外は基本的に握りつぶさずログを出して再送出 or False/空リストを返して呼び出し側で判断。
    """  # 利用側から共通操作をまとめて呼べるようにする



    # ==========================================================
    # コンストラクタ（インスタンス生成時に実行）

    def __init__(self, chrome: WebDriver):
        self.chrome = chrome  # 実ブラウザ制御のハンドル（以降の操作はこれを通じて行う）



    # ==========================================================
    # メソッド定義

    def wait_for_page_complete(self, timeout: int = 10) -> None:
        """
        役割：document.readyState が 'complete' になるまで待機。
        - タイムアウト時は TimeoutException を送出（上位でのリトライ判断用）。
        """  # ページロード完了前に要素探索しないためのガード
        try:
            WebDriverWait(self.chrome, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )  # JSでreadyStateを確認し、completeになるまで待つ
            logger.debug("ページロード完了")  # 正常完了をデバッグログで記録
        except TimeoutException:
            logger.error("ページのロードがタイムアウトしました")  # 待機時間内に完了せず
            raise  # 例外を上位へ送出して処理方針を委ねる
        except Exception as e:
            logger.error(f"wait_for_page_complete失敗: error={e}")  # 想定外の例外を記録
            raise  # 例外の握りつぶしを避ける


    # ==========================================================
    # メソッド定義

    def find_one(self, by, value, timeout: int = 10) -> WebElement:
        """
        役割：単一要素の取得（存在が確認できるまで待機）。
        - 見つからない場合は例外を投げる（呼び出し側でエラーハンドリング）。
        """  # 失敗時はログ＋例外で原因が追いやすい
        try:
            self.wait_for_page_complete()  # ページ読み込み完了を待ってから探索
            element = WebDriverWait(self.chrome, timeout).until(
                EC.presence_of_element_located((by, value))
            )  # 指定ロケータに一致する要素の出現を待つ
            if not element:
                # presence_of_element_located が返したのに None は想定外 → 明示エラー
                raise ValueError(f"要素が見つかりません: by={by}, value={value}")
            return element  # 見つかった要素を返す
        except Exception as e:
            logger.error(f"要素取得失敗: by={by}, value={value}, error={e}")  # ロケータと例外内容を記録
            raise  # 上位に通知



    # ==========================================================
    # メソッド定義

    def find_many(self, by, value, timeout: int = 10) -> list[WebElement]:
        """
        役割：複数要素の取得（最低1つ出現するまで待機）。
        - 空リストは異常とみなして例外を投げる。
        """  # 要素一覧が必要なときに使用
        try:
            self.wait_for_page_complete()  # 読み込み完了待機
            WebDriverWait(self.chrome, timeout).until(
                EC.presence_of_element_located((by, value))
            )  # 少なくとも1つ現れるまで待つ
            elements = self.chrome.find_elements(by, value)  # 条件にマッチする要素を全取得
            if not elements:
                raise ValueError(f"要素リストが空: by={by}, value={value}")  # 空は異常として扱う
            return elements  # 要素リストを返却
        except Exception as e:
            logger.error(f"複数要素取得失敗: by={by}, value={value}, error={e}")  # 詳細ログ
            raise  # 上位へ再送出



    # ==========================================================
    # メソッド定義

    def click(self, by, value, timeout: int = 10) -> None:
        """
        役割：要素をクリック。遮蔽などで通常クリックに失敗した場合はJSクリックにフォールバック。
        """  # クリック安定化のための二段構え
        try:
            el = self.find_one(by, value, timeout)  # クリック対象の要素を取得
            try:
                el.click()  # 通常のクリックを試みる
            except ElementClickInterceptedException:
                # 画面上に隠れている/被っている等でクリック不可 → JSで強制クリック
                self.chrome.execute_script("arguments[0].click();", el)  # JSでのクリックに切替
            logger.debug(f"クリック成功: by={by}, value={value}")  # 成功ログ
            random_sleep()  # クリック後の待機（遷移や描画を安定させる）
        except Exception as e:
            logger.error(f"クリック失敗: by={by}, value={value}, error={e}")  # 失敗内容を記録
            raise  # 上位でのリカバリに委ねる



    # ==========================================================
    # メソッド定義

    def get_auction_end_dates(self) -> list[str]:
        """
        役割：一覧ページ等から終了日時のテキストを複数抽出。
        - 複数のCSSセレクタを順に試し、最初に取れたリストを返す。
        - 取れなければ空リスト（例外ではなく空で継続方針）。
        """  # サイトのマークアップ揺れに耐えるため複数候補を用意
        try:
            WebDriverWait(self.chrome, 1.5).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )  # 軽い完了待機
        except Exception:
            pass  # 完全ロードに失敗しても後続の要素取得でリカバリを試みる

        selectors = [
            ".Product__time",
            ".Product__closedTime",
            "li.Product__item .Product__time"
        ]  # 探索用の候補セレクタ配列

        for css in selectors:
            try:
                els = self.chrome.find_elements(By.CSS_SELECTOR, css)  # 該当要素をまとめて取得
                texts = [el.text.strip() for el in els if el.text and el.text.strip()]  # 空文字を除外しつつ抽出
                if texts:
                    logger.debug(f"終了日リスト({css}): {texts}")  # どのセレクタで取れたかも記録
                    return texts  # 最初に取れたものを返す
            except Exception:
                continue  # セレクタごとにサイレントに次候補へ

        logger.debug("終了日セレクタに一致する要素が見つからず（空配列で継続）")  # 取得できない場合は空配列で返す旨を記録
        return []  # 空で返し、上位で分岐判断してもらう



    # ==========================================================
    # メソッド定義

    def collect_image_src_candidates(self) -> list[str]:
        """
        役割：詳細ページで画像<img>の src 候補を優先度順に収集して返す。
        注意：self.driver を参照しているが、他メソッドは self.chrome を使っている点に要留意。
            （既存仕様としてそのまま。利用側で driver 属性の設定を忘れないこと）
        """  # 使用前に self.driver の存在を必ず確認する
        driver = getattr(self, "driver", None)  # 動的に driver 属性を参照（なければNone）
        if driver is None:
            # 利用前に self.driver をセットしていないケース（呼び出し順序の不整合）
            raise RuntimeError("Seleniumユーティリティに driver が設定されていません。")  # 事前条件違反を通知

        xpaths_in_priority = [
            # 大サイズ優先（1200x900）
            '//img[contains(@src,"i-img1200x900")]',
            # サイズ表記が含まれる i-img 系
            '//img[contains(@src,"i-img") and (contains(@src,"1200") or contains(@src,"900"))]',
            # CDN(auc-pctr / images.auctions)の一般的なパス
            '//img[contains(@src,"auc-pctr.c.yimg.jp") or contains(@src,"images.auctions.yahoo.co.jp/image")]',
            # もう一段広いyimgドメイン
            '//img[contains(@src,"auctions.c.yimg.jp")]',
        ]  # マッチの厳しさ順に優先度を設定

        candidates: list[str] = []  # 収集したURLの格納先
        seen = set()  # 重複排除用

        for xp in xpaths_in_priority:
            try:
                el = WebDriverWait(driver, 1).until(
                    EC.presence_of_element_located((By.XPATH, xp))
                )  # XPATHに一致するimgが出現するまで短く待機
                url = el.get_attribute("src") or ""  # src属性を取得（無ければ空文字）
                if url and url not in seen:
                    candidates.append(url)  # 新規URLを候補に追加
                    seen.add(url)  # 以後の重複を避ける
            except Exception:
                continue  # 見つからなければ次のXPATH候補へ

        return candidates  # 収集できた候補URL一覧を返却



    # ==========================================================
    # メソッド定義

    def get_auction_urls(self) -> list[str]:
        """
        役割：一覧ページから各商品の詳細URLリストを収集。
        - 複数のセレクタ候補を順に試す。最初に取得できたリストを返す。
        - 取れなければ空リスト（例外ではなく空で継続）。
        """  # タイトルリンクなどを対象にhrefを回収
        try:
            WebDriverWait(self.chrome, 1.5).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )  # 軽い完了待機
        except Exception:
            pass  # 待機失敗時も続行（下で取得を試す）

        selectors = [
            "a.Product__titleLink",
            "a.Product__title",
            "li.Product__item a[href*='auction']"
        ]  # 代表的なリンク候補のセレクタ群

        for css in selectors:
            try:
                els = self.chrome.find_elements(By.CSS_SELECTOR, css)  # まとめて要素取得
                urls = [el.get_attribute("href") for el in els if el.get_attribute("href")]  # hrefのあるものだけ抽出
                if urls:
                    logger.debug(f"商品URLリスト({css}): {len(urls)}件")  # 取得件数を記録
                    return urls  # 最初に取れたものを返却
            except Exception:
                continue  # 次の候補へ

        logger.debug("商品URLセレクタに一致する要素が見つからず（空配列で継続）")  # どれでも取れなかった
        return []  # 空リストで返し上位に判断を委ねる



    # ==========================================================
    # メソッド定義

    def click_next(self, timeout: int = 8) -> bool:
        """
        役割：一覧の「次へ」ページャをクリックして次ページへ遷移。
        - 候補セレクタを複数試す。不可なら False。
        - クリックは通常→ダメならJSクリックの順で試す。
        """  # ページング制御のユーティリティ
        try:
            self.wait_for_page_complete()  # まずページの安定化を待つ

            candidates = [
                (By.CSS_SELECTOR, "a.Pager__link[data-cl_link='next']"),
                (By.CSS_SELECTOR, "a[aria-label='次へ']"),
                (By.CSS_SELECTOR, "a[rel='next']"),
                (By.XPATH, "//a[contains(@class,'Pager__link') and (@data-cl-params or @href) and (contains(.,'次') or contains(.,'次の'))]"),
                (By.XPATH, "//a[normalize-space()='次へ' or normalize-space()='次の50件']"),
            ]  # 「次へ」を表す可能性のあるロケータ一覧

            next_el = None  # 見つかったリンク要素の入れ物
            for by, sel in candidates:
                try:
                    next_el = WebDriverWait(self.chrome, timeout).until(
                        EC.presence_of_element_located((by, sel))
                    )  # 候補ごとに存在を待機
                    if next_el:
                        break  # 最初に見つかった候補で打ち切り
                except Exception:
                    continue  # 見つからなければ次の候補

            if not next_el:
                logger.debug("次ページのリンクが見つかりませんでした")  # ページ末の可能性
                return False  # ページング終了を示す

            before_url = self.chrome.current_url  # 遷移確認用の現在URL保持

            # 要素をビューポート内に持ってくる（ヘッダ固定などで隠れないよう少し上に調整）
            self.chrome.execute_script(
                "arguments[0].scrollIntoView({block:'center', inline:'nearest'});",
                next_el
            )  # 画面中央にスクロール
            time.sleep(0.2)  # わずかに待機して描画を安定させる
            self.chrome.execute_script("window.scrollBy(0, -60);")  # ヘッダで隠れないよう微調整
            time.sleep(0.1)  # さらに短い待機

            try:
                # 表示・有効状態を確認してからクリック
                WebDriverWait(self.chrome, timeout).until(
                    lambda d: next_el.is_displayed() and next_el.is_enabled()
                )  # ユーザ操作可能状態を待つ
                next_el.click()  # 通常クリック
            except Exception as click_err:
                logger.debug(f"通常クリック不可: {click_err} → JSクリックにフォールバック")  # フォールバック切替を記録
                self.chrome.execute_script("arguments[0].click();", next_el)  # JSクリック実施

            try:
                # ページ遷移で next_el が Stale になるのを待つ
                WebDriverWait(self.chrome, timeout).until(EC.staleness_of(next_el))  # 参照が無効化されるまで待機
            except Exception:
                # それでも検知できない場合はURL変化で判定
                WebDriverWait(self.chrome, timeout).until(
                    lambda d: d.current_url != before_url
                )  # URLが変わることで遷移を確認

            self.wait_for_page_complete()  # 遷移先の読み込み完了待ち
            random_sleep(0.6, 1.2)  # 遷移後の描画安定待ち
            return True  # 次ページへ進めたことを示す

        except TimeoutException:
            logger.debug("次ページリンク待機タイムアウト")  # 見つからない/操作不可のまま時間切れ
            return False  # 続行不可
        except Exception as e:
            logger.warning(f"click_next 失敗: {e}")  # 予期しない失敗
            return False  # 安全側でFalseを返す



    # ==========================================================
    # メソッド定義

    def get_title(self) -> str:
        """
        役割：詳細ページからタイトル文字列を取得。
        - セレクタはサイト都合で難読クラス名。変更に弱い点に留意。
        """  # 取得失敗時は例外を送出
        try:
            el = self.find_one(By.CSS_SELECTOR, "h1.gv-u-fontSize16--_aSkEz8L_OSLLKFaubKB")  # 見出し要素を取得
            title = el.text.strip()  # 前後空白を除去して実値を得る
            if not title:
                raise ValueError("タイトルが取得できませんでした")  # 空文字は異常
            logger.debug(f"タイトル取得: {title}")  # 取得内容を記録
            return title  # タイトルを返却
        except Exception as e:
            logger.error(f"get_title失敗: {e}")  # 失敗理由を記録
            raise  # 上位で判断



    # ==========================================================
    # メソッド定義

    def get_price(self) -> int:
        """
        役割：詳細ページから価格を取得して整数に変換。
        - 「1,234円」→ カンマ・円記号を除去 → intに変換。
        """  # 価格表記を数値に正規化
        try:
            el = self.find_one(By.CSS_SELECTOR, "span.sc-1f0603b0-2.kxUAXU")  # 価格表示の要素を検索
            price_text = el.text.strip().replace(",", "").replace("円", "")  # 数値以外の装飾を除去
            if not price_text:
                raise ValueError("価格が取得できませんでした")  # 空は異常
            price = int(price_text)  # 文字列→整数に変換
            logger.debug(f"価格取得: {price}")  # 取得値を記録
            return price  # 価格（整数）を返却
        except Exception as e:
            logger.error(f"get_price失敗: {e}")  # 失敗内容をログ
            raise  # 上位での処理に委ねる



    # ==========================================================
    # メソッド定義

    def get_image_url(self, driver=None, wait_seconds: int = 2) -> str:
        """
        役割：詳細ページの代表画像URLを取得。
        - 優先度順にXPATHで探索し、最初に見つかった妥当なsrc系属性を返す。
        - フォールバック時はログでサイズの注意喚起。
        """  # 画像の取得戦略を段階的に実行
        if driver is None:
            driver = self.chrome  # デフォルトは自身のドライバ
        if driver is None:
            # 呼び出し順が不正な場合（create_chrome相当が未実行など）
            raise RuntimeError("WebDriver is not initialized. Call create_chrome() first.")  # 前提未満足

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
        ]  # 上から順に優先度が高い



    # ==========================================================
    # メソッド定義

        def pick_src(el) -> str | None:
            """
            役割：img要素から適切なURLを取り出す。
            - src → data-src → srcset（先頭） の順に確認。
            """  # 取得できなければNoneで返す
            src = el.get_attribute("src")
            if src:
                return src  # 通常はsrcが最優先
            data_src = el.get_attribute("data-src")
            if data_src:
                return data_src  # 遅延読み込み用属性を利用
            srcset = el.get_attribute("srcset")
            if srcset:
                first = srcset.split(",")[0].strip().split(" ")[0]  # 複数候補の先頭を採用
                return first or None  # 空文字対策
            return None  # どれも無ければNone

        last_error = None  # 失敗理由の記録（最終的にデバッグ出力用）

        for c in candidates:
            try:
                elems = WebDriverWait(driver, wait_seconds).until(
                    EC.presence_of_all_elements_located((By.XPATH, c["xpath"]))
                )  # 候補XPATHに合致する全imgを短時間待機
                for el in elems:
                    url = pick_src(el)  # src/data-src/srcsetの順でURLを取得
                    if not url:
                        continue  # URLが取れない要素はスキップ

                    if c["is_fallback_small"]:
                        logger.warning(f"fallback画像URL取得(小サイズの可能性): {url}")  # フォールバックは警告
                    else:
                        # 優先URLはinfoで明示
                        if "1200x900" in url or "auc-pctr.c.yimg.jp" in url:
                            logger.debug(f"優先画像URL取得(1200x900): {url}")  # 望ましい解像度
                        else:
                            logger.debug(f"優先画像URL取得: {url}")  # その他の優先候補
                    return url  # 最初に見つかった有効URLを返却

                # 要素は見つかったが src 系属性が無い場合
                last_error = RuntimeError(f"{c['label']}: img は見つかったが src なし。")  # 次の候補に回す
            except TimeoutException as e:
                last_error = e  # 待機で見つからなかった
            except Exception as e:
                last_error = e  # 想定外の例外

        if last_error:
            logger.debug(f"画像候補の全探索が失敗: {last_error}")  # なぜ失敗したかを記録
        raise RuntimeError("画像URLを取得できませんでした。")  # いずれの候補でも取得不可の場合



    # ==========================================================
    # メソッド定義

    def get_item_info(self) -> dict:
        """
        役割：詳細ページから title/price/image_url をまとめて取得して辞書で返す。
        - どれかの取得に失敗したら例外（上位でのハンドリング前提）。
        """  # まとめ取得の便宜関数
        try:
            item = {
                "title": self.get_title(),
                "price": self.get_price(),
                "image_url": self.get_image_url(),
            }  # 個別取得メソッドを組み合わせて辞書化
            logger.debug(f"商品情報取得: {item}")  # 結果の全体像を記録
            return item  # 呼び出し側でそのまま利用可能な形で返す
        except Exception as e:
            logger.error(f"get_item_info失敗: {e}")  # どの取得で失敗したかの手掛かり
            raise  # 上位での再試行やスキップ判断に委ねる



    # ==========================================================
    # メソッド定義

    def get_detail_end_date(self) -> str:
        """
        役割：詳細ページ内の「終了日時」テキストを取得。
        - 難読クラス名のため将来変更に弱い。複数要素から条件（'終了' or '時' を含む）で拾う。
        """  # 条件一致する最初の文字列を返す
        try:
            elements = self.chrome.find_elements(
                By.CSS_SELECTOR,
                "span.gv-u-fontSize12--s5WnvVgDScOXPWU7Mgqd.gv-u-colorTextGray--OzMlIYwM3n8ZKUl0z2ES",
            )  # 対象の情報が含まれがちなスパンを一覧取得
            for el in elements:
                text = el.text.strip()  # 前後空白除去
                if text and ("終了" in text or "時" in text):
                    logger.debug(f"終了日取得: {text}")  # 抽出に成功したテキストを記録
                    return text  # 条件を満たしたテキストを返す
            raise ValueError("終了日が取得できませんでした")  # 全て不一致の場合は異常
        except Exception as e:
            logger.error(f"get_detail_end_date失敗: {e}")  # 失敗ログ
            raise  # 上位判断へ



    # ==========================================================
    # メソッド定義

    def click_past_auction_button(self, timeout: int = 6) -> bool:
        """
        役割：「落札相場/過去の落札」ボタンをクリック。
        - 候補セレクタを順に試し、クリック不可ならJSクリックにフォールバック。
        - 見つからなければ False。
        """  # 過去の落札結果表示に遷移させる操作
        try:
            self.wait_for_page_complete()  # 事前にページ安定を待つ
            candidates = [
                (By.CSS_SELECTOR, ".Auction__pastAuctionBtn"),
                (By.XPATH, "//button[contains(., '落札相場') or contains(., '過去の落札')]"),
                (By.XPATH, "//a[contains(., '落札相場') or contains(., '過去の落札')]"),
            ]  # ボタン/リンクの有力候補

            btn = None  # 見つかったボタンの格納先
            for by, sel in candidates:
                try:
                    btn = WebDriverWait(self.chrome, timeout).until(
                        EC.element_to_be_clickable((by, sel))
                    )  # クリック可能になるまで待機
                    if btn:
                        break  # 最初に見つかった候補で決定
                except Exception:
                    continue  # 次の候補へ

            if not btn:
                logger.debug("落札相場ボタンが見つかりませんでした")  # UIが無い/条件不一致など
                return False  # 操作不能を通知

            try:
                btn.click()  # 通常クリック
            except ElementClickInterceptedException:
                # 覆い被さる要素等でクリックできない場合はJSでクリック
                self.chrome.execute_script("arguments[0].click();", btn)  # JSクリックを実施

            logger.debug("落札相場ボタンをクリック")  # 成功ログ
            random_sleep(0.4, 0.9)  # 遷移・描画の安定待ち
            return True  # 成功を通知

        except Exception as e:
            logger.warning(f"落札相場ボタン押下失敗: {e}")  # 想定外の失敗は警告レベルで記録
            return False  # 安全側でFalseを返す





# ==============
# 実行の順序
# ==============
# 1. モジュール（time/logging/random/re と Selenium 関連）をimportする
# → 待機・ログ・乱数・例外型・要素探索の機能を読み込む。補足：By と TimeoutException は重複importだが動作は変わらない。

# 2. logger = logging.getLogger(name) を実行する
# → このモジュール専用のロガーを取得する。補足：以降のDEBUG/INFO/ERRORがここに記録される。

# 3. 関数 _log_fallback_image(url) を定義する
# → 画像URLのサイズ目安からログレベル（info/warning）を切り替える。補足：単純な文字列包含で判定する簡易ロジック。

# 4. 関数 random_sleep(min_seconds, max_seconds) を定義する
# → min〜maxの範囲でランダム秒sleepしてアクセス間隔をばらす。補足：Bot検知回避・負荷軽減のための一手。

# 5. 関数 _is_large_image_url(url) を定義する
# → URLに特定の数字/パターンが含まれるかで“大きめ画像”かを真偽で返す。補足：厳密判定ではなくヒューリスティック。

# 6. class Selenium を定義する
# → WebDriver操作のユーティリティをまとめる器を用意する。補足：ここまで“定義”であり実行はされない。

# 7. メソッド init(self, chrome) を定義する
# → 渡された WebDriver を self.chrome に保持する。補足：以降の操作はこのハンドル経由で行う。

# 8. メソッド wait_for_page_complete(self, timeout=10) を定義する
# → document.readyState==‘complete’ になるまで明示的待機する。補足：タイムアウト時は例外を送出（上位で再試行判断）。

# 9. メソッド find_one(self, by, value, timeout=10) を定義する
# → 要素が現れるまで待って単一要素を返す。補足：見つからなければログして例外を投げる。

# 10. メソッド find_many(self, by, value, timeout=10) を定義する
# → 最低1つの出現を待ち、該当要素のリストを返す。補足：空リストは異常として例外を投げる。

# 11. メソッド click(self, by, value, timeout=10) を定義する
# → 要素取得後にクリックし、遮られたらJSクリックにフォールバック。補足：クリック後は random_sleep で描画安定を待つ。

# 12. メソッド get_auction_end_dates(self) を定義する
# → 複数CSSセレクタを試して“終了日時”テキスト群を抽出する。補足：取得できなければ空配列で返し処理継続方針。

# 13. メソッド collect_image_src_candidates(self) を定義する
# → 優先度付きXPATHでのsrc候補を集めて重複除去し返す。補足：self.driver を前提にしており未設定だと例外になる点が混乱ポイント。

# 14. メソッド get_auction_urls(self) を定義する
# → 一覧ページから商品詳細のhrefを複数収集する。補足：セレクタを順に試し、取れなければ空配列で返す。

# 15. メソッド click_next(self, timeout=8) を定義する
# → 「次へ」リンクを複数ロケータで探し、通常→JSクリックの順に試す。補足：URL変化やstalenessで遷移確認し、成功可否を真偽で返す。

# 16. メソッド get_title(self) を定義する
# → 難読クラスのh1からタイトル文字列を取得する。補足：空なら異常として例外を投げる（サイト変更に弱い）。

# 17. メソッド get_price(self) を定義する
# → 価格テキストからカンマ/円を除去して int に変換する。補足：数値化できなければ例外を投げる。

# 18. メソッド get_image_url(self, driver=None, wait_seconds=2) を定義する
# → 複数XPATH候補からimg要素を見つけ、src→data-src→srcsetの順でURLを抽出する。補足：優先候補が無ければ警告ログのうえ最後は例外。

# 19. メソッド get_item_info(self) を定義する
# → get_title / get_price / get_image_url を呼んで辞書{“title”,“price”,“image_url”}にまとめて返す。補足：どれか失敗で例外（上位でスキップ判断）。

# 20. メソッド get_detail_end_date(self) を定義する
# → 複数spanの中から「終了」や「時」を含むテキストを拾って返す。補足：見つからなければ例外（セレクタ変更に弱い）。

# 21. メソッド click_past_auction_button(self, timeout=6) を定義する
# → 「落札相場/過去の落札」ボタンを探してクリックし、不可ならJSクリックへ。補足：見つからない/失敗時は False を返して安全側に倒す。