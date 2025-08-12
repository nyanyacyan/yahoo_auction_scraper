# main_flow.py
# ==========================================================
# import（標準、プロジェクト内モジュール）

import logging
from typing import List, Dict, Any, Optional

import pandas as pd

from datetime import datetime, date, time as dtime
import re
import time as pytime

from installer.src.flow.base.chrome import Chrome
from installer.src.flow.base.spreadsheet_read import SpreadsheetReader
from installer.src.flow.base.url_builder import UrlBuilder
from installer.src.utils.text_utils import NumExtractor
from installer.src.flow.base.utils import DateConverter
from installer.src.flow.base.number_calculator import PriceCalculator
from installer.src.flow.base.selenium_manager import Selenium
from installer.src.flow.detail_page_flow import DetailPageFlow
from installer.src.flow.write_gss_flow import WriteGssFlow
from flow.base.image_downloader import ImageDownloader

# 追加：落札相場ボタン押下に使う
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# ==========================================================
# ログ設定

logger = logging.getLogger(__name__)


# ==========================================================
# ページサマリ用ユーティリティ

from dataclasses import dataclass

@dataclass
class ParseStats:
    ok: int = 0
    ng: int = 0
    min_dt: Optional[datetime] = None
    max_dt: Optional[datetime] = None

    def add_success(self, dt: datetime) -> None:
        self.ok += 1
        if self.min_dt is None or dt < self.min_dt:
            self.min_dt = dt
        if self.max_dt is None or dt > self.max_dt:
            self.max_dt = dt

    def add_failure(self) -> None:
        self.ng += 1


def log_page_summary(page_no: int, added_count: int, total_count: int, stats: ParseStats) -> None:
    """
    ページ単位のサマリをINFOで出力。
    - 追加件数・累計件数
    - 日付パース 成功/失敗 件数
    - そのページ内の最小/最大日時
    """
    min_s = stats.min_dt.strftime("%Y-%m-%d %H:%M:%S") if stats.min_dt else "-"
    max_s = stats.max_dt.strftime("%Y-%m-%d %H:%M:%S") if stats.max_dt else "-"
    logger.info(
        "ページ%d サマリ: 追加 %d / 累計 %d | パース 成功 %d / 失敗 %d | 最小 %s, 最大 %s",
        page_no, added_count, total_count, stats.ok, stats.ng, min_s, max_s
    )


# ==========================================================
# スプレッドシート関連の設定

class Config:
    SPREADSHEET_ID = "1nRJh0BqQazHe8qgT2YTZbMaZ9osPX835CbM3KkUjkcE"
    SEARCH_COND_SHEET = "Master"
    DATA_OUTPUT_SHEET = "1"   # 出力は常に「1」に固定
    HEADLESS = False        # ← 追加（上書きしたいとき True に）
    USER_AGENT = None

# ==========================================================
# スクレイピングとスプレッドシート書き込みの司令塔

class MainFlow:

    def __init__(self, config: Config):
        self.config = config
        self.logger = logger
        self._past_btn_tried = False

    def _ensure_selenium_stack(self) -> None:
        """Chrome → WebDriver → Selenium/DetailPageFlow を初期化"""
        # ヘッドレス解除したいので False を既定に
        headless = getattr(self.config, "headless", getattr(self.config, "HEADLESS", False))
        user_agent = getattr(self.config, "user_agent", getattr(self.config, "USER_AGENT", None))

        # Chrome ラッパ初期化
        if self.chrome is None:
            self.chrome = Chrome(headless=headless, user_agent=user_agent)
            self.logger.info("ChromeDriverを起動しました。")

        # WebDriver の取得（ラッパの仕様差を吸収）
        if self.driver is None:
            if hasattr(self.chrome, "get_driver") and callable(self.chrome.get_driver):
                self.driver = self.chrome.get_driver()
            elif hasattr(self.chrome, "driver"):
                self.driver = self.chrome.driver
            else:
                # 旧実装などで静的メソッドがある場合のフォールバック
                try:
                    self.driver = Chrome.get_driver()
                except TypeError:
                    raise AttributeError(
                        "Chrome から WebDriver を取得できません。"
                        "get_driver() または driver 属性を実装してください。"
                    )

        # Selenium ユーティリティ
        if self.selenium is None:
            self.selenium = Selenium(self.driver)

        # 詳細ページ抽出フロー
        if self.detail_flow is None:
            self.detail_flow = DetailPageFlow(self.driver, self.selenium)

    # --- （任意の手動テスト用：runからは呼ばない） ---
    def test_num_extractor(self, text: str) -> None:
        try:
            ct_value = NumExtractor.extract_ct_value(text)
            self.logger.info(f"カラット抽出: 型={type(ct_value)} | 値={ct_value}")
        except Exception as e:
            self.logger.error(f"NumExtractor抽出失敗: {e}")

    def load_search_conditions(self) -> List[Dict[str, Any]]:
        try:
            reader = SpreadsheetReader(
                spreadsheet_id=self.config.SPREADSHEET_ID,
                worksheet_name=self.config.SEARCH_COND_SHEET
            )
            self.logger.info(f"スプレッドシート({self.config.SPREADSHEET_ID})から検索条件取得")
            conditions = reader.get_search_conditions()
            self.logger.info(f"取得件数: {len(conditions)}件")
            return conditions
        except Exception as e:
            self.logger.error(f"スプレッドシート読込中エラー: {e}")
            return []

    # --- （任意の手動テスト用：runからは呼ばない） ---
    def write_test_data(self, worksheet) -> None:
        test_data = [
            {
                "date": "2025-06-27",
                "title": "ダイヤ ルース 0.500ct 鑑定書付き",
                "price": 51700,
                "ct": 0.500,
                "1ct_price": 84100,
                "image": "https://auctions.c.yimg.jp/images.auctions.yahoo.co.jp/image/dr000/auc0106/user/5ec807c934150c37fea5b1cda6cdb4938dea1bcdd982696a3d9c90b59c549314/i-img1200x849-17500560233691ls9baa33.jpg"
            },
            {
                "date": "2025-06-28",
                "title": "ダイヤモンドルース 0.200ct 新品",
                "price": 20000,
                "ct": 0.200,
                "1ct_price": 32600,
                "image": "https://auctions.c.yimg.jp/images.auctions.yahoo.co.jp/image/dr000/auc0106/user/5ec807c934150c37fea5b1cda6cdb4938dea1bcdd982696a3d9c90b59c549314/i-img1200x849-17500560233691ls9baa33.jpg"
            }
        ]
        try:
            flow = WriteGssFlow(worksheet)
            flow.run(test_data)
            self.logger.info("テストデータ一括書き込み成功")
        except Exception as e:
            self.logger.error(f"テストデータ書き込み失敗: {e}")

    def extract_keyword(self, row: Dict[str, Any]) -> str:
        return " ".join([str(row.get(f"search_{i}", "")) for i in range(1, 6)]).strip()

    @staticmethod
    def _to_date(value):
        """DateConverter.convert() の結果を date に正規化。失敗時は None。"""
        if value is None or str(value).strip() == "":
            return None
        try:
            d = DateConverter.convert(value)
            # DateConverter が date / datetime / Timestamp 等を返す想定に対応
            if isinstance(d, datetime):
                return d.date()
            if isinstance(d, date):
                return d
            if hasattr(d, "to_pydatetime"):  # pandas.Timestamp の可能性
                return d.to_pydatetime().date()
            if hasattr(d, "date") and callable(getattr(d, "date")):
                dd = d.date()
                return dd if isinstance(dd, date) else None
            return None
        except Exception as e:
            logger.debug(f"_to_date変換失敗: {value} ({e})")
            return None

    def _get_page_min_date(self, end_times: list) -> "date | None":
        """
        一覧ページ内の '終了日時' リストから、date の最小値を返す。
        変換失敗は無視。1件も変換できない場合は None。
        """
        page_min: Optional[date] = None
        for v in end_times:
            d = self._to_date(v)
            if d is None:
                continue
            if page_min is None or d < page_min:
                page_min = d
        return page_min

    # ===== ここから追加（No結果ページ検知）=====
    def _page_has_no_results(self, driver) -> bool:
        """
        Yahoo!オークションの閉鎖検索で、結果ゼロのページを判定する。
        - 代表的な文言を page_source から検出
        - 明示的な NoResult 系要素が表示されていれば True
        エラー時は False（＝「未判定」扱い）を返す。
        """
        try:
            # 文言パターン（実際に画面に出る代表例）
            phrases = (
                "条件に一致する商品は見つかりませんでした",
                "該当する商品はありません",
                "該当するオークションはありません",
            )
            src = driver.page_source or ""
            if any(p in src for p in phrases):
                return True

            # NoResult 系の要素（ある場合は可視状態を優先）
            selectors = [
                ".Module__noResult",
                ".NoResult",
                "#NoResult",
                ".Search__noItems",
            ]
            for css in selectors:
                try:
                    els = driver.find_elements(By.CSS_SELECTOR, css)
                    if any(e.is_displayed() for e in els):
                        return True
                except Exception:
                    # セレクタが無い/DOM側でエラー → そのセレクタはスキップ
                    pass

            # ここまでで判定できなければ False
            return False
        except Exception:
            # 何かしら例外（読み込み途中など）→ 判定不能として False
            return False
    # ===== 追加ここまで =====

    # ==========================================================
    # 基本版
    def url_and_selenium_flow(self, conditions: List[Dict[str, Any]]) -> None:
        if not conditions:
            self.logger.warning("条件が空なのでURL生成処理スキップ")
            return

        # ---- DataFrame 前処理 ----
        df = pd.DataFrame(conditions)
        df = df[df["start_date"].astype(str).str.strip() != ""]
        df = df[df["end_date"].astype(str).str.strip() != ""]

        url_builder = UrlBuilder()

        for idx, row in df.iterrows():
            # --- 期間 ---
            try:
                start_date = self._to_date(row.get("start_date"))
                end_date   = self._to_date(row.get("end_date"))
                if start_date is None or end_date is None:
                    raise ValueError("開始/終了日の解釈に失敗")
            except Exception as e:
                self.logger.error(f"{idx+1}行目: 開始・終了日変換失敗: {e}")
                continue

            # --- キーワード ---
            keyword = self.extract_keyword(row)
            if not keyword:
                self.logger.warning(f"{idx+1}行目: キーワードなし。スキップ")
                continue

            # 件数最大化（100要求。サイト側で50になる場合あり）
            search_url = url_builder.build_url(keyword, per_page=100)
            self.logger.info(f"{idx+1}行目: キーワード={keyword} | URL={search_url}")

            driver = Chrome.get_driver()
            selenium_util = Selenium(driver)
            page_no = 1
            detail_urls: List[str] = []
            seen: set[str] = set()

            try:
                driver.get(search_url)

                # --- 落札相場ボタン（失敗しても続行） ---
                try:
                    WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, ".Auction__pastAuctionBtn"))
                    ).click()
                    self.logger.debug("落札相場ボタンをクリック")
                except Exception as e:
                    self.logger.warning(f"落札相場ボタン押下失敗: {e}")

                # ===== 一覧巡回 =====
                while True:
                    try:
                        end_times = selenium_util.get_auction_end_dates()
                        urls      = selenium_util.get_auction_urls()
                    except Exception as e:
                        self.logger.warning(f"{idx+1}行目: 商品URLまたは終了日時取得失敗: {e}")
                        break

                    n = min(len(end_times), len(urls))
                    added_this_page = 0

                    # ページサマリ統計
                    stats = ParseStats()

                    # アイテム単位の判定
                    for i in range(n):
                        d = self._to_date(end_times[i])
                        if d is None:
                            stats.add_failure()
                            continue
                        # サマリ統計用にdatetime化（00:00:00付与）
                        stats.add_success(datetime.combine(d, dtime.min))

                        if d > end_date:
                            continue
                        elif d < start_date:
                            continue
                        else:
                            u = urls[i]
                            if u not in seen:
                                seen.add(u)
                                detail_urls.append(u)
                                added_this_page += 1

                    log_page_summary(page_no, added_this_page, len(detail_urls), stats)

                    # ページ全体の最小日付で終了判定（これ以降は開始日より古いはず）
                    page_min = self._get_page_min_date(end_times)
                    if page_min is not None and page_min < start_date:
                        self.logger.info(
                            f"{idx+1}行目: ページ{page_no}の最小日付 {page_min} が開始日 {start_date} より前のため巡回終了"
                        )
                        break

                    # 次ページへ
                    try:
                        has_next = selenium_util.click_next()
                        if not has_next:
                            self.logger.info(f"{idx+1}行目: 次ページなし。累計 {len(detail_urls)} 件で巡回終了")
                            break
                        page_no += 1
                    except Exception as e:
                        self.logger.warning(f"{idx+1}行目: 次へクリック失敗または次ページなし: {e}")
                        break

                if not detail_urls:
                    self.logger.info(f"{idx+1}行目: 対象期間内の商品なし")
                    continue

                # ===== 詳細抽出 =====
                details: List[Dict[str, Any]] = []
                for detail_url in detail_urls:
                    try:
                        detail_flow = DetailPageFlow(driver, selenium_util)
                        detail_data = detail_flow.extract_detail(detail_url)
                        details.append(detail_data)
                        self.logger.info(f"{idx+1}行目: 詳細抽出成功: {detail_url}")
                    except Exception as e:
                        self.logger.warning(f"{idx+1}行目: 詳細抽出失敗 {detail_url}: {e}")

                # ===== スプレッドシート書き込み =====
                if details:
                    # date の先頭の "'" を除去（既に付いているケースへのケア）
                    for dct in details:
                        if isinstance(dct.get("date"), str) and dct["date"].startswith("'"):
                            dct["date"] = dct["date"].lstrip("'")

                    try:
                        output_sheet_name = self.config.DATA_OUTPUT_SHEET  # 例: "1"
                        reader = SpreadsheetReader(self.config.SPREADSHEET_ID, output_sheet_name)
                        worksheet = reader.get_worksheet(output_sheet_name)
                        flow = WriteGssFlow(worksheet)
                        flow.run(details)
                        self.logger.info(f"{idx+1}行目: 期間内URLを {len(details)} 件書き込み完了")
                    except Exception as e:
                        self.logger.error(f"{idx+1}行目: スプレッドシート書き込み失敗: {e}")

            finally:
                try:
                    driver.quit()
                except Exception:
                    pass

    # ==========================================================
    # 先読み許容版
    def url_and_selenium_flow_lookahead(self, conditions: List[Dict[str, Any]], lookahead_pages: int = 1) -> None:
        """
        ページ内の最小終了日が start_date を下回っても、念のため +lookahead_pages だけ
        余分にページを巡回して取りこぼしを防ぐ版。
        """
        if not conditions:
            self.logger.warning("条件が空なのでURL生成処理スキップ")
            return

        df = pd.DataFrame(conditions)
        df = df[df["start_date"].astype(str).str.strip() != ""]
        df = df[df["end_date"].astype(str).str.strip() != ""]

        url_builder = UrlBuilder()

        for idx, row in df.iterrows():
            # --- 期間 ---
            try:
                start_date = self._to_date(row.get("start_date"))
                end_date   = self._to_date(row.get("end_date"))
                if start_date is None or end_date is None:
                    raise ValueError("開始/終了日の解釈に失敗")
            except Exception as e:
                self.logger.error(f"{idx+1}行目: 開始・終了日変換失敗: {e}")
                continue

            # --- キーワード ---
            keyword = self.extract_keyword(row)
            if not keyword:
                self.logger.warning(f"{idx+1}行目: キーワードなし。スキップ")
                continue

            search_url = url_builder.build_url(keyword, per_page=100)
            self.logger.info(f"{idx+1}行目: キーワード={keyword} | URL={search_url}")

            driver = Chrome.get_driver()
            selenium_util = Selenium(driver)
            page_no = 1
            detail_urls: List[str] = []
            seen: set[str] = set()
            extra_pages_left = int(lookahead_pages) if lookahead_pages and int(lookahead_pages) > 0 else 0
            crossed_threshold = False  # 一度でも「ページ最小日付 < start_date」を検知したか
            # ===== 任意：結果ゼロ連続ページの上限（保険）=====
            zero_pages = 0
            ZERO_CAP   = 3  # ← 連続3ページ「結果ゼロ」で強制終了

            # 検索ページへ
            driver.get(search_url)

            # 軽いロード待ち（最大2秒）
            try:
                WebDriverWait(driver, 2).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
            except Exception:
                pass  # 読み込み待ち失敗は無視して続行

            # まれに data: の白画面になる対策で再トライ
            if driver.current_url.startswith("data:"):
                self.logger.debug("current_url が data: のため再ナビゲーションを実施")
                driver.get(search_url)

            # --- 落札相場ボタン（見つかれば1回だけ押す。無ければスキップ） ---
            try:
                # 1秒だけ存在チェック（クリック可否までは待たない）
                past_btn = WebDriverWait(driver, 1).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".Auction__pastAuctionBtn"))
                )
                try:
                    # 通常clickは失敗しやすいのでJS click
                    driver.execute_script("arguments[0].click();", past_btn)
                    self.logger.debug("落札相場ボタン(JS)クリック")

                    # 画面切替の軽い待機（最大1秒）
                    # ※ any_of は Selenium 4 以降。無ければどちらか一方だけでOK。
                    WebDriverWait(driver, 1).until(
                        EC.any_of(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".Auc")),
                            EC.url_contains("closedsearch")  # 切替でURL変化する場合の保険
                        )
                    )
                except Exception as e:
                    self.logger.debug(f"落札相場ボタンのクリック処理失敗（無視して続行）: {e}")
            except Exception:
                # 見つからなければログだけ残してスキップ
                self.logger.debug("落札相場ボタン見つからず → スキップして続行")

                # ===== 一覧巡回 =====
                while True:
                    try:
                        end_times = selenium_util.get_auction_end_dates()
                        urls      = selenium_util.get_auction_urls()
                    except Exception as e:
                        self.logger.warning(f"{idx+1}行目: 商品URLまたは終了日時取得失敗: {e}")
                        break

                    n = min(len(end_times), len(urls))
                    added_this_page = 0

                    # ページサマリ統計
                    stats = ParseStats()

                    for i in range(n):
                        d = self._to_date(end_times[i])
                        if d is None:
                            stats.add_failure()
                            continue
                        stats.add_success(datetime.combine(d, dtime.min))

                        if d > end_date:
                            continue
                        elif d < start_date:
                            continue
                        else:
                            u = urls[i]
                            if u not in seen:
                                seen.add(u)
                                detail_urls.append(u)
                                added_this_page += 1

                    log_page_summary(page_no, added_this_page, len(detail_urls), stats)

                    if n == 0:
                        # ページ文言 or DOM で「条件に一致する商品は見つかりませんでした。」を検知
                        if self._page_has_no_results(driver):
                            self.logger.info(f"{idx+1}行目: 条件に一致する商品は見つかりませんでした（ページ{page_no}）。巡回終了")
                            break

                        # 念のため: 空ページが続くときのフェイルセーフ（例: 3連続）
                        empty_pages_in_a_row = locals().get("empty_pages_in_a_row", 0) + 1
                        locals()["empty_pages_in_a_row"] = empty_pages_in_a_row
                        if empty_pages_in_a_row >= 3:
                            self.logger.info(f"{idx+1}行目: 空ページが{empty_pages_in_a_row}連続。巡回終了")
                            break
                    else:
                        # 何か取れたらリセット
                        locals()["empty_pages_in_a_row"] = 0

                    # ページ最小日付で終了/先読み判定
                    page_min = self._get_page_min_date(end_times)
                    if page_min is not None and page_min < start_date:
                        # 閾値を跨いだことを記録
                        if not crossed_threshold:
                            crossed_threshold = True
                            self.logger.info(
                                f"{idx+1}行目: ページ{page_no}の最小日付 {page_min} が開始日 {start_date} より前 → "
                                f"先読みを {extra_pages_left} ページ許容"
                            )

                        if extra_pages_left <= 0:
                            self.logger.info(
                                f"{idx+1}行目: 先読み許容量を使い切ったため巡回終了（累計 {len(detail_urls)} 件）"
                            )
                            break
                        else:
                            extra_pages_left -= 1
                            self.logger.info(
                                f"{idx+1}行目: 閾値跨ぎ後の先読み継続。残り先読みページ数: {extra_pages_left}"
                            )

                    # 次ページへ（ボタンクリックを廃止して URL 直ジャンプに変更）
                    try:
                        per_page = 100  # build_url(per_page=100) と合わせる
                        next_b = (page_no * per_page) + 1
                        cur = driver.current_url

                        # 既存の b= を除去してから付け直す
                        base = re.sub(r"([?&])b=\d+", r"\1", cur)
                        # 末尾に ? / & が残っていれば整理
                        if base.endswith("?") or base.endswith("&"):
                            base = base[:-1]
                        sep = "&" if "?" in base else "?"
                        next_url = f"{base}{sep}b={next_b}&n={per_page}"

                        t0 = pytime.perf_counter()
                        driver.get(next_url)
                        WebDriverWait(driver, 3).until(lambda d: f"b={next_b}" in d.current_url)
                        self.logger.info("URLジャンプで次ページへ: b=%d（%.2f秒）", next_b, pytime.perf_counter() - t0)
                        page_no += 1
                    except Exception as e:
                        self.logger.info(f"{idx+1}行目: 次ページなし/遷移失敗のため終了: {e}")
                        break

                if not detail_urls:
                    self.logger.info(f"{idx+1}行目: 対象期間内の商品なし")
                    continue

                # ===== 詳細抽出 =====
                details: List[Dict[str, Any]] = []
                for detail_url in detail_urls:
                    try:
                        detail_flow = DetailPageFlow(driver, selenium_util)
                        detail_data = detail_flow.extract_detail(detail_url)
                        details.append(detail_data)
                        self.logger.info(f"{idx+1}行目: 詳細抽出成功: {detail_url}")
                    except Exception as e:
                        self.logger.warning(f"{idx+1}行目: 詳細抽出失敗 {detail_url}: {e}")

                # ===== スプレッドシート書き込み =====
                if details:
                    for dct in details:
                        # if isinstance(dct.get("date"), str) and dct["date"].startswith("'"):
                        #     dct["date"] = dct["date"].lstrip("'")
                        if isinstance(dct.get("date"), str):
                            dct["date"] = dct["date"].lstrip("'")

                    try:
                        output_sheet_name = self.config.DATA_OUTPUT_SHEET
                        reader = SpreadsheetReader(self.config.SPREADSHEET_ID, output_sheet_name)
                        worksheet = reader.get_worksheet(output_sheet_name)
                        flow = WriteGssFlow(worksheet)
                        flow.run(details)
                        self.logger.info(f"{idx+1}行目: 期間内URLを {len(details)} 件書き込み完了")
                    except Exception as e:
                        self.logger.error(f"{idx+1}行目: スプレッドシート書き込み失敗: {e}")
                    
                    finally:
                        # 毎行（キーワード）ごとにブラウザを確実に閉じる
                        try:
                            driver.quit()
                        except Exception:
                            pass

    # --- （任意の手動テスト用：runからは呼ばない）---
    def test_date_converter(self, sample_end_time: str) -> None:
        try:
            converted_date = DateConverter.convert(sample_end_time)
            self.logger.info(f"日付変換: 型={type(converted_date)} | 値={converted_date}")
        except Exception as e:
            self.logger.error(f"DateConverter変換テストでエラー: {e}")

    # --- （任意の手動テスト用：runからは呼ばない） ---
    def test_price_calculator(self, title: str, price: int) -> None:
        try:
            price_per_ct = PriceCalculator.calculate_price_per_carat(title, price)
            self.logger.info(f"タイトル: {title} / 落札価格: {price} → 1ct単価: {price_per_ct} 円/ct")
        except Exception as e:
            self.logger.error(f"PriceCalculatorテスト失敗: {e}")

    # --- （任意の手動テスト用：runからは呼ばない） ---
    def test_image_downloader(self) -> None:
        try:
            image_url = "https://auctions.c.yimg.jp/images.auctions.yahoo.co.jp/image/dr000/auc0106/user/5ec807c934150c37fea5b1cda6cdb4938dea1bcdd982696a3d9c90b59c549314/i-img1200x849-17500560233691ls9baa33.jpg"
            formula = ImageDownloader.get_image_formula(image_url)
            self.logger.info(f"ImageDownloaderテスト成功: {formula}")
            print(f"IMAGE式: {formula}")
        except Exception as e:
            self.logger.error("ImageDownloaderテスト失敗", exc_info=True)
            print("画像ダウンロード失敗:", e)

    # ==========================================================
    # メイン処理（本番用）

    def run(self) -> None:
        self.logger.info("プログラム開始")
        try:
            conditions = self.load_search_conditions()
            # 先読み1ページ許容（取りこぼし防止）
            self.url_and_selenium_flow_lookahead(conditions, lookahead_pages=1)
        finally:
            self.logger.info("プログラム終了")