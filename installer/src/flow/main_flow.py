# ==========================================================
# import（標準、プロジェクト内モジュール）  # ここから必要なモジュールを読み込む

import os as _os  # OS操作・環境変数参照のための標準ライブラリ（別名で衝突回避）
import logging  # ログ出力（デバッグ/情報/警告/エラー）に使用
from typing import List, Dict, Any, Optional  # 型ヒント用。関数の入出力を明確化
import pandas as pd  # 表形式データ操作用（DataFrame）
from datetime import datetime, date, time as dtime  # 日付/日時型と、日の最小時刻(dtime.min)取得に使用
import re  # 文字列のパターン置換や検索に使用
import time as pytime  # 高精度計時(perf_counter)用途で別名インポート
import time  # 待機や経過時間計測の簡易用途
from installer.src.flow.base.chrome import Chrome  # ChromeDriver生成ラッパ
from installer.src.flow.base.spreadsheet_read import SpreadsheetReader  # スプレッドシート読取ユーティリティ
from installer.src.flow.base.url_builder import UrlBuilder  # 検索URLの組み立て用
from installer.src.utils.text_utils import NumExtractor  # タイトル等から数値(ct)抽出
from installer.src.flow.base.utils import DateConverter  # 終了日表示文字列の正規化
from installer.src.flow.base.number_calculator import PriceCalculator  # 価格計算（1ct単価など）
from installer.src.flow.base.selenium_manager import Selenium  # WebDriver操作ユーティリティ
from installer.src.flow.detail_page_flow import DetailPageFlow  # 詳細ページから情報抽出するフロー
from installer.src.flow.write_gss_flow import WriteGssFlow  # GSS（Google Sheets）への書き込みフロー
from flow.base.image_downloader import ImageDownloader  # 画像式（=IMAGE(...)）生成ユーティリティ
from selenium.webdriver.common.by import By  # Seleniumのロケータ種別
from selenium.webdriver.support.ui import WebDriverWait  # 条件成立までの待機
from selenium.webdriver.support import expected_conditions as EC  # 代表的な待機条件
from dataclasses import dataclass  # 簡潔にデータ保持クラスを定義するためのデコレータ
import time as _time  # 実行時間の集計などに使う別名（衝突防止）
from installer.src.const import gss as CGSS  # GSS関連の定数
from installer.src.const import url as CURL  # URL構築関連の定数
from installer.src.const import scrape as CSCR  # スクレイピング時の定数（待機秒・セレクタ等）
from .write_gss_flow import WriteGssFlow, WriteResult  # 既存どおり  # 再インポート（相対）でIDE補完を効かせる
from installer.src.bootstrap import bootstrap  # 実行前の初期化（ログ設定/依存準備など）
from pathlib import Path  # パス操作（__file__起点での探索に使用）
    # 空行: ログ設定セクションへ切り替える区切り


# ==========================================================  # ログ設定セクション開始
# ログ設定  # モジュール専用のロガーを用意（上位でハンドラ・レベル設定想定）

logger = logging.getLogger(__name__)  # このモジュール名に紐づくロガーを取得
# 空行: データ構造定義（集計用）セクションへ


# ==========================================================
# class定義

@dataclass  # 単純な集計値保持のためのデータクラス
class CrawlStats:
    pages: int = 0  # 巡回したページ数
    added: int = 0  # 期間内として追加したURL件数
    parse_ok: int = 0  # 終了日パース成功件数
    parse_ng: int = 0  # 終了日パース失敗件数
    written: int = 0  # スプレッドシートへ書き込めた件数


# ==========================================================
# class定義

@dataclass  # ページ単位のパース統計（最小/最大日時も記録）
class ParseStats:
    ok: int = 0  # パース成功数
    ng: int = 0  # パース失敗数
    min_dt: Optional[datetime] = None  # そのページで見つかった最小日時
    max_dt: Optional[datetime] = None  # そのページで見つかった最大日時

    # ==========================================================
    # メソッド定義

    def add_success(self, dt: datetime) -> None:  # 成功時に件数とmin/maxを更新
        self.ok += 1  # 成功カウントをインクリメント
        if self.min_dt is None or dt < self.min_dt:  # 最小値更新判定
            self.min_dt = dt  # 最小日時を更新
        if self.max_dt is None or dt > self.max_dt:  # 最大値更新判定
            self.max_dt = dt  # 最大日時を更新

    # ==========================================================
    # メソッド定義

    def add_failure(self) -> None:  # 失敗件数のみ増やす
        self.ng += 1  # 失敗カウントをインクリメント


# ==========================================================
# 関数定義

def log_page_summary(page_no: int, added_count: int, total_count: int, stats: ParseStats) -> None:  # ページ単位の要約ログ
    min_s = stats.min_dt.strftime("%Y-%m-%d %H:%M:%S") if stats.min_dt else "-"  # 最小日時を文字列化（無ければ-）
    max_s = stats.max_dt.strftime("%Y-%m-%d %H:%M:%S") if stats.max_dt else "-"  # 最大日時を文字列化（無ければ-）
    logger.info(  # 情報ログとして集計を出力
        "ページ%d サマリ: 追加 %d / 累計 %d | パース 成功 %d / 失敗 %d | 最小 %s, 最大 %s",
        page_no, added_count, total_count, stats.ok, stats.ng, min_s, max_s
    )
    # 空行: 設定クラスセクションへ切り替え


# ==========================================================
# class定義

class Config:  # 実行時設定の受け口。値自体はconst側で集中管理
    # 文字列や外部仕様は const に寄せ、ここではデフォルトの「受け口」として参照する
    SPREADSHEET_ID: str = CGSS.SPREADSHEET_ID  # 対象スプレッドシートID
    SEARCH_COND_SHEET: str = CGSS.SEARCH_COND_SHEET  # 検索条件を持つシート名
    DATA_OUTPUT_SHEET: str = CGSS.DEFAULT_OUTPUT_SHEET  # 出力先の既定シート名

    HEADLESS: bool = False  # ブラウザ表示（デバッグ用）。既定は表示ON（False=非ヘッドレス）
    USER_AGENT: Optional[str] = None  # 任意のUA指定（未指定は既定）

    GOOGLE_CREDENTIALS_JSON_PATH: Optional[str] = _os.environ.get(CGSS.ENV_GOOGLE_CREDENTIALS_VAR)  # 認証JSONのパス（環境変数から）
    # 空行: メインフローのクラス定義へ


# ==========================================================
# class定義

class MainFlow:  # 全体を束ねる実行フロー（読込→検索→抽出→書込）
    """
    役割：全体の実行フロー（条件読込 → 検索 → 期間フィルタ → 詳細抽出 → GSS書込）
    """


    # ==========================================================
    # コンストラクタ

    def __init__(self, config: Config) -> None:  # 設定を受け取り、必要なハンドルを初期化
        self.config: Config = config  # 実行時設定を保持
        self.logger: logging.Logger = logger  # モジュールロガーを利用
        self._past_btn_tried: bool = False  # 「落札相場」ボタン押下を試したかのフラグ
        self.chrome: Optional[Chrome] = None  # Chromeラッパ（後で起動）
        self.driver: Optional[Any] = None  # 実体のWebDriver
        self.selenium: Optional[Selenium] = None  # Seleniumユーティリティ
        self.detail_flow: Optional[DetailPageFlow] = None  # 詳細抽出フロー

        # 空行: 補助メソッド群（環境/認証/ドライバ準備）へ


    # ==========================================================
    # メソッド定義

    def _load_env_files(self) -> None:  # .envファイル群を読み込み、未設定の環境変数を補完
        """
        .env / config/.env があれば読み込み、未設定の環境変数を注入する。
        （依存ライブラリは使わず、 KEY=VALUE の行だけ素朴に読む）
        """
        try:
            root = Path(__file__).resolve().parents[3]  # <repo-root>  # リポジトリルート推定
        except Exception:
            return  # 取得できない場合は静かにスキップ
        for env_path in (root / ".env", root / "config" / ".env"):  # 候補2箇所を順に確認
            if not env_path.exists():
                continue  # 無い場合は次へ
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():  # 1行ずつ処理
                    line = line.strip()  # 前後空白除去
                    if not line or line.startswith("#") or "=" not in line:  # 空行/コメント/無効行は飛ばす
                        continue
                    k, v = line.split("=", 1)  # KEY=VALUE を分割
                    k, v = k.strip(), v.strip()  # 余分な空白を除去
                    if k and (k not in _os.environ or _os.environ[k] == "") and v:  # 未設定時のみ反映
                        _os.environ[k] = v  # 環境変数として注入
                        self.logger.debug(f".env から注入: {k}=***")  # 値は伏せてログ
            except Exception as e:
                self.logger.debug(f".env 読み込みをスキップ: {env_path} ({e})")  # 読み込み失敗は警告せずデバッグ扱い


    # ==========================================================
    # メソッド定義

    def _ensure_google_credentials_env(self) -> None:  # Google認証情報の自動検出・設定
        """
        GOOGLE_* が何も設定されていなければ、よくある配置場所を順に探して
        GOOGLE_APPLICATION_CREDENTIALS を自動設定する。
        """
        # すでに何か設定済みなら何もしない
        if (
            _os.environ.get("GOOGLE_CREDENTIALS_JSON")
            or _os.environ.get("GOOGLE_CREDENTIALS_JSON_B64")
            or _os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        ):
            return  # 既に設定済みなので終了

        try:
            repo_root = Path(__file__).resolve().parents[3]  # <repo-root>  # ルート推定
        except Exception:
            return  # 取得不可なら何もしない

        candidates = [  # 典型的な配置パスを列挙
            repo_root / "config" / "credentials.json",                 # 推奨
            repo_root / "installer" / "config" / "credentials.json",   # 旧来
            Path(__file__).resolve().parents[2] / "config" / "credentials.json",  # installer/src/config/
        ]
        for p in candidates:
            if p.exists():  # 見つかったら
                _os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(p)  # 環境変数へ設定
                self.logger.info(f"Google認証: {p} を使用します（自動検出）")  # 採用パスを通知
                return  # 1件で十分

        self.logger.warning("Google認証ファイルが見つかりませんでした。config/credentials.json を配置するか、環境変数を設定してください。")  # 案内
        # 空行: Seleniumスタックの準備メソッドへ


    # ==========================================================
    # メソッド定義

    def _ensure_selenium_stack(self) -> None:  # Chrome/Selenium関連の初期化（怠惰ロード）
        headless: bool = getattr(self.config, "headless", getattr(self.config, "HEADLESS", False))  # ヘッドレス設定の解決
        user_agent: Optional[str] = getattr(self.config, "user_agent", getattr(self.config, "USER_AGENT", None))  # UA取得

        if getattr(self, "chrome", None) is None:  # Chromeラッパ未生成なら
            self.chrome = Chrome(headless=headless, user_agent=user_agent)  # 生成（内部でdriverも持つ）
            self.logger.info("ChromeDriverを起動しました。")  # 起動ログ

        if getattr(self, "driver", None) is None:  # driver未設定なら
            if hasattr(self.chrome, "driver"):
                self.driver = self.chrome.driver  # 属性から取得
            elif hasattr(self.chrome, "get_driver") and callable(self.chrome.get_driver):
                self.driver = self.chrome.get_driver()  # メソッドから取得
            else:
                try:
                    self.driver = Chrome.get_driver(headless=headless, user_agent=user_agent)  # 互換APIで取得
                except TypeError:
                    self.driver = Chrome.get_driver()  # 引数差異にフォールバック

        if getattr(self, "selenium", None) is None:  # Seleniumユーティリティ未生成なら
            self.selenium = Selenium(self.driver)  # ラップして利用可能に

        if getattr(self, "detail_flow", None) is None:  # 詳細抽出フロー未生成なら
            self.detail_flow = DetailPageFlow(self.driver, self.selenium)  # 依存を注入して生成


    # ==========================================================
    # メソッド定義

    def _new_driver(self) -> Any:  # 新しいWebDriverインスタンスを都度作るヘルパ
        headless: bool = getattr(self.config, "headless", getattr(self.config, "HEADLESS", False))  # ヘッドレス解決
        user_agent: Optional[str] = getattr(self.config, "user_agent", getattr(self.config, "USER_AGENT", None))  # UA解決

        try:
            chrome = Chrome(headless=headless, user_agent=user_agent)  # 一時的にChromeラッパを生成
            if hasattr(chrome, "driver"):
                return chrome.driver  # 属性からdriverを返す
            if hasattr(chrome, "get_driver") and callable(chrome.get_driver):
                return chrome.get_driver()  # 互換APIから取得
        except Exception:
            pass  # 失敗時は次の手段へ

        try:
            return Chrome.get_driver(headless=headless, user_agent=user_agent)  # 直接取得
        except TypeError:
            return Chrome.get_driver()  # 引数差異に対応


    # ==========================================================
    # メソッド定義

    def test_num_extractor(self, text: str) -> None:  # ct抽出のデバッグ用ヘルパ
        try:
            ct_value: Any = NumExtractor.extract_ct_value(text)  # 文字列からctを抽出
            self.logger.info(f"カラット抽出: 型={type(ct_value)} | 値={ct_value}")  # 結果をログ
        except Exception as e:
            self.logger.error(f"NumExtractor抽出失敗: {e}")  # 例外時ログ


    # ==========================================================
    # メソッド定義

    def load_search_conditions(self) -> List[Dict[str, Any]]:  # 検索条件をシートから取得
        # ★ 追加：.env を読み、GOOGLE_* 未設定なら既定パスを自動注入  # 必要に応じて有効化
        # self._load_env_files()  # 環境変数の読み込み
        # self._ensure_google_credentials_env()  # 認証パスの自動設定
        try:
            reader = SpreadsheetReader(  # リーダを用意（認証は内部で実施）
                spreadsheet_id=self.config.SPREADSHEET_ID,
                credentials_path=self.config.GOOGLE_CREDENTIALS_JSON_PATH,
            )
            self.reader = reader  # 後でクライアント再利用できるよう保持
            self.logger.info(f"スプレッドシート({self.config.SPREADSHEET_ID})から検索条件取得")  # 読み込み開始ログ
            conditions: List[Dict[str, Any]] = reader.get_search_conditions(self.config.SEARCH_COND_SHEET)  # 条件取得
            self.logger.info(f"取得件数: {len(conditions)}件")  # 件数を記録
            return conditions  # 条件のリストを返す
        except Exception as e:
            self.logger.error(f"スプレッドシート読込中エラー: {e}")  # 読み込み失敗
            return []  # 空で返し、以降の処理をスキップ可能に


    # ==========================================================
    # メソッド定義

    def write_test_data(self, worksheet: Any) -> None:  # 動作確認用のテストデータ書き込み
        test_data: List[Dict[str, Any]] = [  # 最小限のダミーデータ
            {
                "date": "2025-06-27",  # 終了日
                "title": "ダイヤ ルース 0.500ct 鑑定書付き",  # タイトル
                "price": 51700,  # 価格
                "ct": 0.500,  # カラット
                "1ct_price": 84100,  # 計算済み1ct単価
                "image": "https://...jpg"  # 画像URL（例）
            },
            {
                "date": "2025-06-28",
                "title": "ダイヤモンドルース 0.200ct 新品",
                "price": 20000,
                "ct": 0.200,
                "1ct_price": 32600,
                "image": "https://...jpg"
            }
        ]
        try:
            flow = WriteGssFlow(worksheet)  # 書き込みフローを作成
            flow.run(test_data)  # 一括書き込みを実行
            self.logger.info("テストデータ一括書き込み成功")  # 成功ログ
        except Exception as e:
            self.logger.error(f"テストデータ書き込み失敗: {e}")  # 失敗ログ


    # ==========================================================
    # メソッド定義

    def extract_keyword(self, row: Dict[str, Any]) -> str:  # 条件行から検索キーワードを連結生成
        return " ".join([str(row.get(f"search_{i}", "")) for i in range(1, 6)]).strip()  # search_1..5を空白区切りで連結


    # ==========================================================
    # メソッド定義

    def _resolve_output_sheet_name(self, row_index: int) -> str:  # 出力先シート名を行番号に応じて決定
        mapping = getattr(self.config, "OUTPUT_SHEETS", None)  # 明示的なマッピングがあれば優先
        if isinstance(mapping, (list, tuple)) and row_index < len(mapping):
            return str(mapping[row_index])  # 指定のシート名を使用

        base = str(getattr(self.config, "DATA_OUTPUT_SHEET", CGSS.DEFAULT_OUTPUT_SHEET)).strip()  # 既定シート名を取得

        import re as _re  # ローカルで正規表現を使用（衝突回避の別名）
        match = _re.match(r'^(.*?)(\d+)$', base)  # 末尾が数字ならインクリメント
        if match:
            prefix, num = match.groups()
            return f"{prefix}{int(num) + row_index}"  # 先頭番号を基準に行オフセットを加算

        if base.isdigit():  # 文字列全体が数字だけなら
            return str(row_index + 1)  # 行番号でシート名を割り振り

        return base  # それ以外はベース名のまま


    # ==========================================================
    # メソッド定義

    @staticmethod
    def _to_date(value: Any) -> Optional[date]:  # 任意入力をdateへ安全に変換（失敗はNone）
        if value is None or str(value).strip() == "":
            return None  # 空値は変換不可
        try:
            converted_date = DateConverter.convert(value)  # 方針に従って正規化
            if isinstance(converted_date, datetime):
                return converted_date.date()  # datetime→date
            if isinstance(converted_date, date):
                return converted_date  # 既にdate
            if hasattr(converted_date, "to_pydatetime"):
                return converted_date.to_pydatetime().date()  # pandas互換
            if hasattr(converted_date, "date") and callable(getattr(converted_date, "date")):
                extracted_date = converted_date.date()
                return extracted_date if isinstance(extracted_date, date) else None  # 安全確認
            return None  # 想定外の型
        except Exception as e:
            logger.debug(f"_to_date変換失敗: {value} ({e})")  # 失敗はデバッグログに留める
            return None  # 呼び出し側でスキップ可能に


    # ==========================================================
    # メソッド定義

    def _get_page_min_date(self, end_times: List[Any]) -> Optional[date]:  # 一覧ページの最小終了日を求める
        page_min: Optional[date] = None  # 初期値は未設定
        for end_time_value in end_times:  # 各終了日時表現を走査
            converted_date = self._to_date(end_time_value)  # date化を試行
            if converted_date is None:
                continue  # 変換不可はスキップ
            if page_min is None or converted_date < page_min:  # 最小値の更新判定
                page_min = converted_date  # 更新
        return page_min  # 最小日（無ければNone）


    # ==========================================================
    # メソッド定義

    def _page_has_no_results(self, driver: Any) -> bool:  # 0件ページかどうかのヒューリスティック判定
        try:
            page_source_html = driver.page_source or ""  # HTML文字列を取得
            if any(no_result_text in page_source_html for no_result_text in CSCR.NO_RESULT_TEXTS):  # テキストで判定
                return True  # 0件表示に一致
            for selector in CSCR.NO_RESULT_SELECTORS:  # CSSセレクタでもチェック
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if any(element.is_displayed() for element in elements):  # 表示要素があれば0件とみなす
                        return True
                except Exception:
                    pass  # セレクタ不一致は無視
            return False  # どれにも該当しない
        except Exception:
            return False  # 例外時は保守的にFalse
        # 空行: URL生成＋Selenium巡回フロー（通常版）


    # ==========================================================
    # メソッド定義

    def url_and_selenium_flow(self, conditions: List[Dict[str, Any]]) -> None:  # 条件ごとにURL生成→巡回→抽出→書込
        if not conditions:
            self.logger.warning("条件が空なのでURL生成処理スキップ")  # 入力なし
            return  # 早期終了

        conditions_df = pd.DataFrame(conditions)  # 条件をDataFrame化（列アクセス容易に）
        conditions_df = conditions_df[conditions_df["start_date"].astype(str).str.strip() != ""]  # 必須列の空値除外
        conditions_df = conditions_df[conditions_df["end_date"].astype(str).str.strip() != ""]  # 同上

        url_builder = UrlBuilder()  # URL組立ヘルパを用意

        for row_index, condition_row in conditions_df.iterrows():  # 各条件行を処理
            try:
                start_date = self._to_date(condition_row.get("start_date"))  # 開始日をdate化
                end_date = self._to_date(condition_row.get("end_date"))  # 終了日をdate化
                if start_date is None or end_date is None:
                    raise ValueError("開始/終了日の解釈に失敗")  # 不正条件
            except Exception as e:
                self.logger.error(f"{row_index+1}行目: 開始・終了日変換失敗: {e}")  # ログ出力
                continue  # 次の条件へ

            keyword = self.extract_keyword(condition_row)  # キーワード連結生成
            if not keyword:
                self.logger.warning(f"{row_index+1}行目: キーワードなし。スキップ")  # 空はスキップ
                continue

            search_url = url_builder.build_url(keyword, per_page=CURL.PER_PAGE)  # 一覧URLを構築
            self.logger.info(f"{row_index+1}行目: キーワード={keyword} | URL={search_url}")  # 情報ログ

            driver: Any = self._new_driver()  # 毎行ごとに新規ドライバ（衝突回避）
            selenium_util = Selenium(driver)  # ユーティリティ化
            page_number = 1  # ページカウンタ
            detail_urls: List[str] = []  # 期間内URLの蓄積
            seen: set[str] = set()  # 重複防止

            try:
                driver.get(search_url)  # 一覧へアクセス

                try:
                    WebDriverWait(driver, CSCR.WAIT_PAST_BTN_CLICK_SEC).until(  # 「落札相場」ボタンを待つ
                        EC.element_to_be_clickable((By.CSS_SELECTOR, CSCR.PAST_AUCTION_BUTTON_CSS))
                    ).click()  # クリック
                    self.logger.debug("落札相場ボタンをクリック")  # デバッグログ
                except Exception:
                    self.logger.debug("落札相場ボタン見つからず → スキップして続行")  # 見つからなくても続行

                while True:  # ページ送りしながら収集
                    try:
                        auction_end_times = selenium_util.get_auction_end_dates()  # 終了日時テキスト一覧
                        auction_urls = selenium_util.get_auction_urls()  # 商品URL一覧
                    except Exception as e:
                        self.logger.warning(f"{row_index+1}行目: 商品URLまたは終了日時取得失敗: {e}")  # 失敗時は打ち切り
                        break

                    items_count = min(len(auction_end_times), len(auction_urls))  # ペアの数で処理
                    added_count_in_page = 0  # そのページで追加した件数
                    parse_stats = ParseStats()  # パース統計

                    for i in range(items_count):  # 各アイテムを評価
                        auction_end_date = self._to_date(auction_end_times[i])  # date化を試行
                        if auction_end_date is None:
                            parse_stats.add_failure()  # 失敗カウント
                            continue
                        parse_stats.add_success(datetime.combine(auction_end_date, dtime.min))  # 成功＋min時刻で統一

                        if auction_end_date > end_date:
                            continue  # 終了日の上限より後→除外
                        elif auction_end_date < start_date:
                            continue  # 下限より前→除外
                        else:
                            auction_url = auction_urls[i]  # 対象期間内
                            if auction_url not in seen:  # 重複チェック
                                seen.add(auction_url)  # 記録
                                detail_urls.append(auction_url)  # 収集
                                added_count_in_page += 1  # 追加カウント

                    log_page_summary(page_number, added_count_in_page, len(detail_urls), parse_stats)  # ページ要約

                    page_min = self._get_page_min_date(auction_end_times)  # そのページの最小終了日
                    if page_min is not None and page_min < start_date:  # ページ全体が期間外へ突入したら
                        self.logger.info(
                            f"{row_index+1}行目: ページ{page_number}の最小日付 {page_min} が開始日 {start_date} より前のため巡回終了"
                        )
                        break  # 打ち切り

                    try:
                        has_next = selenium_util.click_next()  # 次ページへ
                        if not has_next:
                            self.logger.info(f"{row_index+1}行目: 次ページなし。累計 {len(detail_urls)} 件で巡回終了")  # 終了
                            break
                        page_number += 1  # ページ番号を進める
                    except Exception as e:
                        self.logger.warning(f"{row_index+1}行目: 次へクリック失敗または次ページなし: {e}")  # 例外時終了
                        break

                if not detail_urls:  # 期間内該当なし
                    self.logger.info(f"{row_index+1}行目: 対象期間内の商品なし")  # 告知
                    continue  # 次の条件へ

                detail_records: List[Dict[str, Any]] = []  # 詳細抽出結果の蓄積
                for detail_url in detail_urls:  # 各URLを詳細抽出
                    try:
                        detail_flow = DetailPageFlow(driver, selenium_util)  # 依存を注入
                        detail_record = detail_flow.extract_detail(detail_url)  # 抽出
                        detail_records.append(detail_record)  # 追加
                        self.logger.debug("%d行目: 詳細抽出成功: %s", row_index+1, detail_url)  # 成功ログ
                    except Exception as e:
                        self.logger.warning(f"{row_index+1}行目: 詳細抽出失敗 {detail_url}: {e}")  # 失敗は継続

                if detail_records:
                    try:
                        self._write_details_to_sheet(row_index, detail_records)  # 書き込み（後述メソッド想定）
                    except Exception as e:
                        self.logger.error(f"{row_index+1}行目: スプレッドシート書き込み失敗: {e}")  # 書込失敗
                else:
                    self.logger.info(f"{row_index+1}行目: 対象期間内の商品なし")  # 収集0件

            finally:
                try:
                    driver.quit()  # リソース解放
                except Exception:
                    pass  # 解放失敗は無視

        # 空行: 先読み付き巡回フロー（しきい値跨ぎ後に数ページだけ余分に巡回）


    # ==========================================================
    # メソッド定義

    def url_and_selenium_flow_lookahead(self, conditions: List[Dict[str, Any]], lookahead_pages: int = 1) -> None:  # 先読み版
        if not conditions:
            self.logger.warning("条件が空なのでURL生成処理スキップ")  # 入力なし
            return  # 早期終了

        conditions_df = pd.DataFrame(conditions)  # 条件のDataFrame化
        conditions_df = conditions_df[conditions_df["start_date"].astype(str).str.strip() != ""]  # 必須列の空除外
        conditions_df = conditions_df[conditions_df["end_date"].astype(str).str.strip() != ""]  # 同上

        url_builder = UrlBuilder()  # URL組立ヘルパ生成

        for row_index, condition_row in conditions_df.iterrows():  # 条件ごとに処理
            try:
                start_date = self._to_date(condition_row.get("start_date"))  # 開始日をdate化
                end_date = self._to_date(condition_row.get("end_date"))  # 終了日をdate化
                if start_date is None or end_date is None:
                    raise ValueError("開始/終了日の解釈に失敗")  # 不正
            except Exception as e:
                self.logger.error(f"{row_index+1}行目: 開始・終了日変換失敗: {e}")  # ログ
                continue  # 次へ

            keyword = self.extract_keyword(condition_row)  # キーワードを連結
            if not keyword:
                self.logger.warning(f"{row_index+1}行目: キーワードなし。スキップ")  # 空はスキップ
                continue

            search_url = url_builder.build_url(keyword, per_page=CURL.PER_PAGE)  # 一覧URL構築
            self.logger.info(f"{row_index+1}行目: キーワード={keyword} | URL={search_url}")  # 情報ログ

            start_time = _time.time()  # 計測開始
            crawl_stats = CrawlStats()  # 集計用

            driver: Any = None  # 後でfinallyでquitするために先に宣言
            try:
                driver = self._new_driver()  # 新規ドライバ
                selenium_util = Selenium(driver)  # ユーティリティ
                page_number = 1  # ページ番号
                detail_urls: List[str] = []  # 対象URL蓄積
                seen: set[str] = set()  # 重複防止
                extra_pages_left = int(lookahead_pages) if lookahead_pages and int(lookahead_pages) > 0 else 0  # 先読み残数
                crossed_threshold = False  # しきい値（開始日未満）を既に跨いだか

                driver.get(search_url)  # 一覧へ遷移
                try:
                    WebDriverWait(driver, CSCR.WAIT_DOC_READY_SEC).until(  # DOM完成待ち
                        lambda d: d.execute_script("return document.readyState") == "complete"
                    )
                except Exception:
                    pass  # 待機失敗は致命的でない

                if driver.current_url.startswith("data:"):  # 稀にdata:URLになる場合の再ナビゲーション
                    self.logger.debug("current_url が data: のため再ナビゲーションを実施")
                    driver.get(search_url)

                # 落札相場ボタン（あれば）  # JSクリックで確実に押下を試みる
                try:
                    past_btn = WebDriverWait(driver, 1).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, CSCR.PAST_AUCTION_BUTTON_CSS))
                    )
                    try:
                        driver.execute_script("arguments[0].click();", past_btn)  # JS経由クリック（覆い被さり対策）
                        self.logger.debug("落札相場ボタン(JS)クリック")
                        WebDriverWait(driver, 1).until(  # 画面変化を軽く待つ
                            EC.any_of(
                                EC.presence_of_element_located((By.CSS_SELECTOR, ".Auc")),
                                EC.url_contains("closedsearch")
                            )
                        )
                    except Exception as e:
                        self.logger.debug(f"落札相場ボタンのクリック処理失敗（無視して続行）: {e}")
                except Exception:
                    self.logger.debug("落札相場ボタン見つからず → スキップして続行")

                # 一覧巡回  # ページを送りながらURL/日時を収集・フィルタ
                while True:
                    try:
                        auction_end_times = selenium_util.get_auction_end_dates()  # 終了日時候補
                        auction_urls = selenium_util.get_auction_urls()  # 対応する商品URL
                    except Exception as e:
                        self.logger.warning(f"{row_index+1}行目: 商品URLまたは終了日時取得失敗: {e}")  # 取得失敗
                        break  # ページ巡回終了

                    items_count = min(len(auction_end_times), len(auction_urls))  # ペア件数
                    added_count_in_page = 0  # ページ内追加数
                    page_parse_success_count = 0  # パース成功数
                    page_parse_failure_count = 0  # パース失敗数

                    for i in range(items_count):  # 各行を評価
                        auction_end_date = self._to_date(auction_end_times[i])  # date化
                        if auction_end_date is None:
                            page_parse_failure_count += 1  # 失敗
                            continue
                        page_parse_success_count += 1  # 成功

                        if auction_end_date > end_date:
                            continue  # 上限を超える
                        elif auction_end_date < start_date:
                            continue  # 下限を下回る
                        else:
                            auction_url = auction_urls[i]  # 期間内
                            if auction_url not in seen:  # 未収集なら
                                seen.add(auction_url)  # 記録
                                detail_urls.append(auction_url)  # 保存
                                added_count_in_page += 1  # カウント

                    # 集計
                    crawl_stats.pages += 1  # ページ+1
                    crawl_stats.added += added_count_in_page  # 追加件数累計
                    crawl_stats.parse_ok += page_parse_success_count  # パース成功累計
                    crawl_stats.parse_ng += page_parse_failure_count  # パース失敗累計

                    self.logger.debug(  # ページ要約（デバッグ）
                        "ページ%d サマリ: 追加 %d / 累計 %d | パース 成功 %d / 失敗 %d",
                        page_number, added_count_in_page, len(detail_urls),
                        page_parse_success_count, page_parse_failure_count
                    )

                    # 0件ページの打ち切り  # 何も取れないページが続く場合の早期終了
                    if items_count == 0:
                        if self._page_has_no_results(driver):  # 明示の0件表示なら即終了
                            self.logger.info(f"{row_index+1}行目: 条件に一致する商品は見つかりませんでした（ページ{page_number}）。巡回終了")
                            break
                        empty_pages_in_a_row = locals().get("empty_pages_in_a_row", 0) + 1  # 連続カウント
                        locals()["empty_pages_in_a_row"] = empty_pages_in_a_row  # ローカル辞書で簡易保持
                        if empty_pages_in_a_row >= 3:  # 3連続で0件なら終了
                            self.logger.warning(f"{row_index+1}行目: 空ページが{empty_pages_in_a_row}連続。巡回終了")
                            break
                    else:
                        locals()["empty_pages_in_a_row"] = 0  # 連続カウントをリセット

                    # 閾値跨ぎ→先読み  # ページの最小日が開始日未満になった後は「少しだけ」先を読む
                    page_min_date = self._get_page_min_date(auction_end_times)  # ページ最小日
                    if page_min_date is not None and page_min_date < start_date:
                        if not crossed_threshold:  # 初回跨ぎ時に通知
                            crossed_threshold = True
                            self.logger.debug(
                                f"{row_index+1}行目: ページ{page_number}の最小日付 {page_min_date} が開始日 {start_date} より前 → "
                                f"先読みを {extra_pages_left} ページ許容"
                            )
                        if extra_pages_left <= 0:  # 先読み残数が尽きたら終了
                            self.logger.debug(
                                f"{row_index+1}行目: 先読み許容量を使い切ったため巡回終了（累計 {len(detail_urls)} 件）"
                            )
                            break
                        extra_pages_left -= 1  # 残数をデクリメント
                        self.logger.debug(
                            f"{row_index+1}行目: 閾値跨ぎ後の先読み継続。残り先読みページ数: {extra_pages_left}"
                        )

                    # URLのパラメータを書き換えてページ送り（const使用）  # b= と n= を指定してジャンプ
                    try:
                        per_page = CURL.PER_PAGE  # 1ページ件数
                        next_b = (page_number * per_page) + 1  # 次ページ先頭位置
                        current_url = driver.current_url  # 現在URL

                        # 既存の b= / n= を除去  # 二重指定を避けるために一旦消す
                        base_url = re.sub(rf"([?&]){CURL.PARM_PAGE_OFFSET if hasattr(CURL,'PARM_PAGE_OFFSET') else CURL.PARAM_PAGE_OFFSET}=\d+", r"\1", current_url)
                        base_url = re.sub(rf"([?&]){CURL.PARAM_PER_PAGE}=\d+", r"\1", base_url)
                        if base_url.endswith("?") or base_url.endswith("&"):
                            base_url = base_url[:-1]  # 末尾の余分な区切りを除去
                        query_separator = "&" if "?" in base_url else "?"  # 最初の区切り記号を決定
                        next_url = f"{base_url}{query_separator}{CURL.PARAM_PAGE_OFFSET}={next_b}&{CURL.PARAM_PER_PAGE}={per_page}"  # 次URL

                        nav_start_time = pytime.perf_counter()  # ナビ開始時刻
                        driver.get(next_url)  # 遷移
                        WebDriverWait(driver, CSCR.WAIT_NEXT_PAGE_SEC).until(lambda d: f"{CURL.PARAM_PAGE_OFFSET}={next_b}" in d.current_url)  # URL変化待ち
                        self.logger.debug("URLジャンプで次ページへ: %s=%d（%.2f秒）",
                            CURL.PARAM_PAGE_OFFSET, next_b, pytime.perf_counter() - nav_start_time)  # 所要時間ログ
                        page_number += 1  # ページ番号更新
                    except Exception as e:
                        self.logger.info(f"{row_index+1}行目: 次ページなし/遷移失敗のため終了: {e}")  # ここで巡回終了
                        break

                if not detail_urls:  # 期間内0件
                    self.logger.info(f"{row_index+1}行目: 対象期間内の商品なし")  # 通知
                    continue  # 次の条件へ

                # 詳細抽出  # 期間内URLを詳細ページで精査
                detail_records: List[Dict[str, Any]] = []  # 抽出結果を保持
                for detail_url in detail_urls:  # 各URLを処理
                    try:
                        detail_flow = DetailPageFlow(driver, selenium_util)  # 詳細抽出フローを生成
                        detail_record = detail_flow.extract_detail(detail_url)  # 情報抽出
                        detail_records.append(detail_record)  # 蓄積
                        self.logger.debug(f"{row_index+1}行目: 詳細抽出成功: {detail_url}")  # 成功ログ
                    except Exception as e:
                        self.logger.warning(f"{row_index+1}行目: 詳細抽出失敗 {detail_url}: {e}")  # 失敗しても続行

                if detail_records:  # 1件以上あれば書き込みへ
                    default_ws_name = str(self._resolve_output_sheet_name(row_index))  # 既定WS名
                    ws_name_from_master = str(condition_row.get("ws_name") or default_ws_name).strip() or default_ws_name  # マスター優先
                    for detail_record in detail_records:
                        detail_record["ws_name"] = ws_name_from_master  # 出力先シート名を付加
                        detail_record["check"] = condition_row.get("check", True)  # フラグ類も踏襲

                    try:
                        # 既定のタブ名（Master の ws_name 未指定時に使う）
                        output_sheet_name = self._resolve_output_sheet_name(row_index)

                        # 実際に書き込まれるタブ名を、レコードの ws_name と既定から解決して集計表示
                        from collections import Counter
                        _ws_names: list[str] = []
                        for r in detail_records:
                            raw = r.get("ws_name")
                            name = str(raw).strip() if raw not in (None, "") else str(output_sheet_name)
                            if name in ("nan", "None", ""):
                                name = str(output_sheet_name)
                            _ws_names.append(name)
                        ws_counts = Counter(_ws_names)
                        if len(ws_counts) == 1:
                            self.logger.debug(f"出力WS: {next(iter(ws_counts))}（default={output_sheet_name}）")
                        else:
                            self.logger.debug(f"出力WS: {dict(ws_counts)}（default={output_sheet_name}）")

                        # gspread クライアントは可能なら既存を再利用
                        if getattr(self, "reader", None) is not None and hasattr(self.reader, "_get_client"):
                            gc_client = self.reader._get_client()
                        else:
                            tmp_reader = SpreadsheetReader(self.config.SPREADSHEET_ID, str(output_sheet_name))
                            gc_client = tmp_reader._get_client()
                            if getattr(self, "reader", None) is None:
                                self.reader = tmp_reader

                        # 書き込みフローを準備（ws_name ごとのルーティングは WriteGssFlow 側で実施）
                        writer = WriteGssFlow(
                            gc=gc_client,
                            spreadsheet_id=self.config.SPREADSHEET_ID,
                            default_title=str(output_sheet_name),
                        )

                        # 実書き込み
                        write_result = writer.write(detail_records)

                        # 結果ログと集計更新
                        self.logger.info(
                            f"{row_index+1}行目: 期間内URLを書き込み完了: 書込み={write_result.written}, 重複スキップ={write_result.skipped}"
                        )
                        crawl_stats.written = write_result.written
                    except Exception as e:
                        self.logger.error(f"{row_index+1}行目: スプレッドシート書き込み失敗: {e}")

            finally:
                try:
                    if driver is not None:
                        driver.quit()  # ドライバ終了
                except Exception:
                    pass  # 終了失敗は無視

                self.logger.info(  # 条件1件分の総括をログ
                    "集計: キーワード='%s' | ページ=%d | 期間内URL=%d | パース 成功=%d 失敗=%d | 書込み=%d | %.2fs",
                    keyword, crawl_stats.pages, crawl_stats.added,
                    crawl_stats.parse_ok, crawl_stats.parse_ng,
                    crawl_stats.written, _time.time() - start_time
                )
        # 空行: テスト用の小さなユーティリティ群


    # ==========================================================
    # メソッド定義

    def test_date_converter(self, sample_end_time_str: str) -> None:  # DateConverterのテスト
        try:
            converted_date_obj: Any = DateConverter.convert(sample_end_time_str)  # 文字列→date変換
            self.logger.info(f"日付変換: 型={type(converted_date_obj)} | 値={converted_date_obj}")  # 結果ログ
        except Exception as e:
            self.logger.error(f"DateConverter変換テストでエラー: {e}")  # 失敗ログ


    # ==========================================================
    # メソッド定義

    def test_price_calculator(self, title: str, price: int) -> None:  # PriceCalculatorのテスト
        try:
            price_per_carat_jpy: Any = PriceCalculator.calculate_price_per_carat(title, price)  # タイトルからct抽出→単価算出
            self.logger.info(f"タイトル: {title} / 落札価格: {price} → 1ct単価: {price_per_carat_jpy} 円/ct")  # 結果ログ
        except Exception as e:
            self.logger.error(f"PriceCalculatorテスト失敗: {e}")  # 失敗ログ


    # ==========================================================
    # メソッド定義

    def test_image_downloader(self) -> None:  # IMAGE式生成のテスト
        try:
            sample_image_url = "https://auctions.c.yimg.jp/images.auctions.yahoo.co.jp/image/dr000/auc0106/user/5ec807c934150c37fea5b1cda6cdb4938dea1bcdd982696a3d9c90b59c549314/i-img1200x849-17500560233691ls9baa33.jpg"  # サンプルURL
            image_formula = ImageDownloader.get_image_formula(sample_image_url)  # =IMAGE(...) 文字列を生成
            self.logger.info(f"ImageDownloaderテスト成功: {image_formula}")  # 成功ログ
            print(f"IMAGE式: {image_formula}")  # 目視確認用
        except Exception as e:
            self.logger.error("ImageDownloaderテスト失敗", exc_info=True)  # 例外スタックも出力
            print("画像ダウンロード失敗:", e)  # コンソールにも表示
        # 空行: 実行エントリポイント


    # ==========================================================
    # メソッド定義

    def run(self) -> None:  # 全体の実行手順（起動前処理→条件取得→巡回）
        # ★ 起動前処理（ログ・認証など）を冪等に一度だけ実施
        bootstrap(debug=True)  # 初期化処理（開発時はdebug=Trueで詳細ログ）
        self.logger.info("MainFlow started")  # 開始ログ
        self.logger.info("プログラム開始")  # 追加開始ログ
        try:
            conditions = self.load_search_conditions()  # 検索条件を取得
            self.url_and_selenium_flow_lookahead(conditions, lookahead_pages=1)  # 先読み1ページで巡回実行
        finally:
            self.logger.info("プログラム終了")  # 終了ログ（成功/失敗に関わらず実行）
