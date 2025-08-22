# ==========================================================
# imports  # 標準/外部/プロジェクト内モジュールを読み込む宣言

import os  # 環境変数の取得やパス操作に使用
import sys  # 実行環境情報やバンドル実行（PyInstaller）時のパス取得に使用
import json  # JSON文字列⇔Python辞書の相互変換に使用
import base64  # base64エンコード/デコード（認証情報の埋め込み取得に使用）
import logging  # ログ出力（情報/警告/エラーの記録）に使用
from pathlib import Path  # ファイルパス操作をオブジェクト指向的に扱う
from typing import Optional, List, Dict, Any  # 型ヒント用（可読性と保守性向上）
import pandas as pd  # 表形式データの扱い（DataFrame）に使用
import gspread  # Google Sheets API を扱うためのラッパーライブラリ
from google.oauth2.service_account import Credentials  # サービスアカウント認証用のクレデンシャル
from gspread.exceptions import GSpreadException  # gspread特有の例外クラス
from installer.src.const import sheets as C_SHEET  # スプレッドシート関連の定数（列名/スコープ/環境変数名など）


# ==========================================================
# ログ設定  # このモジュール専用のロガーを取得する

logger: logging.Logger = logging.getLogger(__name__)  # モジュール名付きロガー（ハンドラ/レベルは上位で設定想定）


# ==========================================================
# class定義

class SpreadsheetReader:  # 認証/接続の共通化と行データ取得の責務を持つクラス
    """
    Google スプレッドシートの読み取り／ワークシート取得ユーティリティ。
    - 認証は _build_credentials → _authorize に集約
    - gspread.Client はクラス変数で共有・再利用
    - シート名/列名/認証スコープ/環境変数キー等は const(sheet.py) で一元管理
    """
        # 上記docstringはクラスの役割と設計方針の要約（処理には影響しない）

    _shared_client: Optional["gspread.Client"] = None  # 認証済みクライアントの共有キャッシュ
    _shared_key: Optional[str] = None  # 共有クライアントの識別用キー（認証ファイルパスなど）

    # ==========================================================
    # コンストラクタ

    def __init__(  # SpreadsheetReaderの初期化
        self,
        spreadsheet_id: str,  # 参照対象のスプレッドシートID
        credentials_path: Optional[str] = None,  # 認証ファイルの明示パス（省略可）
        worksheet_name: Optional[str] = None,  # 生成時に取得するワークシート名（省略可）
    ) -> None:
        self.spreadsheet_id: str = spreadsheet_id  # インスタンスにシートIDを保持

        # 既定: {repo_root}/config/credentials.json（constで定義）  # 認証ファイルの既定パスを構築
        default_credentials_path: Path = C_SHEET.default_credentials_path()  # 既定の資格情報パスを取得
        self.credentials_path: Path = Path(credentials_path) if credentials_path else default_credentials_path  # 指定があれば優先

        self._client: Optional[gspread.Client] = None  # 認証クライアントのインスタンスキャッシュ
        self._ws: Optional[gspread.Worksheet] = None  # 直近で取得したワークシートのキャッシュ

        if worksheet_name:  # 生成時に特定ワークシートが必要な場合
            self._ws = self.get_worksheet(worksheet_name)  # ワークシートを取得してキャッシュ


    # ==========================================================
    # メソッド定義

    def get_dataframe(self, worksheet_name: str) -> pd.DataFrame:  # 指定ワークシートをDataFrameで返す
        """指定ワークシートを DataFrame で返す"""  # 関数の目的を短く説明
        client: gspread.Client = self._get_client()  # 認証済みクライアントを取得（共有キャッシュ優先）
        spreadsheet: gspread.Spreadsheet = client.open_by_key(self.spreadsheet_id)  # シートIDからSpreadsheetオブジェクトを開く
        worksheet: gspread.Worksheet = spreadsheet.worksheet(worksheet_name)  # 対象のワークシートを取得
        sheet_values: List[List[str]] = worksheet.get_all_values()  # すべてのセル値を2次元配列として取得
        if not sheet_values:  # 空シートの場合
            return pd.DataFrame()  # 空のDataFrameを返す
        header: List[str]  # 1行目をヘッダとして型ヒントを明示
        rows: List[List[Any]]  # 2行目以降はデータ行
        header, *rows = sheet_values  # アンパックしてヘッダと行データに分離
        return pd.DataFrame(rows, columns=header)  # ヘッダを列名に指定してDataFrame化


    # ==========================================================
    # メソッド定義

    def get_search_conditions(  # 検索条件を辞書のリストで返す
        self,
        worksheet_name: str = C_SHEET.MASTER_SHEET_NAME  # 既定はマスタシート名（定数管理）
    ) -> List[Dict[str, Any]]:
        """
        検索条件を List[Dict[str, Any]] で返す。
        - start_date / end_date が空の行は除外（列名は const で管理）
        - `check` が TRUE の行だけを採用（TRUE のみ。その他の真値表現は不可）
        """
        df: pd.DataFrame = self.get_dataframe(worksheet_name)  # 対象シートをDataFrameとして取得
        if df.empty:  # シートが空なら
            return []  # 空リストを返して終了

        # 必須列の存在チェック  # 主要な列が揃っているかを検証
        required_columns = {C_SHEET.COL_START_DATE, C_SHEET.COL_END_DATE}  # 必須列名の集合
        if not required_columns.issubset(df.columns):  # 必須列が欠けている場合
            logger.error(  # 何が足りないかをログに記録
                f"{worksheet_name} に必須列が見つかりません: required={required_columns}, actual={set(df.columns)}"
            )
            return []  # 不備があるので空結果を返す

        # 必須列の空行を除外  # start/endのいずれかが空の行は対象外
        df = df[df[C_SHEET.COL_START_DATE].astype(str).str.strip() != ""]  # 文字列化して空白のみも除外
        df = df[df[C_SHEET.COL_END_DATE].astype(str).str.strip() != ""]  # 同様にend_dateもフィルタ
        total_after_required_filter = len(df)  # フィルタ後の総件数を記録（ログ用）

        # check=TRUE のみを通す（列名も const 管理）  # チェック列があればTRUEのみを採用
        if C_SHEET.COL_CHECK in df.columns:  # チェック列の有無を確認
            df = df[df[C_SHEET.COL_CHECK].map(C_SHEET.is_true_only)]  # TRUE以外は除外（関数で厳格判定）
            logger.info(  # 採用件数をログ出力
                f"検索条件データ取得完了（{C_SHEET.COL_CHECK}=TRUE のみ）: {len(df)}/{total_after_required_filter}件"
            )
        else:  # チェック列が存在しない場合
            logger.warning(  # TRUEフィルタが適用できない旨を通知
                f"{worksheet_name} に '{C_SHEET.COL_CHECK}' 列が見つかりません。TRUEフィルタ未適用で全行対象になります。"
            )

        condition_records: List[Dict[str, Any]] = df.to_dict(orient="records")  # 各行を辞書化してリストにする
        return condition_records  # フィルタ済みの条件レコードを返す

    # 後方互換の別名  # 旧コード向けに同機能の関数名を残す
    get_conditions = get_search_conditions  # get_conditionsで呼んでもget_search_conditionsを実行


    # ==========================================================
    # メソッド定義

    def get_worksheet(self, name: str) -> "gspread.Worksheet":  # ワークシート名からWorksheetを返す
        client: gspread.Client = self._get_client()  # 認証クライアントを取得
        spreadsheet: gspread.Spreadsheet = client.open_by_key(self.spreadsheet_id)  # Spreadsheetを開く
        return spreadsheet.worksheet(name)  # 指定名のWorksheetを返す


    # ==========================================================
    # メソッド定義

    def get_worksheet_by_index(self, index: int) -> "gspread.Worksheet":  # インデックスでWorksheetを取得
        client: gspread.Client = self._get_client()  # 認証クライアントを取得
        spreadsheet: gspread.Spreadsheet = client.open_by_key(self.spreadsheet_id)  # Spreadsheetを開く
        return spreadsheet.get_worksheet(index)  # 指定位置のWorksheetを返す


    # ==========================================================
    # メソッド定義

    def read_as_dataframe(self, sheet_name: str) -> pd.DataFrame:  # レコード形式で取得しDataFrame化
        """指定シートを DataFrame で返す（ヘッダ1行前提）。"""  # get_all_recordsは1行目をヘッダ前提とする
        worksheet: gspread.Worksheet = self.get_worksheet(sheet_name)  # Worksheetを取得
        rows: List[Dict[str, Any]] = worksheet.get_all_records()  # 各行を辞書として取得
        return pd.DataFrame(rows)  # 辞書リストをDataFrameに変換


    # ==========================================================
    # メソッド定義

    def _get_client(self) -> "gspread.Client":  # 認証済みクライアントを取得（必要なら作成）
        """認証クライアントを取得（共有キャッシュを優先）。"""  # 既存キャッシュの再利用で高速化
        if self._client is not None:  # インスタンス内に既にある場合
            return self._client  # それを返す

        credentials_key: str = str(self.credentials_path) if self.credentials_path else "<default-credentials>"  # 識別キー

        if SpreadsheetReader._shared_client is not None and SpreadsheetReader._shared_key == credentials_key:  # 共有が使えるか
            logger.debug("Google Sheets API: 既存クライアントを再利用します。")  # 再利用を通知
            self._client = SpreadsheetReader._shared_client  # 共有をインスタンスにも反映
            return self._client  # 返却

        client: gspread.Client = self._authorize()  # 新規に認証してクライアントを作成
        SpreadsheetReader._shared_client = client  # クラス共有に格納
        SpreadsheetReader._shared_key = credentials_key  # 共有キーも更新
        self._client = client  # インスタンスにも格納
        return client  # 認証済みクライアントを返す


    # ==========================================================
    # メソッド定義

    def _authorize(self) -> "gspread.Client":  # 認証処理の実体（初回または再認証）
        # 共有が既にあればそれを使う（静かに）  # 二重認証を避ける
        if SpreadsheetReader._shared_client is not None:  # 既存クライアントがある場合
            self._client = SpreadsheetReader._shared_client  # それを利用
            logger.debug("Google Sheets API: 既存クライアントを再利用します。")  # 再利用ログ
            return self._client  # 共有クライアントを返す

        # 初回認証  # ここから実際の認証フロー
        logger.info("Google Sheets APIの認証処理を開始します。")  # 認証開始を通知
        try:  # 例外に備える
            credentials, source = self._build_credentials()  # 資格情報と取得元の説明を得る
            client: gspread.Client = gspread.authorize(credentials)  # gspreadで認可済みクライアントを生成

            SpreadsheetReader._shared_client = client  # 共有に保存
            self._client = client  # インスタンスにも保存

            logger.info(f"Google Sheets APIの認証に成功しました。（{source}）")  # どの経路で認証したかログ
            return client  # 認証済みクライアントを返す
        except Exception as e:  # 認証失敗時
            logger.error(f"Google認証時にエラー: {e}")  # エラー内容を記録
            raise  # 例外を上位へ


    # ==========================================================
    # メソッド定義

    def _build_credentials(self) -> tuple[Credentials, str]:  # 認証情報の構築（複数の取得経路に対応）
        """
        認証情報を作って返す。戻り値は (credentials, source)。
        優先度:
        1) GOOGLE_CREDENTIALS_JSON         … JSON文字列
        2) GOOGLE_CREDENTIALS_JSON_B64     … base64エンコードJSON
        3) GOOGLE_APPLICATION_CREDENTIALS  … ファイルパス
        4) self.credentials_path            … 既定 (config/credentials.json)
        5) PyInstaller / exe 近傍           … config/credentials.json
        """
        scopes: List[str] = C_SHEET.GSPREAD_SCOPES  # Sheets APIで必要なスコープリスト（定数で一元管理）

        # 1) そのまま JSON 文字列  # 環境変数にJSON全文が入っている場合
        raw_json: Optional[str] = os.environ.get(C_SHEET.ENV_JSON)  # JSON文字列の環境変数を取得
        if raw_json:  # 値があれば
            credentials_info: Dict[str, Any] = json.loads(raw_json)  # JSON文字列を辞書へデコード
            return Credentials.from_service_account_info(credentials_info, scopes=scopes), "環境変数 JSON"  # クレデンシャル作成

        # 2) base64 で埋め込み  # 環境変数にbase64で埋め込まれている場合
        b64_credentials: Optional[str] = os.environ.get(C_SHEET.ENV_B64)  # base64文字列の環境変数
        if b64_credentials:  # 値があれば
            decoded_data = base64.b64decode(b64_credentials)  # base64をデコード
            credentials_info = json.loads(decoded_data.decode("utf-8"))  # UTF-8文字列としてJSONデコード
            return Credentials.from_service_account_info(credentials_info, scopes=scopes), "環境変数 base64"  # 作成して返す

        # 3) パス指定（環境変数）  # 環境変数に認証ファイルパスが指定されている場合
        credentials_path_env: Optional[str] = os.environ.get(C_SHEET.ENV_FILE)  # パス用の環境変数を取得
        if credentials_path_env and Path(credentials_path_env).exists():  # パスが存在するか確認
            return Credentials.from_service_account_file(credentials_path_env, scopes=scopes), f"指定ファイル: {credentials_path_env}"  # ファイルから作成

        # 4) __init__ で決めたパス  # インスタンス生成時に決めた既定パスを利用
        if self.credentials_path and Path(self.credentials_path).exists():  # 既定パスが存在する場合
            return Credentials.from_service_account_file(self.credentials_path, scopes=scopes), f"指定ファイル: {self.credentials_path}"  # 作成して返す

        # 5) exe/バンドル近傍（PyInstaller 想定）  # バンドル実行時の同梱ファイル候補を探す
        credential_candidates: List[Path] = []  # 探索候補のパスリスト
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):  # PyInstallerでバンドルされている場合
            credential_candidates.append(Path(sys._MEIPASS) / "config" / "credentials.json")  # type: ignore[attr-defined]  # バンドル内のconfigを候補に追加
        exe: str = getattr(sys, "executable", "")  # 実行バイナリのパス（バンドル時など）
        if exe:  # 実行ファイルパスが得られた場合
            credential_candidates.append(Path(exe).resolve().parent / "config" / "credentials.json")  # 近傍configを候補に追加

        for candidate_path in credential_candidates:  # 候補を順に確認
            if candidate_path.exists():  # 実在する場合
                return Credentials.from_service_account_file(candidate_path, scopes=scopes), f"同梱ファイル: {candidate_path}"  # そのファイルから作成

        error_message: str = (  # いずれの方法でも認証情報が見つからない場合のメッセージ
            "認証情報が見つかりませんでした。"
            f"{C_SHEET.ENV_JSON}（JSON）/ {C_SHEET.ENV_B64}（base64）/ "
            f"{C_SHEET.ENV_FILE}（パス）を設定するか、config/credentials.json を同梱してください。"
        )
        logger.error(error_message)  # 詳細なエラーメッセージをログ
        raise RuntimeError(error_message)  # 呼び出し側に明示的な失敗として通知
    