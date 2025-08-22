# ==========================================================
# import（標準、プロジェクト内モジュール）  # 必要な標準/外部ライブラリ・自作モジュールを読み込む

import logging  # ログ記録のための標準ライブラリ
from datetime import datetime  # 日時の取得やフォーマットに使用
from dataclasses import dataclass  # データ保持用の軽量クラスを簡潔に定義するために使用
from collections import defaultdict  # キーごとにレコードを束ねるための辞書亜種
from typing import Any, Dict, List, Optional, Set  # 型ヒント（読みやすさ/静的解析向上）
import gspread  # Google スプレッドシート操作用ライブラリ
from gspread.exceptions import WorksheetNotFound  # 指定タブが存在しない場合の例外
from installer.src.const import gss as CGSS  # スプレッドシート全体に関する定数
from installer.src.const import sheets as CSHEETS  # シート構造・列名・書式などの定数
from installer.src.const import templates as CTPL  # 出力テンプレート（TEXT_PREFIX, IMAGE式など）


# ==========================================================
# ログ設定（このモジュール専用のロガー）  # 他モジュールと区別できるロガーを取得

logger: logging.Logger = logging.getLogger(__name__)  # このファイル専用のロガーを作成


# ==========================================================
# class定義

@dataclass  # フィールド定義だけで比較/表示などを自動生成
class WriteResult:
    written: int   # 実際に新規で書き込んだ件数（全タブ合計）
    skipped: int   # 重複でスキップした件数（全タブ合計）


# ==========================================================
# class定義

class WorksheetRouter:


    # ==========================================================
    # コンストラクタ

    def __init__(self, gc: gspread.Client, spreadsheet_id: str, default_title: str) -> None:  # 依存注入
        self.gc = gc  # gspread のクライアントインスタンスを保持
        self.spreadsheet = gc.open_by_key(spreadsheet_id)  # 対象のスプレッドシート本体を開く
        self.default_title = str(default_title)  # デフォルトで使うタブ名（文字列化して保持）
        self._cache: Dict[str, gspread.Worksheet] = {}  # 取得済みタブをキャッシュして再利用


    # ==========================================================
    # メソッド定義

    def by_title(self, title_like: Any) -> gspread.Worksheet:  # タイトル（に準ずる値）からタブを返す
        # 例：2, " 2 ", None → "2" / デフォルトへ  # Noneや空は既定タブへフォールバック
        name = str(title_like).strip() if title_like not in (None, "") else self.default_title  # 文字列化・前後空白除去
        if name in ("nan", "None", ""):  # NaN/None風の文字列にも対処
            name = self.default_title  # 無効値は既定タブ名に置き換える

        if name in self._cache:  # 既に取得済みなら
            return self._cache[name]  # キャッシュから即返す

        try:
            worksheet = self.spreadsheet.worksheet(name)  # ← タイトル名でタブを取得（存在すれば成功）
        except WorksheetNotFound:
            # 必要なら自動作成（const の既定サイズを使用）  # 無ければ新規タブを作成
            worksheet = self.spreadsheet.add_worksheet(
                title=name,  # 生成するタブのタイトル
                rows=CSHEETS.DEFAULT_WS_ROWS,  # 行数の既定値（定数で管理）
                cols=CSHEETS.DEFAULT_WS_COLS,  # 列数の既定値（定数で管理）
            )

        self._cache[name] = worksheet  # 取得/作成したタブをキャッシュに保存
        return worksheet  # 呼び出し元へワークシートを返す


# ==========================================================
# class定義

class WriteGssFlow:
    """
    役割：
    抽出済みレコードのリストを Google スプレッドシートへ append 形式で書き込む。
    既存 URL と重複するものは除外し、書込み件数/重複件数を返す。
    ws_name 列があれば、そのタイトルのタブに書き込む。

    想定レコード構造(dict):
    input_date, date, title, price, ct, 1ct_price, image/image_url/img_url, url, ws_name, check
    """  # 複数フィールドを想定した入出力仕様をdocstringで説明


    # ==========================================================
    # コンストラクタ

    def __init__(
        self,
        *,
        worksheet: Optional[gspread.Worksheet] = None,  # 単一タブ固定で書き込む場合に指定
        gc: Optional[gspread.Client] = None,  # ルーティング書き込み時に使用するクライアント
        spreadsheet_id: Optional[str] = None,  # ルーティング先スプレッドシートID
        default_title: str = CGSS.DEFAULT_OUTPUT_SHEET,  # 既定のタブ名（constで管理）
    ) -> None:
        self.logger: logging.Logger = logger  # モジュールロガーをインスタンスから参照
        self.default_title: str = str(default_title)  # 既定タブ名を文字列で保持

        if worksheet is not None:  # 単一タブモードの設定
            self._mode: str = "single"  # モード名を識別用に保存
            self._worksheet: gspread.Worksheet = worksheet  # 直接渡されたワークシートを保持
            self._router: Optional[WorksheetRouter] = None  # ルータは不要なのでNone
        elif gc is not None and spreadsheet_id is not None:  # ルーティングモード
            self._mode = "route"  # 複数タブへの振り分けを行う
            self._router = WorksheetRouter(gc, spreadsheet_id, default_title=self.default_title)  # ルータ生成
            self._worksheet = None  # type: ignore[assignment]  # singleモード以外では未使用
        else:
            raise ValueError("WriteGssFlow: worksheet か (gc と spreadsheet_id) のいずれかを指定してください。")  # 引数チェック


    # ==========================================================
    # メソッド定義

    def _safe_sheet_text(self, value: Any) -> str:  # TEXT_PREFIXを付け文字列として扱わせる
        text_value = str(value)  # まずは文字列化
        return text_value if text_value.startswith(CTPL.TEXT_PREFIX) else f"{CTPL.TEXT_PREFIX}{text_value}"  # 既に付いていればそのまま


    # ==========================================================
    # メソッド定義

    def _to_bool(self, candidate_value: Any) -> bool:  # 真偽値への正規化処理
        if isinstance(candidate_value, bool):  # すでにboolなら
            return candidate_value  # そのまま返す
        text_value = str(candidate_value).strip().lower()  # 文字列化して余白除去・小文字化
        return text_value in ("1", "true", "t", "yes", "y", "on")  # 代表的なtrue表現を受け付ける


    # ==========================================================
    # メソッド定義

    def _target_ws(self, ws_name_like: Any) -> gspread.Worksheet:  # 書き込み先タブを決定
        if self._mode == "single":  # 単一タブモードなら
            return self._worksheet  # type: ignore[return-value]  # そのまま事前指定のタブを返す
        assert self._router is not None  # ルーティングモード前提の保証
        name = str(ws_name_like).strip() if ws_name_like not in (None, "") else self.default_title  # 空は既定に落とす
        if name in ("nan", "None", ""):  # 無効っぽい値は
            name = self.default_title  # 既定タブへ寄せる
        return self._router.by_title(name)  # 取得（無ければ作成）して返す


    # ==========================================================
    # メソッド定義

    def format_image_formula(self, url_or_formula: Any) -> str:  # 画像セル用の値を整形
        if not url_or_formula:  # 空なら
            return ""  # そのまま空で返す
        text_value = str(url_or_formula).strip()  # 文字列として扱う
        if text_value.startswith("="):  # 既に=IMAGE(...) などの式なら
            return text_value  # 加工せず返す
        return CTPL.IMAGE_FORMULA.format(url=text_value)  # URLならテンプレで=IMAGE(...)化


    # ==========================================================
    # メソッド定義

    @staticmethod
    def _norm(value: Any) -> str:  # 比較用・キー生成用に正規化
        if value is None:  # None対策
            return ""  # 空文字へ
        text_value = str(value).strip().lower()  # 前後空白除去＋小文字統一
        return text_value  # 正規化後の文字列を返す


    # ==========================================================
    # メソッド定義

    def _build_output_row(self, record: Dict[str, Any]) -> List[Any]:  # 1件のレコードを行配列へ変換
        image_source = record.get("img_url") or record.get("image_url") or record.get("image") or record.get("img_src") or ""  # 画像URL候補を優先順に取得

        fallback_today_str = datetime.now().strftime(CTPL.INPUT_DATE_FMT)  # input_date未指定時のデフォルト（今日）
        raw_input_date = record.get("input_date") or fallback_today_str  # レコードの値を優先

        normalized_input_date_str = str(raw_input_date).replace("/", "-").split()[0]  # フォーマットを揃え日付部分のみ抽出
        input_date_cell_str = self._safe_sheet_text(normalized_input_date_str)  # シート上で文字列として扱うための整形

        date_cell_str = self._safe_sheet_text(record.get("date", ""))  # 終了日も文字列固定で貼り付け

        return [
            input_date_cell_str,  # 入力日（TEXT_PREFIX付きの文字列）
            date_cell_str,  # 終了日（TEXT_PREFIX付きの文字列）
            record.get("title", ""),  # タイトル文字列
            record.get("price", ""),  # 価格（数値/文字どちらでも格納可）
            record.get("ct", ""),  # カラット値
            record.get("1ct_price", ""),  # 1ct単価
            self.format_image_formula(image_source),  # 画像セル（=IMAGE(...)式 or 空）
            record.get("url", ""),  # 詳細ページURL
        ]  # シートの1行として返す


    # ==========================================================
    # メソッド定義

    def _find_url_col_index(self, worksheet: gspread.Worksheet) -> Optional[int]:  # 見出し行からURL列を探す
        try:
            header_row_values = [self._norm(header_cell_value) for header_cell_value in (worksheet.row_values(1) or [])]  # 1行目（見出し）を正規化して取得
        except Exception:
            header_row_values = []  # 取得に失敗した場合は空として扱う
        if not header_row_values:  # 見出しが無ければ
            return None  # URL列は特定できない

        for col_index, header_cell_value in enumerate(header_row_values, start=1):  # 厳密候補で検索
            if header_cell_value in CSHEETS.URL_HEADER_CANDIDATES:  # 完全一致候補
                return col_index  # 見つかった列番号を返す
        for col_index, header_cell_value in enumerate(header_row_values, start=1):  # あいまい候補で再検索
            if header_cell_value in CSHEETS.URL_HEADER_FUZZY:  # 近似名候補
                return col_index  # 見つかった列番号を返す
        return None  # 該当列が無い場合


    # ==========================================================
    # メソッド定義

    def _load_existing_url_keys(self, worksheet: gspread.Worksheet) -> Set[str]:  # 既存URLの集合を読み込む
        url_col_index = self._find_url_col_index(worksheet)  # URLが入っている列を推定
        try:
            if url_col_index is None:  # 見つからなければ
                column_values = worksheet.col_values(CSHEETS.APPEND_ANCHOR_COLUMN_INDEX)  # アンカー列（既定列）で代替
            else:
                column_values = worksheet.col_values(url_col_index)  # URL列の値を全取得
        except Exception as e:
            self.logger.warning(f"[{worksheet.title}] 既存URL取得に失敗。重複判定をスキップします: {e}")  # 読み込み失敗時は重複判定しない
            return set()  # 空集合を返す

        return {
            self._norm(cell_value)  # 比較しやすいよう正規化
            for cell_value in (column_values[1:] if len(column_values) > 1 else [])  # 見出し行（先頭）を除外
            if cell_value  # 空文字は除外
        }  # 既存URLのキー集合を作成


    # ==========================================================
    # メソッド定義

    @staticmethod
    def _extract_url_key_from_record(record: Any) -> str:  # レコードから重複判定用のURLキーを取り出す
        if isinstance(record, dict):  # dict形式のとき
            for k in ("url", "detail_url", "link", "リンク", "URL"):  # 候補キーを優先順に確認
                if k in record and record[k]:  # 値が存在していれば
                    return WriteGssFlow._norm(record[k])  # 正規化して返す
            return ""  # 見つからない場合
        if isinstance(record, (list, tuple)):  # 配列形式のとき（末尾がURL想定）
            return WriteGssFlow._norm(record[-1] if record else "")  # 末尾要素を正規化
        if isinstance(record, str):  # 文字列そのものがURLのとき
            return WriteGssFlow._norm(record)  # 正規化して返す
        return ""  # 対応外の型は空を返す


    # ==========================================================
    # メソッド定義

    def _filter_duplicates_for_ws(self, records: List[Dict[str, Any]], worksheet: gspread.Worksheet) -> List[Dict[str, Any]]:  # 同一URLの重複を除外
        existing_url_keys = self._load_existing_url_keys(worksheet)  # 既存登録済みURLの集合を取得
        filtered_records: List[Dict[str, Any]] = []  # 採用するレコードの入れ物
        dropped_count = 0  # スキップ件数のカウンタ

        for record in records:  # 各レコードを確認
            url_key = self._extract_url_key_from_record(record)  # 重複判定に使うキーを取り出す
            if url_key and url_key in existing_url_keys:  # 既に存在するURLなら
                dropped_count += 1  # スキップ数を加算
                continue  # 次のレコードへ
            filtered_records.append(record)  # 採用リストに追加
            if url_key:  # 新規URLが得られたら
                existing_url_keys.add(url_key)  # 以降の判定用に集合へ追加

        self.logger.info(f"[{worksheet.title}] 重複スキップ: 採用={len(filtered_records)}件, 除外={dropped_count}件")  # 結果をログ出力
        return filtered_records  # 重複を除いたレコード群を返す


    # ==========================================================
    # メソッド定義

    def _append_batch(self, worksheet: gspread.Worksheet, rows: List[List[Any]]) -> None:  # 連続範囲で一括更新
        start_row_index = len(worksheet.col_values(CSHEETS.APPEND_ANCHOR_COLUMN_INDEX)) + 1  # 先頭列の使用数から次行を算出
        start_cell_addr = f"{CSHEETS.APPEND_ANCHOR_COLUMN}{start_row_index}"  # A1表記の開始セルを組み立て
        worksheet.update(start_cell_addr, rows, value_input_option=CSHEETS.VALUE_INPUT_OPTION)  # APIで範囲更新（入力方式は定数で指定）
        self.logger.info(f"[{worksheet.title}] write: start={start_cell_addr}, rows={len(rows)}")  # 実行内容を情報ログ


    # ==========================================================
    # メソッド定義

    def write(self, rows_in_period: List[Dict[str, Any]]) -> WriteResult:  # レコード群を書き込み、結果件数を返す
        self.logger.info("WriteGssFlow: データの書き込みフローを開始します")  # フロー開始のログ

        if self._mode == "single":  # 単一タブモードの処理
            worksheet = self._worksheet  # type: ignore[assignment]  # 事前にもらったワークシートを利用
            records = [r for r in rows_in_period if ("check" not in r) or self._to_bool(r.get("check"))]  # check=False を除外
            new_rows = self._filter_duplicates_for_ws(records, worksheet)  # 重複レコードを除去
            if not new_rows:  # 書き込むものが無い場合
                self.logger.info(f"[{worksheet.title}] 新規書き込み対象がありません（0件）")  # 何も書かない旨をログ
                return WriteResult(written=0, skipped=len(rows_in_period))  # すべてスキップ扱いで返す

            output_rows = [self._build_output_row(r) for r in new_rows]  # シート行へ変換
            self._append_batch(worksheet, output_rows)  # 一括で追記

            written_count = len(output_rows)  # 実際に書けた件数
            skipped_count = len(rows_in_period) - written_count  # 元件数との差分=スキップ件数
            return WriteResult(written=written_count, skipped=skipped_count)  # 集計結果を返す

        records_by_ws_name: Dict[str, List[Dict[str, Any]]] = defaultdict(list)  # タブ名ごとにレコードを仕分け
        for record in rows_in_period:  # 入力レコードを走査
            if "check" in record and not self._to_bool(record.get("check")):  # check=Falseは除外
                continue  # 次へ
            ws_name_str = str(record.get("ws_name") or self.default_title).strip() or self.default_title  # タブ名を決定
            if ws_name_str in ("nan", "None", ""):  # 無効値を補正
                ws_name_str = self.default_title  # 既定タブへ
            records_by_ws_name[ws_name_str].append(record)  # タブ単位の配列に追加

        total_written = 0  # 全タブ合計の書込み件数
        total_skipped = 0  # 全タブ合計のスキップ件数

        for ws_name_str, records in records_by_ws_name.items():  # タブごとに処理
            worksheet = self._target_ws(ws_name_str)  # 書き込み先タブを用意
            new_rows = self._filter_duplicates_for_ws(records, worksheet)  # 重複除去を実施
            if not new_rows:  # 新規が無ければ
                self.logger.info(f"[{worksheet.title}] 新規書き込み対象がありません（0件）")  # ログして
                total_skipped += len(records)  # すべてスキップに加算
                continue  # 次のタブへ

            output_rows = [self._build_output_row(r) for r in new_rows]  # 出力行へ変換
            self._append_batch(worksheet, output_rows)  # 一括追記

            total_written += len(output_rows)  # 書込み件数を合算
            total_skipped += (len(records) - len(output_rows))  # スキップ件数を合算

        self.logger.info(f"スプレッドシート書き込み成功: {total_written}件（全タブ合計）")  # 成功件数を出力
        self.logger.info(f"重複スキップ（合計）: 採用={total_written}件, 除外={total_skipped}件")  # スキップ件数も出力

        return WriteResult(written=total_written, skipped=total_skipped)  # 合計結果を返す


    # ==========================================================
    # メソッド定義

    def run(self, rows_in_period: List[Dict[str, Any]]) -> int:  # 旧APIとの互換のためのヘルパ
        self.logger.debug("WriteGssFlow.run() is deprecated. Use write() instead.")  # 非推奨である旨をログ
        result = self.write(rows_in_period)  # 新メソッドに処理を委譲
        return result.written  # 旧API互換：書き込んだ件数だけ返す
    