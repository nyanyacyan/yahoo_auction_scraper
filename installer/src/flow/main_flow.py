# ==========================================================
# import（標準、プロジェクト内モジュール）

import os as _os  # os を別名 _os で使用（環境変数取得などに使う）
import logging  # ログ出力（進捗・デバッグ・エラー）
from typing import List, Dict, Any, Optional  # 型ヒント（可読性・保守性UP）
import pandas as pd  # 表形式データ処理
from datetime import datetime, date, time as dtime  # 日付・時刻型
import re  # URL書き換え等で使用
import time as pytime  # 計測用（経過秒）
import time  # 時刻取得やsleep等の基本的な時間処理
from installer.src.flow.base.chrome import Chrome  # WebDriver供給（プロジェクト内ラッパ）
from installer.src.flow.base.spreadsheet_read import SpreadsheetReader  # GSS読取
from installer.src.flow.base.url_builder import UrlBuilder  # 検索URL生成
from installer.src.utils.text_utils import NumExtractor  # 文字列→数値抽出（ctなど）
from installer.src.flow.base.utils import DateConverter  # 多様な日付表記の正規化
from installer.src.flow.base.number_calculator import PriceCalculator  # 1ct単価計算
from installer.src.flow.base.selenium_manager import Selenium  # Seleniumユーティリティ（要素取得等）
from installer.src.flow.detail_page_flow import DetailPageFlow  # 詳細ページ抽出フロー
from installer.src.flow.write_gss_flow import WriteGssFlow  # GSS書き込みフロー
from flow.base.image_downloader import ImageDownloader  # 画像式生成ユーティリティ
from selenium.webdriver.common.by import By  # 要素指定に使う定数
from selenium.webdriver.support.ui import WebDriverWait  # 明示的待機
from selenium.webdriver.support import expected_conditions as EC  # 待機条件
from dataclasses import dataclass  # 軽量データ構造
import time as _time  # 統計などの経過時間計測用に別名でtimeを使用



# ==========================================================
# ログ設定

logger = logging.getLogger(__name__)  # このモジュール専用ロガー



# ==========================================================
# データ構造class定義

@dataclass  # データ保持用の簡素なクラスを自動生成
class CrawlStats:  # キーワード単位の集計（ページ数、追加URL数など）を持つ
    pages: int = 0  # 処理したページ数
    added: int = 0  # 期間内として追加したURL件数
    parse_ok: int = 0  # 終了日時の解釈（パース）に成功した件数
    parse_ng: int = 0  # 終了日時の解釈に失敗した件数
    written: int = 0  # スプレッドシートに書き込んだ件数



# ==========================================================
# データ構造class定義

@dataclass  # データ専用クラスを簡潔に定義するデコレータ
class ParseStats:  # 1ページ内でのパース成功/失敗や時刻範囲を記録
    # 1ページ内のパース結果統計を保持する簡易構造体
    ok: int = 0   # パース成功件数
    ng: int = 0   # パース失敗件数
    min_dt: Optional[datetime] = None  # そのページ内の最小日時
    max_dt: Optional[datetime] = None  # そのページ内の最大日時



    # ==========================================================
    # メソッド定義

    def add_success(self, dt: datetime) -> None:  # 成功時に件数・最小/最大の更新を行う
        # 成功件数を加算し、最小・最大日時を更新
        self.ok += 1  # 成功件数を1増やす
        if self.min_dt is None or dt < self.min_dt:  # 既存の最小より小さければ更新
            self.min_dt = dt  # 最小日時を更新
        if self.max_dt is None or dt > self.max_dt:  # 既存の最大より大きければ更新
            self.max_dt = dt  # 最大日時を更新



    # ==========================================================
    # メソッド定義

    def add_failure(self) -> None:  # 失敗時に件数のみ加算
        # 失敗件数を加算
        self.ng += 1  # 失敗件数を1増やす



# ==========================================================
# 関数定義

def log_page_summary(page_no: int, added_count: int, total_count: int, stats: ParseStats) -> None:  # ページの集計結果をINFOで記録
    # 1ページ処理の集計を人間が読みやすい形でログ出力
    min_s = stats.min_dt.strftime("%Y-%m-%d %H:%M:%S") if stats.min_dt else "-"  # 最小日時を文字列に（なければ-）
    max_s = stats.max_dt.strftime("%Y-%m-%d %H:%M:%S") if stats.max_dt else "-"  # 最大日時を文字列に（なければ-）
    logger.info(  # 集計情報を整形して出力
        "ページ%d サマリ: 追加 %d / 累計 %d | パース 成功 %d / 失敗 %d | 最小 %s, 最大 %s",
        page_no, added_count, total_count, stats.ok, stats.ng, min_s, max_s
    )



# ==========================================================
# class定義

class Config:  # 動作に関する設定値をまとめるクラス
    # 設定値の置き場（外部I/O仕様はここに集約）
    SPREADSHEET_ID = "1nRJh0BqQazHe8qgT2YTZbMaZ9osPX835CbM3KkUjkcE"  # 参照するスプレッドシートID
    SEARCH_COND_SHEET = "Master"  # 検索条件を記載したシート名
    DATA_OUTPUT_SHEET = "1"  # 出力先シート名
    HEADLESS = False  # ヘッドレス起動フラグ
    USER_AGENT = None  # カスタムUAが必要な場合に設定
    GOOGLE_CREDENTIALS_JSON_PATH = _os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")  # 認証ファイルパス（環境変数から取得）



# ==========================================================
# class定義

class MainFlow:  # 主要な実行手順を統括するクラス
    """
    役割：全体の実行フローを司るオーケストレーター。
    1) 条件の読込 → 2) 検索 → 3) 対象期間フィルタ → 4) 詳細抽出 → 5) GSS書込
    """  # クラス全体の説明。実行には影響しない。

    # ==========================================================
    # メソッド定義

    def __init__(self, config: Config):  # 構成情報を受け取って初期化
        self.config = config  # 実行時の設定
        self.logger = logger  # モジュールロガーを別名で保持
        self._past_btn_tried = False  # 「落札相場」ボタン押下を試したかのフラグ（将来拡張用？）



    # ==========================================================
    # メソッド定義

    def _ensure_selenium_stack(self) -> None:  # Selenium/Chrome関連オブジェクトを遅延初期化
        # Selenium周り（Chromeラッパ・WebDriver・ユーティリティ）を遅延初期化
        headless = getattr(self.config, "headless", getattr(self.config, "HEADLESS", False))  # 設定からヘッドレス指定を取得
        user_agent = getattr(self.config, "user_agent", getattr(self.config, "USER_AGENT", None))  # UA設定を取得

        if self.chrome is None:  # Chromeラッパ未生成なら
            self.chrome = Chrome(headless=headless, user_agent=user_agent)  # プロジェクト独自のChromeラッパ想定
            self.logger.info("ChromeDriverを起動しました。")  # 起動をINFOで通知

        if self.driver is None:  # WebDriver未保持なら
            # Chromeラッパの実装差異（get_driver/driver属性）に幅広く対応
            if hasattr(self.chrome, "get_driver") and callable(self.chrome.get_driver):  # get_driverメソッドがある場合
                self.driver = self.chrome.get_driver()  # メソッド経由で取得
            elif hasattr(self.chrome, "driver"):  # driver属性がある場合
                self.driver = self.chrome.driver  # 属性から取得
            else:  # いずれもない場合
                try:
                    self.driver = Chrome.get_driver()  # クラスメソッドで取得を試みる
                except TypeError:  # 取得失敗時
                    # ラッパ側の仕様不足を明確なメッセージで通知
                    raise AttributeError(
                        "Chrome から WebDriver を取得できません。"
                        "get_driver() または driver 属性を実装してください。"
                    )

        if self.selenium is None:  # Seleniumユーティリティ未生成なら
            self.selenium = Selenium(self.driver)  # 要素取得等の共通処理

        if self.detail_flow is None:  # 詳細抽出フロー未生成なら
            self.detail_flow = DetailPageFlow(self.driver, self.selenium)  # 詳細抽出フロー



    # ==========================================================
    # メソッド定義

    def test_num_extractor(self, text: str) -> None:  # カラット抽出ユーティリティの動作確認
        # NumExtractorの動作確認ログ（例外は握りつぶさずログ）
        try:
            ct_value = NumExtractor.extract_ct_value(text)  # 文字列からct値を抽出
            self.logger.info(f"カラット抽出: 型={type(ct_value)} | 値={ct_value}")  # 抽出結果をINFOで表示
        except Exception as e:  # 例外発生時
            self.logger.error(f"NumExtractor抽出失敗: {e}")  # エラー内容をログ



    # ==========================================================
    # メソッド定義

    def load_search_conditions(self) -> List[Dict[str, Any]]:  # GSSから検索条件を読み込む
        """GSSから検索条件（開始日/終了日/キーワード群など）を取得"""  # 関数の目的を簡潔に説明
        try:
            reader = SpreadsheetReader(  # スプレッドシート読み取り用インスタンスを作成
                spreadsheet_id=self.config.SPREADSHEET_ID,  # 対象のスプレッドシートID
                credentials_path=self.config.GOOGLE_CREDENTIALS_JSON_PATH,  # 認証情報のパス（環境変数から）
            )
            self.logger.info(f"スプレッドシート({self.config.SPREADSHEET_ID})から検索条件取得")  # 取得開始をINFOで通知
            conditions: List[Dict[str, Any]] = reader.get_search_conditions("Master")  # ← 1回だけ  # 指定シートから条件取得
            self.logger.info(f"取得件数: {len(conditions)}件")  # 件数を記録
            return conditions  # 取得した条件を返す
        except Exception as e:  # 読み込み時のエラー処理
            self.logger.error(f"スプレッドシート読込中エラー: {e}")  # エラー内容を出力
            return []  # 失敗時は空配列を返して上位で判断させる



    # ==========================================================
    # メソッド定義

    def write_test_data(self, worksheet) -> None:  # 動作確認用にダミーデータを書き込む
        # GSS書込の動作検証用ダミーデータ（本番処理とは独立）
        test_data = [  # スプレッドシートに書き込む想定のレコード例
            {
                "date": "2025-06-27",  # 日付
                "title": "ダイヤ ルース 0.500ct 鑑定書付き",  # タイトル
                "price": 51700,  # 価格
                "ct": 0.500,  # カラット数
                "1ct_price": 84100,  # 1ct単価
                "image": "https://auctions.c.yimg.jp/images.auctions.yahoo.co.jp/image/dr000/auc0106/user/5ec807c934150c37fea5b1cda6cdb4938dea1bcdd982696a3d9c90b59c549314/i-img1200x849-17500560233691ls9baa33.jpg"  # 画像URL
            },
            {
                "date": "2025-06-28",  # 日付
                "title": "ダイヤモンドルース 0.200ct 新品",  # タイトル
                "price": 20000,  # 価格
                "ct": 0.200,  # カラット数
                "1ct_price": 32600,  # 1ct単価
                "image": "https://auctions.c.yimg.jp/images.auctions.yahoo.co.jp/image/dr000/auc0106/user/5ec807c934150c37fea5b1cda6cdb4938dea1bcdd982696a3d9c90b59c549314/i-img1200x849-17500560233691ls9baa33.jpg"  # 画像URL
            }
        ]
        try:
            flow = WriteGssFlow(worksheet)  # 書き込みフローを生成
            flow.run(test_data)  # テストデータを一括書き込み
            self.logger.info("テストデータ一括書き込み成功")  # 成功ログ
        except Exception as e:  # 書き込み失敗時
            self.logger.error(f"テストデータ書き込み失敗: {e}")  # エラーをログ



    # ==========================================================
    # メソッド定義

    def extract_keyword(self, row: Dict[str, Any]) -> str:  # search_1〜5を結合して検索語を作成
        # search_1〜search_5 を空白結合してキーワード作成（空は無視）
        return " ".join([str(row.get(f"search_{i}", "")) for i in range(1, 6)]).strip()  # 連結後に前後空白を除去













    # ==========================================================
    # メソッド定義

    def _resolve_output_sheet_name(self, row_index: int) -> str:
        """
        行インデックス(0始まり)に応じて書き込み先WS名を返す。
        優先順:
        1) Config.OUTPUT_SHEETS があればそのマップ（例: ["1","2"] / ["WS1","WS2"]）
        2) Config.DATA_OUTPUT_SHEET が末尾数字を持てば +row_index で連番化（"1"→"2"...／"WS1"→"WS2"...）
        3) 上記以外は row_index+1 を文字列化（"1","2",...）
        """
        mapping = getattr(self.config, "OUTPUT_SHEETS", None)
        if isinstance(mapping, (list, tuple)) and row_index < len(mapping):
            return str(mapping[row_index])

        base = str(getattr(self.config, "DATA_OUTPUT_SHEET", "1")).strip()

        # 末尾に数字があれば連番化（例: "1"→"2"…／"WS1"→"WS2"…）
        import re
        m = re.match(r'^(.*?)(\d+)$', base)
        if m:
            prefix, num = m.groups()
            return f"{prefix}{int(num) + row_index}"

        # 数値だけなら行番号ベース
        if base.isdigit():
            return str(row_index + 1)

        # それ以外は常に base（=固定名）
        return base











    # ==========================================================
    # 静的メソッド（インスタンス化不要で利用可能）

    @staticmethod  # インスタンス外からユーティリティ的に使うためstaticmethod
    def _to_date(value):  # 任意の値をdate型に寄せる（失敗時はNone）
        # 受け取った値を date に寄せる小ユーティリティ（厳格エラーではなく None を返す）
        if value is None or str(value).strip() == "":  # 空値はそのままNoneを返す
            return None  # 値なしを示す
        try:
            d = DateConverter.convert(value)  # まずは共通の変換器に委譲
            if isinstance(d, datetime):  # datetimeなら
                return d.date()  # date部分に変換
            if isinstance(d, date):  # 既にdateなら
                return d  # そのまま返す
            if hasattr(d, "to_pydatetime"):  # Pandas Timestampなどの対応
                return d.to_pydatetime().date()  # Python datetimeへ変換してdate取り出し
            if hasattr(d, "date") and callable(getattr(d, "date")):  # date()メソッドを持つオブジェクト対応
                dd = d.date()  # dateを取得
                return dd if isinstance(dd, date) else None  # date型なら返す
            return None  # ここまでで判定不能ならNone
        except Exception as e:  # 変換エラー時
            logger.debug(f"_to_date変換失敗: {value} ({e})")  # デバッグログに残す
            return None  # 失敗は呼び出し元でスキップ判断



    # ==========================================================
    # メソッド定義

    def _get_page_min_date(self, end_times: list) -> "date | None":  # 終了日時文字列の配列から最小日付を求める
        # そのページで取得した終了日時（文字列群）から最小日付を求める
        page_min: Optional[date] = None  # 初期値なし
        for v in end_times:  # 各終了時刻文字列を走査
            d = self._to_date(v)  # 文字列をdateに寄せる
            if d is None:  # 変換失敗は無視
                continue  # 次へ
            if page_min is None or d < page_min:  # より小さい日付なら更新
                page_min = d  # 最小値を更新
        return page_min  # 見つかった最小日付（なければNone）



    # ==========================================================
    # メソッド定義

    def _page_has_no_results(self, driver) -> bool:  # ページに「該当なし」表示があるかを検出する
        # 検索結果0件の判定（文言 or DOM構造）。UI変化に弱い点に注意。
        try:
            phrases = (  # 文言ベースの判定候補
                "条件に一致する商品は見つかりませんでした",
                "該当する商品はありません",
                "該当するオークションはありません",
            )
            src = driver.page_source or ""  # ページHTMLを取得
            if any(p in src for p in phrases):  # いずれかの文言が含まれているか
                return True  # 0件とみなす

            selectors = [  # DOM構造ベースの判定候補
                ".Module__noResult",
                ".NoResult",
                "#NoResult",
                ".Search__noItems",
            ]
            for css in selectors:  # CSSセレクタごとに探索
                try:
                    els = driver.find_elements(By.CSS_SELECTOR, css)  # 要素群を取得
                    if any(e.is_displayed() for e in els):  # 表示されていれば0件UIと判断
                        return True  # 0件
                except Exception:  # セレクタエラー等は無視
                    pass  # 次のセレクタへ

            return False  # どれにも当てはまらなければ0件ではない
        except Exception:  # 予期せぬ例外時
            return False  # 例外時は保守的に「結果あり」とみなす



    # ==========================================================
    # メソッド定義

    def url_and_selenium_flow(self, conditions: List[Dict[str, Any]]) -> None:  # 先読みなしの基本巡回
        # 旧ロジック：先読みなしの巡回。基本のページ送り〜詳細抽出〜書き込みまで。
        if not conditions:  # 条件が空なら処理しない
            self.logger.warning("条件が空なのでURL生成処理スキップ")  # 警告ログ
            return  # 関数を終了

        df = pd.DataFrame(conditions)  # 条件をDataFrame化
        # 開始・終了日が空の行は除外（事前に最小限の整形）
        df = df[df["start_date"].astype(str).str.strip() != ""]  # start_dateが空でない行に限定
        df = df[df["end_date"].astype(str).str.strip() != ""]  # end_dateが空でない行に限定

        url_builder = UrlBuilder()  # 検索URL生成ユーティリティ

        for idx, row in df.iterrows():  # 各条件行を処理
            try:
                start_date = self._to_date(row.get("start_date"))  # 開始日をdateに
                end_date   = self._to_date(row.get("end_date"))  # 終了日をdateに
                if start_date is None or end_date is None:  # どちらか判定不能なら
                    raise ValueError("開始/終了日の解釈に失敗")  # エラーを投げる
            except Exception as e:  # 例外発生時
                self.logger.error(f"{idx+1}行目: 開始・終了日変換失敗: {e}")  # 行番号付きで記録
                continue  # 次の行へ

            keyword = self.extract_keyword(row)  # キーワード連結
            if not keyword:  # 空なら
                self.logger.warning(f"{idx+1}行目: キーワードなし。スキップ")  # スキップを通知
                continue  # 次の行へ

            search_url = url_builder.build_url(keyword, per_page=100)  # 検索URL生成
            self.logger.info(f"{idx+1}行目: キーワード={keyword} | URL={search_url}")  # INFOログ

            driver = Chrome.get_driver()  # 毎行で新規起動（コスト高だが仕様に従う）
            selenium_util = Selenium(driver)  # Selenium補助
            page_no = 1  # ページ番号
            detail_urls: List[str] = []  # 詳細ページURLの蓄積
            seen: set[str] = set()  # 重複防止用セット

            try:
                driver.get(search_url)  # 検索ページに遷移

                # 「落札相場」ボタンがあれば押す（クローズド検索に遷移させる意図）
                try:
                    WebDriverWait(driver, 5).until(  # クリック可能になるまで待機
                        EC.element_to_be_clickable((By.CSS_SELECTOR, ".Auction__pastAuctionBtn"))
                    ).click()  # クリック実行
                    self.logger.debug("落札相場ボタンをクリック")  # DEBUGログ
                except Exception as e:  # クリック失敗時
                    self.logger.warning(f"落札相場ボタン押下失敗: {e}")  # 警告ログ

                while True:  # 一覧ページの巡回ループ
                    # 一覧から終了日時テキスト群と商品URL群を収集
                    try:
                        end_times = selenium_util.get_auction_end_dates()  # 終了日時群
                        urls      = selenium_util.get_auction_urls()  # 詳細URL群
                    except Exception as e:  # 取得失敗時
                        self.logger.warning(f"{idx+1}行目: 商品URLまたは終了日時取得失敗: {e}")  # 警告
                        break  # 現在のキーワード巡回を終了

                    n = min(len(end_times), len(urls))  # ペアとして扱える件数
                    added_this_page = 0  # 今ページで追加できた件数
                    stats = ParseStats()  # ページ内統計

                    # 期間フィルタ：start_date <= d <= end_date のものだけ採用
                    for i in range(n):  # 各要素をチェック
                        d = self._to_date(end_times[i])  # 日付に寄せる
                        if d is None:  # 失敗時
                            stats.add_failure()  # 失敗カウント
                            continue  # 次へ
                        stats.add_success(datetime.combine(d, dtime.min))  # 成功として統計更新

                        if d > end_date:  # 新しすぎる（先のページほど古い想定）
                            continue  # スキップ
                        elif d < start_date:  # 古すぎる
                            continue  # スキップ
                        else:  # 期間内
                            u = urls[i]  # 対応URL
                            if u not in seen:  # 未収集なら
                                seen.add(u)  # 重複防止に追加
                                detail_urls.append(u)  # 詳細収集対象に追加
                                added_this_page += 1  # 追加数を加算

                    log_page_summary(page_no, added_this_page, len(detail_urls), stats)  # ページ要約を出力

                    # ページ内の最小日付が開始日より前なら以降のページは古すぎるので終了
                    page_min = self._get_page_min_date(end_times)  # 最小日付を算出
                    if page_min is not None and page_min < start_date:  # 閾値を下回るなら
                        self.logger.info(
                            f"{idx+1}行目: ページ{page_no}の最小日付 {page_min} が開始日 {start_date} より前のため巡回終了"
                        )
                        break  # 打ち切り

                    # 次ページへ（見つからない/失敗なら終了）
                    try:
                        has_next = selenium_util.click_next()  # ページャをクリック
                        if not has_next:  # 次が無いなら
                            self.logger.info(f"{idx+1}行目: 次ページなし。累計 {len(detail_urls)} 件で巡回終了")  # 終了ログ
                            break  # ループ終了
                        page_no += 1  # ページ番号を進める
                    except Exception as e:  # クリック失敗等
                        self.logger.warning(f"{idx+1}行目: 次へクリック失敗または次ページなし: {e}")  # 警告
                        break  # ループ終了

                if not detail_urls:  # 期間内URLが空なら
                    self.logger.info(f"{idx+1}行目: 対象期間内の商品なし")  # 対象なしを通知
                    continue  # 次の行へ

                # 詳細ページを回って必要情報抽出
                details: List[Dict[str, Any]] = []  # 抽出結果の蓄積
                for detail_url in detail_urls:  # 各詳細URLを処理
                    try:
                        detail_flow = DetailPageFlow(driver, selenium_util)  # 詳細抽出フローを用意
                        detail_data = detail_flow.extract_detail(detail_url)  # 詳細情報を抽出
                        details.append(detail_data)  # 取得結果を追加
                        self.logger.debug("%d行目: 詳細抽出成功: %s", idx+1, detail_url)  # DEBUG出力
                    except Exception as e:  # 抽出失敗時
                        self.logger.warning(f"{idx+1}行目: 詳細抽出失敗 {detail_url}: {e}")  # 警告ログ

                # GSSに書き込む（dateは見栄えのためプレフィックス除去）
                if details:  # 抽出結果がある場合
                    for dct in details:  # 各レコードの整形
                        if isinstance(dct.get("date"), str) and dct["date"].startswith("'"):  # 先頭'で始まる場合
                            dct["date"] = dct["date"].lstrip("'")  # 先頭の'を取り除く

                    try:
                        # output_sheet_name = self.config.DATA_OUTPUT_SHEET  # 出力シート名
                        # reader = SpreadsheetReader(self.config.SPREADSHEET_ID, output_sheet_name)  # リーダ作成
                        # worksheet = reader.get_worksheet(output_sheet_name)  # 対象ワークシート取得

                        # ↓置き換え
                        output_sheet_name = self._resolve_output_sheet_name(idx)
                        reader = SpreadsheetReader(self.config.SPREADSHEET_ID, output_sheet_name)
                        worksheet = reader.get_worksheet(output_sheet_name)
                        self.logger.debug(f"出力WS: {output_sheet_name}")



                        flow = WriteGssFlow(worksheet)  # 書き込みフロー生成
                        flow.run(details)  # 一括書き込み実行
                        self.logger.info(f"{idx+1}行目: 期間内URLを {len(details)} 件書き込み完了")  # 完了ログ
                    except Exception as e:  # 書き込み失敗時
                        self.logger.error(f"{idx+1}行目: スプレッドシート書き込み失敗: {e}")  # エラー出力

            finally:
                # ドライバは都度クローズ（リソースリーク防止）
                try:
                    driver.quit()  # ブラウザを確実に終了
                except Exception:  # 終了時の例外は無視
                    pass  # 続行



    # ==========================================================
    # メソッド定義

    def url_and_selenium_flow_lookahead(self, conditions: List[Dict[str, Any]], lookahead_pages: int = 1) -> None:  # 先読み(lookahead)付きで検索一覧を巡回し、詳細抽出・書き込みまで行うエントリ関数
        # 新ロジック：「開始日をまたいだ後もNページだけ先読み」する巡回                                      # 目的の概要（開始日閾値を越えた後も少しだけページを進める）
        if not conditions:  # 検索条件が空なら処理不要
            self.logger.warning("条件が空なのでURL生成処理スキップ")  # ユーザに分かるように警告ログを出す
            return  # ここで関数終了（以降の処理は行わない）

        df = pd.DataFrame(conditions)  # 条件リストをDataFrame化（列操作やフィルタをやりやすくする）
        df = df[df["start_date"].astype(str).str.strip() != ""]  # 開始日が空の行を除外（前処理）
        df = df[df["end_date"].astype(str).str.strip() != ""]    # 終了日が空の行を除外（前処理）

        url_builder = UrlBuilder()  # 検索URLを生成するユーティリティを準備

        for idx, row in df.iterrows():  # 条件の各行を1件ずつ処理（idxは0始まりインデックス）
            try:  # 開始・終了日のパースと検証をまとめて例外処理
                start_date = self._to_date(row.get("start_date"))  # 任意型→dateに寄せるヘルパで開始日を取得
                end_date   = self._to_date(row.get("end_date"))    # 同様に終了日を取得
                if start_date is None or end_date is None:  # どちらかが解釈できない場合は不正
                    raise ValueError("開始/終了日の解釈に失敗")  # エラーとして処理し、下のexceptへ
            except Exception as e:  # パース失敗時のエラーハンドリング
                self.logger.error(f"{idx+1}行目: 開始・終了日変換失敗: {e}")  # 行番号付きで原因をログ
                continue  # この行はスキップして次の行へ

            keyword = self.extract_keyword(row)  # search_1〜search_5を連結して検索キーワードを生成
            if not keyword:  # キーワードが空の場合
                self.logger.warning(f"{idx+1}行目: キーワードなし。スキップ")  # 作業不能のためスキップを通知
                continue  # 次の行へ

            search_url = url_builder.build_url(keyword, per_page=100)  # 1ページ100件で検索URLを作成
            self.logger.info(f"{idx+1}行目: キーワード={keyword} | URL={search_url}")  # 何を検索するかをINFOで記録

            # --- ここからキーワード単位の集計（INFOは最後に1行だけ出す）---                                # 以降、このキーワードでの処理全体の統計を取る
            _t0 = _time.time()  # 経過時間計測のための開始時刻（_timeはtimeモジュールの別名想定）
            kstats = CrawlStats()  # ページ数・追加件数・パース成功/失敗・書込件数などの集計用オブジェクト

            try:  # ドライバの起動〜巡回〜詳細抽出〜書き込みを包括するtry
                driver = Chrome.get_driver()  # プロジェクトのChromeラッパからWebDriverを取得
                selenium_util = Selenium(driver)  # 要素取得やクリック等のユーティリティをラップ
                page_no = 1  # 現在のページ番号（1始まり）
                detail_urls: List[str] = []  # 期間内と判定された詳細ページURLの蓄積リスト
                seen: set[str] = set()  # 重複URLを避けるための集合
                extra_pages_left = int(lookahead_pages) if lookahead_pages and int(lookahead_pages) > 0 else 0  # 先読み可能な残ページ数（0以下なら先読みなし）
                crossed_threshold = False  # 「ページ最小日付が開始日より前」という閾値を跨いだかのフラグ
                zero_pages = 0  # 未使用のカウンタ（将来の空ページ連続検出用の名残）
                ZERO_CAP   = 3  # 上記の上限値（同じく未使用だが意味合いは「最大3ページまで」）

                driver.get(search_url)  # 検索URLへ遷移（初回ページ）

                # 初回ロードの安定化（失敗しても続行）                                           # ページのDocument読み込み完了を短時間待つ
                try:
                    WebDriverWait(driver, 2).until(
                        lambda d: d.execute_script("return document.readyState") == "complete"  # readyStateがcompleteになるのを待機
                    )
                except Exception:  # タイムアウト等
                    pass  # タイムアウト等でも続行（以降の取得でリカバリを試す）

                # data:URL に遷移してしまうケースへのガード（再ナビゲーション）                        # 稀にcurrent_urlがdata:になる対策
                if driver.current_url.startswith("data:"):  # data:スキームを検出
                    self.logger.debug("current_url が data: のため再ナビゲーションを実施")  # 事象をDEBUGで記録
                    driver.get(search_url)  # 改めて同じURLへ遷移

                # 「落札相場」ボタンを可能ならJSクリック（通常クリック不可対策）                         # UI上のボタンでクローズド検索へ誘導
                try:
                    past_btn = WebDriverWait(driver, 1).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".Auction__pastAuctionBtn"))  # ボタンの存在を待つ
                    )
                    try:
                        driver.execute_script("arguments[0].click();", past_btn)  # 被り等でクリックできない場合に備えJSでクリック
                        self.logger.debug("落札相場ボタン(JS)クリック")  # 実行したことをDEBUGで記録

                        WebDriverWait(driver, 1).until(  # クリック後に目的の状態に達するまで短時間待機
                            EC.any_of(
                                EC.presence_of_element_located((By.CSS_SELECTOR, ".Auc")),  # 特定DOMの出現
                                EC.url_contains("closedsearch")  # URLにclosedsearchが含まれる
                            )
                        )
                    except Exception as e:  # JSクリック失敗時
                        self.logger.debug(f"落札相場ボタンのクリック処理失敗（無視して続行）: {e}")  # クリック失敗でも致命的でないため続行
                except Exception:  # そもそもボタンが見つからないケース
                    self.logger.debug("落札相場ボタン見つからず → スキップして続行")  # ボタン無し環境として通常巡回に移る

                    # ※注意：この while は except ブロック内にあるため、                                      # whileループは「ボタン未検出時」にのみ実行される
                    #  ボタンが見つかった場合は以下のループに入らない（意図通りか要確認）。                     # 仕様として意図的かの確認ポイント
                    while True:  # 一覧ページをページ送りしながらURLと終了日時を集めるループ
                        try:
                            end_times = selenium_util.get_auction_end_dates()  # 一覧の終了日時テキスト群を取得
                            urls      = selenium_util.get_auction_urls()       # 対応する詳細URL群を取得
                        except Exception as e:  # 一覧取得失敗
                            self.logger.warning(f"{idx+1}行目: 商品URLまたは終了日時取得失敗: {e}")  # 一覧取得に失敗した場合は警告して中断
                            break  # ループ終了

                        n = min(len(end_times), len(urls))  # ペアとして扱える件数（短い方に合わせる）
                        added_this_page = 0  # このページで新規に追加できたURL数
                        # ページ単位のパース成否カウント（集計用）                                           # 1ページ内の成功/失敗件数を数える
                        page_parse_ok = 0  # 成功カウント初期化
                        page_parse_ng = 0  # 失敗カウント初期化

                        for i in range(n):  # ペアごとに日付判定と期間フィルタを実施
                            d = self._to_date(end_times[i])  # 終了日時表記をdateに解釈（失敗ならNone）
                            if d is None:  # パース失敗
                                page_parse_ng += 1  # パース失敗としてカウント
                                continue  # 次の要素へ
                            page_parse_ok += 1  # パース成功

                            if d > end_date:  # 終了日が指定期間より新しすぎる（先へ進むと古くなる前提でスキップ）
                                continue  # 採用しない
                            elif d < start_date:  # 終了日が期間より古い（以降も古い可能性が高い）
                                continue  # 採用しない
                            else:  # 期間内
                                u = urls[i]  # 期間内なので対応するURLを取り出す
                                if u not in seen:  # まだ未収集なら
                                    seen.add(u)  # 重複防止セットに追加
                                    detail_urls.append(u)  # 詳細抽出対象に追加
                                    added_this_page += 1  # 今ページの追加数をインクリメント

                        # ← 集計に反映                                                                       # キーワード単位の集計(kstats)へページ結果を反映
                        kstats.pages += 1  # 処理したページ数をカウント
                        kstats.added += added_this_page  # 期間内に追加できたURL件数を加算
                        kstats.parse_ok += page_parse_ok  # パース成功件数を累積
                        kstats.parse_ng += page_parse_ng  # パース失敗件数を累積

                        # ページごとのログは DEBUG に降格                                                          # 通常運用では冗長なため詳細はDEBUGで記録
                        self.logger.debug(
                            "ページ%d サマリ: 追加 %d / 累計 %d | パース 成功 %d / 失敗 %d",
                            page_no, added_this_page, len(detail_urls), page_parse_ok, page_parse_ng
                        )

                        # 取得件数0のページが続く場合の打ち切り（locals()でカウンタを疑似管理）                        # 要素0ページが続くときに早期終了する仕組み
                        if n == 0:  # 1件も取得できなかった場合
                            if self._page_has_no_results(driver):  # DOMや文言から「0件」を検出できた場合
                                self.logger.info(f"{idx+1}行目: 条件に一致する商品は見つかりませんでした（ページ{page_no}）。巡回終了")  # 終了通知
                                break  # ループ終了

                            empty_pages_in_a_row = locals().get("empty_pages_in_a_row", 0) + 1  # 連続空ページ数をカウントアップ
                            locals()["empty_pages_in_a_row"] = empty_pages_in_a_row  # 疑似的にローカル変数として保持
                            if empty_pages_in_a_row >= 3:  # 3連続で空なら
                                self.logger.warning(f"{idx+1}行目: 空ページが{empty_pages_in_a_row}連続。巡回終了")  # 打ち切りを警告
                                break  # ループ終了
                        else:  # 1件以上は取れた場合
                            locals()["empty_pages_in_a_row"] = 0  # 何か取れたら連続カウンタをリセット

                        # 最小日付が開始日より前 → 以降は古い可能性が高いので先読みモード                              # 閾値を跨いだ後、残り許容量の範囲で数ページだけ進む
                        page_min = self._get_page_min_date(end_times)  # ページ中の最小日付を算出
                        if page_min is not None and page_min < start_date:  # 閾値（開始日）より古いデータが含まれる
                            if not crossed_threshold:  # 初回だけログを出す
                                crossed_threshold = True  # 閾値を跨いだことを記録
                                self.logger.debug(
                                    f"{idx+1}行目: ページ{page_no}の最小日付 {page_min} が開始日 {start_date} より前 → "
                                    f"先読みを {extra_pages_left} ページ許容"
                                )

                            if extra_pages_left <= 0:  # もう先読み許容量がない場合
                                self.logger.debug(
                                    f"{idx+1}行目: 先読み許容量を使い切ったため巡回終了（累計 {len(detail_urls)} 件）"
                                )
                                break  # ループ終了
                            else:  # まだ先読みできる場合
                                extra_pages_left -= 1  # 先読み残数を1減らす
                                self.logger.debug(
                                    f"{idx+1}行目: 閾値跨ぎ後の先読み継続。残り先読みページ数: {extra_pages_left}"
                                )

                        # ページャではなくURLの b= を書き換えてページ送り（セレクタ変更の影響回避）                     # UI依存を避け、クエリパラメータで確実にページを進める
                        try:
                            per_page = 100  # 1ページの件数（URL組み立て時に使用）
                            next_b = (page_no * per_page) + 1  # 次ページ先頭の開始インデックス（b=）
                            cur = driver.current_url  # 現在のURLを取得

                            # 既存の b= を削除しつつURLを再構成                                                     # 既存のb=を取り除き、正しい区切り文字で付け直す
                            base = re.sub(r"([?&])b=\d+", r"\1", cur)  # b=クエリを正規表現で除去
                            if base.endswith("?") or base.endswith("&"):  # 末尾が不正な区切りなら
                                base = base[:-1]  # 余分な記号を1文字取り除く
                            sep = "&" if "?" in base else "?"  # 既にクエリがあるかで区切りを選択
                            next_url = f"{base}{sep}b={next_b}&n={per_page}"  # 次ページのURLを組み立て

                            t0 = pytime.perf_counter()  # 遷移の経過時間計測開始
                            driver.get(next_url)  # 直接URL指定でページ遷移
                            WebDriverWait(driver, 3).until(lambda d: f"b={next_b}" in d.current_url)  # URLに期待のb=が入るまで待機
                            self.logger.debug("URLジャンプで次ページへ: b=%d（%.2f秒）", next_b, pytime.perf_counter() - t0)  # 遷移時間をDEBUG出力
                            page_no += 1  # ページ番号を進める
                        except Exception as e:  # URLジャンプ失敗等
                            self.logger.info(f"{idx+1}行目: 次ページなし/遷移失敗のため終了: {e}")  # ページ送り不可なら情報ログを出して終了
                            break  # ループ終了

                    if not detail_urls:  # 期間内に該当URLが1件もない場合
                        self.logger.info(f"{idx+1}行目: 対象期間内の商品なし")  # その旨を通知
                        # kstats.written は 0 のまま                                                           # 書き込み件数は変更しない
                        continue  # 次のキーワードへ

                    # 詳細抽出と書き込み（date先頭の'は除去）                                                    # 収集したURLを詳細巡回し、結果をGSSに書き込む
                    details: List[Dict[str, Any]] = []  # 詳細データの蓄積リスト
                    for detail_url in detail_urls:  # 各URLを詳細ページとして処理
                        try:
                            detail_flow = DetailPageFlow(driver, selenium_util)  # 詳細抽出用フローを生成
                            detail_data = detail_flow.extract_detail(detail_url)  # タイトル/価格/ct/画像/日付を抽出
                            details.append(detail_data)  # 正常に取得できたデータを蓄積
                            # 成功は DEBUG に降格                                                                 # 通常は冗長なため詳細成功ログはDEBUG
                            self.logger.debug(f"{idx+1}行目: 詳細抽出成功: {detail_url}")  # 個別成功の記録
                        except Exception as e:  # 1件の詳細抽出に失敗
                            self.logger.warning(f"{idx+1}行目: 詳細抽出失敗 {detail_url}: {e}")  # 失敗URLは警告して継続

                    if details:  # 1件以上詳細が取れていれば
                        for dct in details:  # スプレッドシート表示上の都合で日付先頭の'を除去
                            if isinstance(dct.get("date"), str):  # 文字列型の日付のみ対象
                                dct["date"] = dct["date"].lstrip("'")  # 先頭のシングルクォートを削る

                        try:
                            # output_sheet_name = self.config.DATA_OUTPUT_SHEET  # 出力先シート名
                            # reader = SpreadsheetReader(self.config.SPREADSHEET_ID, output_sheet_name)  # シート読取用
                            # worksheet = reader.get_worksheet(output_sheet_name)  # 対象ワークシートを取得


                            # ↓置き換え
                            output_sheet_name = self._resolve_output_sheet_name(idx)
                            reader = SpreadsheetReader(self.config.SPREADSHEET_ID, output_sheet_name)
                            worksheet = reader.get_worksheet(output_sheet_name)
                            self.logger.debug(f"出力WS: {output_sheet_name}")




                            flow = WriteGssFlow(worksheet)  # 書き込みフローを用意
                            flow.run(details)  # まとめて書き込み（USER_ENTEREDで式や数値を評価）
                            self.logger.info(f"{idx+1}行目: 期間内URLを {len(details)} 件書き込み完了")  # 書き込み完了をINFOで通知
                            kstats.written = len(details)  # ← 集計に反映                                                    # 書き込み件数を統計に反映
                        except Exception as e:  # 書き込み失敗
                            self.logger.error(f"{idx+1}行目: スプレッドシート書き込み失敗: {e}")  # 書き込み失敗時のエラーログ
                        
                        finally:  # 書き込みの成否に関わらずドライバ終了を試みる
                            # ※注意：driver.quit() がこの finally の内側にあるため、                                  # 注意点：detailsが空のときはquitされない可能性に触れている
                            #  details が空のときは quit されない（リソースリークの恐れ）。                              # 設計上の挙動であり、ここでは仕様に従う
                            #  仕様上の振る舞いなのでここでは変更しない。                                                  # 本コードでは修正しない旨のコメント
                            try:
                                driver.quit()  # ブラウザを終了してリソース解放
                            except Exception:  # 終了失敗は無視
                                pass  # 継続

            finally:  # キーワード単位の処理が終わったら必ず集計ログを出す
                # キーワード単位の最終集計（INFO で 1 行だけ）                                                  # ページ数/追加件数/パース成否/書込み件数/経過秒をまとめて出力
                self.logger.info(
                    "集計: キーワード='%s' | ページ=%d | 期間内URL=%d | パース 成功=%d 失敗=%d | 書込み=%d | %.2fs",
                    keyword, kstats.pages, kstats.added, kstats.parse_ok, kstats.parse_ng, kstats.written, _time.time() - _t0  # 所要時間は開始時刻との差
                )



    # ==========================================================
    # メソッド定義

    def test_date_converter(self, sample_end_time: str) -> None:  # DateConverterの動作を試す
        # DateConverterの動作確認（型と値をログ）
        try:
            converted_date = DateConverter.convert(sample_end_time)  # 文字列を日付に変換
            self.logger.info(f"日付変換: 型={type(converted_date)} | 値={converted_date}")  # 結果を出力
        except Exception as e:  # 失敗時
            self.logger.error(f"DateConverter変換テストでエラー: {e}")  # エラー内容



    # ==========================================================
    # メソッド定義

    def test_price_calculator(self, title: str, price: int) -> None:  # 1ct単価計算のテスト
        # PriceCalculatorの動作確認（1ct単価を算出してログ）
        try:
            price_per_ct = PriceCalculator.calculate_price_per_carat(title, price)  # タイトルと価格から単価を計算
            self.logger.info(f"タイトル: {title} / 落札価格: {price} → 1ct単価: {price_per_ct} 円/ct")  # 結果を出力
        except Exception as e:  # 失敗時
            self.logger.error(f"PriceCalculatorテスト失敗: {e}")  # エラー内容を出力



    # ==========================================================
    # メソッド定義

    def test_image_downloader(self) -> None:  # =IMAGE()式の生成確認
        # ImageDownloaderの動作確認（=IMAGE()式の生成）
        try:
            image_url = "https://auctions.c.yimg.jp/images.auctions.yahoo.co.jp/image/dr000/auc0106/user/5ec807c934150c37fea5b1cda6cdb4938dea1bcdd982696a3d9c90b59c549314/i-img1200x849-17500560233691ls9baa33.jpg"  # テスト用URL
            formula = ImageDownloader.get_image_formula(image_url)  # =IMAGE(...) 形式を生成
            self.logger.info(f"ImageDownloaderテスト成功: {formula}")  # 成功ログ
            print(f"IMAGE式: {formula}")  # ログ以外にも標準出力で確認
        except Exception as e:  # 失敗時
            self.logger.error("ImageDownloaderテスト失敗", exc_info=True)  # 例外情報付きでログ
            print("画像ダウンロード失敗:", e)  # 標準出力にも表示



    # ==========================================================
    # メソッド定義

    def run(self) -> None:  # 全体の処理開始点
        # メインエントリ：条件読込→巡回実行→終了ログ
        self.logger.info("プログラム開始")  # 開始ログ
        try:
            conditions = self.load_search_conditions()  # 条件を読み込む
            self.url_and_selenium_flow_lookahead(conditions, lookahead_pages=1)  # 既定で先読み1ページ
        finally:
            self.logger.info("プログラム終了")  # 終了ログ





# ==============
# 実行の順序
# ==============
# 1. 各種モジュールをimportする（os/logging/typing/pandas/datetime/re/time/Selenium系/自作モジュール など）
# → 以降で使う標準・外部・自作モジュールを読み込む準備段階。補足：dataclassは重複importされているが挙動に影響はない（冪等）。

# 2. logger = logging.getLogger(name) を実行する
# → このモジュール専用のロガーを取得し、以降の情報・警告・エラーをここへ集約する。補足：ログ出力の有効/詳細度は上位設定に依存。

# 3. class CrawlStats を定義する（@dataclass）
# → キーワード単位でのページ数・追加URL数・パース成功/失敗・書込み件数などの集計用データ構造を用意する。補足：定義のみでこの時点では実行されない。

# 4. class ParseStats を定義する（@dataclass）＋ メソッド add_success / add_failure
# → 1ページ内のパース成功/失敗件数と最小/最大日時を管理する。補足：成功時に最小/最大日時を更新するロジックをメソッドに切り出している。

# 5. 関数 log_page_summary(…) を定義する
# → 1ページ処理の集計（追加件数/累計/成功失敗/最小最大日時）をINFOログに出すヘルパ。補足：ここも定義だけで即時実行はされない。

# 6. class Config を定義する
# → スプレッドシートIDやシート名、ヘッドレス指定、認証パス等の設定値を集約する。補足：環境変数から認証パスを拾うため、実行環境ごとの差し替えが容易。

# 7. class MainFlow を定義する（全体のオーケストレーター）
# → 条件の読み込み→検索巡回→詳細抽出→スプレッドシート書き込み までの主要手順をまとめる器。補足：この段階ではメソッドの“定義”だけ。

# 8. メソッド init(self, config: Config) を定義する
# → 設定とロガーを保持し、内部フラグを初期化する。補足：ここでWebDriver等は作らず、実際に必要になったときに用意する方針。

# 9. メソッド _ensure_selenium_stack(self) を定義する
# → Chromeラッパ/Driver/Seleniumユーティリティ/詳細抽出フローを遅延初期化する。補足：get_driverメソッド有無など複数実装差に防御的に対応。

# 10. メソッド test_num_extractor(self, text) を定義する
# → NumExtractorでct値抽出を試し、成功/失敗をログ出力するテスト用ユーティリティ。補足：本処理には必須ではない検証用。

# 11. メソッド load_search_conditions(self) を定義する
# → SpreadsheetReaderで検索条件を読み込み、件数をINFOログに出して返す。補足：失敗時はエラーをログに残し、空リストを返す設計。

# 12. メソッド write_test_data(self, worksheet) を定義する
# → ダミーデータを作成し、WriteGssFlow.runで一括書き込みする動作確認用の関数。補足：例外時はエラーをログに記録。

# 13. メソッド extract_keyword(self, row) を定義する
# → search_1〜search_5 を空白結合して検索キーワード文字列を作る。補足：空要素は空文字として無視され、前後空白は除去。

# 14. 静的メソッド _to_date(value) を定義する（@staticmethod）
# → 受け取った値をDateConverter等でdate型へ“寄せ”、失敗時はNoneを返すユーティリティ。補足：厳格エラーではなくNone返しで上位判定に委ねる。

# 15. メソッド _get_page_min_date(self, end_times) を定義する
# → 終了日時文字列の配列から最小日付を求めて返す。補足：変換失敗（None）はスキップして最小値を更新。

# 16. メソッド _page_has_no_results(self, driver) を定義する
# → 文言/DOMの両面から「検索結果0件」UIを検出する。補足：UI変更に弱いため複数パターンでの検出を試みる防御的実装。

# 17. メソッド url_and_selenium_flow(self, conditions) を定義する
# → 旧ロジック：先読みなしで一覧巡回→期間フィルタ→詳細抽出→GSS書込み→driver終了までを実装。補足：こちらはfinallyでdriverを確実にquitする設計。

# 18. メソッド url_and_selenium_flow_lookahead(self, conditions, lookahead_pages=1) を定義する
# → 新ロジック：開始日閾値を跨いだ後も指定ページ数だけ先読みしつつ巡回・抽出・書込みする。補足：except内にwhileループがあり「落札相場ボタン未検出時のみ巡回ループに入る」構造になっている点は混乱しやすい。

# 19. メソッド test_date_converter / test_price_calculator / test_image_downloader を定義する
# → それぞれDateConverter・PriceCalculator・ImageDownloaderの動作確認用メソッド。補足：運用必須ではないテスト・検証用途。

# 20. メソッド run(self) を定義する（エントリポイント）
# → 「開始ログ→条件読込→先読み付き巡回呼び出し→終了ログ」の骨格をまとめる。補足：ここも定義であり、外部から呼ばれて初めて処理が動く。

# 21. （実行時）外部から class MainFlow を生成し、メソッド run() が呼ばれる
# → INFOで開始を記録し、load_search_conditions()で条件リストを取得して url_and_selenium_flow_lookahead(…) を呼ぶ。補足：finallyで必ず終了ログを出す。

# 22. （実行時）url_and_selenium_flow_lookahead の前処理が走る
# → 条件をDataFrame化し、開始/終了日が空の行を除外、UrlBuilderを用意する。補足：日付は _to_date でdate型へ寄せて検証。

# 23. （実行時）各行ループで検索URL生成→Driver起動→初回ナビゲーション→「落札相場」ボタン対応を試みる
# → ボタンが見つからず例外になった場合のみ、以降の一覧巡回whileループに入る。補足：ボタン“が見つかった”場合はこのwhileに入らない構造なので設計意図の確認が必要。

# 24. （実行時）一覧巡回ループで end_times / urls を取得し、期間フィルタと重複排除を行う
# → 期間内URLを detail_urls に蓄積し、ページ単位の統計を更新してDEBUG/INFOログを出す。補足：ページ最小日付が開始日より前になったら「先読み許容量」の範囲で数ページだけ続行。

# 25. （実行時）ページ送りはUIクリックではなくURLの b= パラメータを書き換えて進める
# → ...?b=次開始位置&n=100 の形式で直接遷移し、待機条件でURL反映を確認する。補足：UI変更の影響を受けにくい堅牢化テクニック。

# 26. （実行時）detail_urls が空なら次のキーワードへ、1件以上あれば詳細抽出に進む
# → DetailPageFlow.extract_detail(…) で各詳細を収集し、日付先頭の’は表示都合で削除。補足：抽出失敗は警告ログに留めて処理継続。

# 27. （実行時）WriteGssFlow(worksheet).run(details) でスプレッドシートに一括書き込みする
# → USER_ENTEREDで式は評価され、画像列は =IMAGE(…) 形式が反映される。補足：書込み成功件数をINFOに記録し、kstats.writtenに反映。

# 28. （実行時）ドライバ終了とキーワード集計ログを出す
# → finallyで driver.quit() を試み、最後にページ数/追加数/成功失敗/書込み/経過秒の集計をINFOで出す。補足：本実装コメント上、detailsが空のケースではquitされない設計が示唆されており、リソースリークに注意。