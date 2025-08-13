# ==========================================================
# imports

import os  # OS機能（環境変数・パス存在確認など）を使うための標準ライブラリ
import sys  # 実行環境情報（PyInstaller判定など）にアクセスするための標準ライブラリ
import json  # JSON文字列⇄Pythonオブジェクトの変換に使用
import base64  # base64エンコード/デコードに使用（資格情報の安全な埋め込み向け）
import logging  # ログ出力（情報・警告・エラー）のための標準ライブラリ
from pathlib import Path  # パス操作を高機能に扱うためのユーティリティ
from typing import Optional, List, Dict, Any  # 型ヒント用（可読性・保守性の向上）
import pandas as pd  # 表データの扱い（DataFrame変換など）に使用
import gspread  # Google Sheets API のPythonクライアント
from google.oauth2.service_account import Credentials  # サービスアカウント認証用のクラス
from gspread.exceptions import GSpreadException  # gspread で発生する一般的な例外クラス



# ==========================================================
# ログ設定

logger = logging.getLogger(__name__)  # このモジュール専用のロガーを取得



# ==========================================================
# class定義

class SpreadsheetReader:  # スプレッドシートの読み取りとワークシート取得を担うユーティリティクラス
    """
    Google スプレッドシートの読み取り／ワークシート取得ユーティリティ。
    - 認証は _build_credentials → _authorize に集約
    - gspread.Client はクラス変数で共有・再利用
    """  # ドキュメンテーション文字列：クラスの目的と設計方針を説明

    _shared_client: Optional["gspread.Client"] = None  # 認証済みクライアントの共有キャッシュ（全インスタンス共通）
    _shared_key: Optional[str] = None  # 共有クライアントが有効かを判定するためのキー（資格情報パスなどの識別子）



    # ==========================================================
    # コンストラクタ（インスタンス生成時に実行）

    def __init__(  # インスタンス生成時の初期化処理
        self,
        spreadsheet_id: str,  # 操作対象のスプレッドシートID（必須）
        credentials_path: Optional[str] = None,  # 資格情報JSONのパス（省略可：既定パスを使用）
        worksheet_name: Optional[str] = None,  # すぐにワークシートを開く場合のシート名（省略可）
    ) -> None:
        self.spreadsheet_id = spreadsheet_id  # 渡されたスプレッドシートIDを保持

        # 既定: {repo_root}/installer/config/credentials.json
        default_path = Path(__file__).resolve().parents[3] / "config" / "credentials.json"  # 既定の資格情報パスを算出
        self.credentials_path = Path(credentials_path) if credentials_path else default_path  # 指定がなければ既定パスを使用

        self._client: Optional[gspread.Client] = None  # インスタンス固有のクライアント参照（未取得ならNone）
        self._ws: Optional[gspread.Worksheet] = None  # 直近で取得したワークシートの保持用（必要に応じて利用）

        if worksheet_name:  # コンストラクタでワークシート名が渡された場合
            # ここで client を必ず確保
            self._ws = self.get_worksheet(worksheet_name)  # 先にクライアントを確保し、指定シートを開いて保持する



    # ==========================================================
    # メソッド定義

    def get_dataframe(self, worksheet_name: str) -> pd.DataFrame:  # 指定ワークシートを DataFrame にして返す
        """指定ワークシートを DataFrame で返す"""  # 簡単な説明（ヘッダ行前提）
        client = self._get_client()  # ← self._client を内部で用意・共有
        sh = client.open_by_key(self.spreadsheet_id)  # スプレッドシートIDからブックを開く
        ws = sh.worksheet(worksheet_name)  # 指定名のワークシートを取得
        values = ws.get_all_values()  # 全セルの文字列値を2次元配列で取得
        if not values:  # 値が空の場合（シートが空など）
            return pd.DataFrame()  # 空のDataFrameを返す
        header, *rows = values  # 先頭行をヘッダ、それ以降をデータ行として分割
        return pd.DataFrame(rows, columns=header)  # ヘッダを列名としてDataFrame化



    # ==========================================================
    # メソッド定義

    def get_search_conditions(self, worksheet_name: str = "Master") -> list[dict]:  # 検索条件を辞書リストで返す
        """検索条件を List[Dict] で返す（空行を除去）"""  # 説明：必須列が空の行は除外
        df = self.get_dataframe(worksheet_name)  # 指定シートをDataFrame取得
        if df.empty:  # データが空なら
            return []  # 空リストで返す
        # 必須列（start_date/end_date）が空の行は落とす
        df = df[df["start_date"].astype(str).str.strip() != ""]  # start_date が空文字の行を除外
        df = df[df["end_date"].astype(str).str.strip() != ""]  # end_date が空文字の行を除外
        records = df.to_dict(orient="records")  # 行ごとに辞書化（列名→値）
        logger.info(f"検索条件データ取得完了。取得件数: {len(records)}件")  # 取得件数を情報ログで出力
        return records  # 整形後のレコード群を返す
    get_conditions = get_search_conditions  # 別名メソッド（後方互換や可読性のため）



    # ==========================================================
    # メソッド定義

    def get_worksheet(self, name: str) -> "gspread.Worksheet":  # ワークシート名からWorksheetオブジェクトを取得
        client = self._get_client()  # 認証済みクライアントを取得（共有キャッシュを活用）
        sh = client.open_by_key(self.spreadsheet_id)  # スプレッドシートを開く
        return sh.worksheet(name)  # 指定名のワークシートを返す



    # ==========================================================
    # メソッド定義

    def get_worksheet_by_index(self, index: int) -> "gspread.Worksheet":  # インデックス番号でワークシート取得
        client = self._get_client()  # クライアントを取得
        sh = client.open_by_key(self.spreadsheet_id)  # ブックを開く
        return sh.get_worksheet(index)  # 指定インデックスのワークシートを返す



    # ==========================================================
    # メソッド定義

    def read_as_dataframe(self, sheet_name: str) -> pd.DataFrame:  # 1行目をヘッダとしてDataFrame化して返す
        """指定シートを DataFrame で返す（ヘッダ1行前提）。"""  # ヘッダ行がある想定
        ws = self.get_worksheet(sheet_name)  # ワークシートを取得
        rows = ws.get_all_records()  # 1行目をヘッダとして各行を辞書化
        return pd.DataFrame(rows)  # 辞書リストからDataFrameを作成



    # ==========================================================
    # メソッド定義

    def _get_client(self) -> "gspread.Client":  # 認証クライアントを取得（共有キャッシュ優先）
        """認証クライアントを取得（共有キャッシュを優先）。"""  # 内部利用のための説明
        if self._client is not None:  # 既にインスタンス内に保持している場合
            return self._client  # それを返す

        key = str(self.credentials_path) if self.credentials_path else "<default-credentials>"  # 資格情報識別子を作成

        if SpreadsheetReader._shared_client is not None and SpreadsheetReader._shared_key == key:  # 共有クライアントが使えるか判定
            logger.debug("Google Sheets API: 既存クライアントを再利用します。")  # 再利用の旨をデバッグ出力
            self._client = SpreadsheetReader._shared_client  # 共有クライアントをインスタンスにセット
            return self._client  # クライアントを返す

        # 初回だけ認証
        client = self._authorize()  # 初回は認証実行してクライアントを生成
        SpreadsheetReader._shared_client = client  # 共有キャッシュに格納
        SpreadsheetReader._shared_key = key  # 共有キーを更新
        self._client = client  # インスタンスにもセット
        return client  # 認証済みクライアントを返す



    # ==========================================================
    # メソッド定義

    def _authorize(self) -> "gspread.Client":  # 認証を行い、gspread.Client を返す
        # 共有が既にあればそれを使う（静かに）
        if SpreadsheetReader._shared_client is not None:  # 共有に既存クライアントがある場合
            self._client = SpreadsheetReader._shared_client  # それをインスタンスにも反映
            logger.debug("Google Sheets API: 既存クライアントを再利用します。")  # 再利用ログ（静かめ）
            return self._client  # 共有クライアントを返す

        # ここから先は“初回認証”のみ
        logger.info("Google Sheets APIの認証処理を開始します。")  # 初回認証の開始ログ
        try:
            credentials, source = self._build_credentials()  # 認証情報を環境やファイルから構築
            client = gspread.authorize(credentials)  # gspreadクライアントを認証情報で初期化

            # 共有キャッシュとインスタンス両方に格納
            SpreadsheetReader._shared_client = client  # クラス共有に保存
            self._client = client  # インスタンスにも保存

            logger.info(f"Google Sheets APIの認証に成功しました。（{source}）")  # どの経路で認証したかを明示
            return client  # 認証済みクライアントを返す
        except Exception as e:  # 認証に失敗した場合
            logger.error(f"Google認証時にエラー: {e}")  # エラーログを出力
            raise  # 例外を上位へ再送出



    # ==========================================================
    # メソッド定義

    def _build_credentials(self) -> tuple[Credentials, str]:  # 認証情報（Credentials）と情報源名を返す
        """
        認証情報を作って返す。戻り値は (credentials, source)。
        優先度:
        1) GOOGLE_CREDENTIALS_JSON         … JSON文字列
        2) GOOGLE_CREDENTIALS_JSON_B64     … base64エンコードJSON
        3) GOOGLE_APPLICATION_CREDENTIALS  … ファイルパス
        4) self.credentials_path            … 既定 (installer/config/credentials.json)
        5) PyInstaller / exe 近傍           … config/credentials.json
        """  # 認証情報の探索順序と各手段の説明
        scopes = [  # Sheets/Drive に対するアクセス権限（スコープ）を定義
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        # 1) そのまま JSON 文字列
        raw_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")  # 環境変数にJSON文字列があるか確認
        if raw_json:  # JSON文字列が直接提供されている場合
            info = json.loads(raw_json)  # JSON文字列を辞書に変換
            return Credentials.from_service_account_info(info, scopes=scopes), "環境変数 JSON"  # 情報源名も返す

        # 2) base64 で埋め込み
        b64 = os.environ.get("GOOGLE_CREDENTIALS_JSON_B64")  # base64化されたJSONがあるか確認
        if b64:  # base64提供の場合
            data = base64.b64decode(b64)  # base64をデコード
            info = json.loads(data.decode("utf-8"))  # UTF-8文字列にしてJSON読み込み
            return Credentials.from_service_account_info(info, scopes=scopes), "環境変数 base64"  # 認証情報と情報源名

        # 3) パス指定（環境変数）
        path_env = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")  # 資格情報ファイルパスが環境変数にあるか
        if path_env and Path(path_env).exists():  # パスが存在すれば
            return Credentials.from_service_account_file(path_env, scopes=scopes), f"指定ファイル: {path_env}"  # ファイルから読み込む

        # 4) __init__ で決めたパス
        if self.credentials_path and Path(self.credentials_path).exists():  # コンストラクタで設定したパスが存在する場合
            return Credentials.from_service_account_file(self.credentials_path, scopes=scopes), f"指定ファイル: {self.credentials_path}"  # 既定ファイル

        # 5) exe/バンドル近傍（PyInstaller 想定）
        candidates: list[Path] = []  # 探索候補のパス配列
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):  # PyInstallerでバンドルされた実行形式か判定
            candidates.append(Path(sys._MEIPASS) / "config" / "credentials.json")  # type: ignore[attr-defined]  # バンドル内部の想定パス
        exe = getattr(sys, "executable", "")  # 実行ファイルの場所（バイナリ時）
        if exe:  # 実行ファイルが特定できる場合
            candidates.append(Path(exe).resolve().parent / "config" / "credentials.json")  # exe隣接のconfig/credentials.json

        for c in candidates:  # 候補パスを順にチェック
            if c.exists():  # 見つかった場合
                return Credentials.from_service_account_file(c, scopes=scopes), f"同梱ファイル: {c}"  # そのファイルから認証

        # どれもなければエラー
        msg = (  # エラーメッセージを作成（利用可能な設定方法をガイド）
            "認証情報が見つかりませんでした。"
            "GOOGLE_CREDENTIALS_JSON（JSON）/ GOOGLE_CREDENTIALS_JSON_B64（base64）/ "
            "GOOGLE_APPLICATION_CREDENTIALS（パス）を設定するか、config/credentials.json を同梱してください。"
        )
        logger.error(msg)  # 詳細なエラーをログに出力
        raise RuntimeError(msg)  # 実行継続不能のため例外を送出





# ==============
# 実行の順序
# ==============
# 1. モジュール（os/sys/json/base64/logging/pathlib/typing/pandas/gspread/認証関連）をimportする
# → 後続のファイル操作・環境変数・認証・スプレッドシート処理に必要な機能を読み込む。補足：ここではまだ処理は動かない。

# 2. logger = logging.getLogger(name) を実行する
# → このモジュール専用のロガーを取得する。補足：以降のINFO/DEBUG/ERRORをここに記録する。

# 3. class SpreadsheetReader を定義する
# → スプレッドシートの認証・ワークシート取得・DataFrame化をまとめるユーティリティclass。補足：定義段階では実行されない。

# 4. （class変数）_shared_client / _shared_key を定義する
# → 認証済みgspread.Clientと、その有効性を判定するキーを全インスタンスで共有する。補足：認証の再実行を避けて高速化。

# 5. メソッド init(self, spreadsheet_id, credentials_path=None, worksheet_name=None) を定義する
# → 対象スプレッドシートIDと資格情報パスを保持し、インスタンス用の_client/_wsを初期化する。補足：worksheet_nameがあれば後述のget_worksheetで即取得する。

# 6. （init が呼ばれたとき）既定credentials.jsonのパスを計算し、必要ならself.credentials_pathに採用する
# → 明示パスがなければ {repo_root}/installer/config/credentials.json を使う。補足：worksheet_nameが指定されていれば get_worksheet を呼んで self._ws を先取りする。

# 7. メソッド get_dataframe(self, worksheet_name) を定義する
# → 指定ワークシートを開き、全セル値からヘッダ行つきのDataFrameを作って返す。補足：データが無ければ空のDataFrameを返す。

# 8. （get_dataframe が呼ばれたとき）_get_client→open_by_key→worksheet→get_all_values→DataFrame化の順で処理する
# → 先頭行を列名、以降を行データにして整形する。補足：値は文字列ベースで取得される点に注意。

# 9. メソッド get_search_conditions(self, worksheet_name=“Master”) を定義し、別名 get_conditions も用意する
# → 検索条件シートを読み、空行（start_date/end_dateが空）を除いた辞書リストに変換する。補足：取得件数をINFOログに出す。

# 10. （get_search_conditions が呼ばれたとき）get_dataframe→空文字除外→to_dict(orient=“records”)→return の順で処理する
# → 必須列の欠落行は事前フィルタで弾く。補足：空なら空リストを返して上位判断に委ねる。

# 11. メソッド get_worksheet(self, name) を定義する
# → 認証クライアントを取得してブックを開き、指定名のワークシートオブジェクトを返す。補足：共有クライアントを優先再利用。

# 12. （get_worksheet が呼ばれたとき）_get_client→open_by_key→sh.worksheet(name) の順で取得する
# → 失敗時はgspread側の例外が上がる想定。補足：名前のタイプミスに注意。

# 13. メソッド get_worksheet_by_index(self, index) を定義する
# → インデックス番号でワークシートを取得する。補足：0始まりのインデックスに従う。

# 14. （get_worksheet_by_index が呼ばれたとき）_get_client→open_by_key→sh.get_worksheet(index) で返す
# → インデックス範囲外ならNoneや例外になる実装に依存。補足：存在確認は上位で行う。

# 15. メソッド read_as_dataframe(self, sheet_name) を定義する
# → 1行目をヘッダとして get_all_records で辞書化し、DataFrameに変換する。補足：ヘッダ行がある前提。

# 16. （read_as_dataframe が呼ばれたとき）get_worksheet→get_all_records→pd.DataFrame(rows) を実行する
# → 型は基本文字列になるため必要に応じて後段で型変換する。補足：空シートなら空DataFrame。

# 17. メソッド _get_client(self) を定義する
# → まずインスタンス内の_clientを返し、無ければ共有キャッシュか _authorize() で新規作成する。補足：credentials_pathの文字列をキーに共有を切り替える。

# 18. （_get_client が呼ばれたとき）self._client→共有(_shared_client & _shared_key一致)→_authorize() の順で判定する
# → 新規作成時は共有キャッシュとインスタンス両方に保存し、_shared_keyも更新する。補足：ログで再利用可否をDEBUG出力。

# 19. メソッド _authorize(self) を定義する
# → 共有が既にあればそれを返し、無ければ _build_credentials()→gspread.authorize(…) でクライアントを作る。補足：成功/失敗をINFO/ERRORで記録。

# 20. （_authorize が呼ばれたとき）成功時は共有とインスタンスにクライアントを設定し情報源名もログに残す
# → 失敗時はエラーログを出して例外を再送出する。補足：上位でハンドリング可能にするため握りつぶさない。

# 21. メソッド _build_credentials(self) を定義する
# → 認証スコープ設定後、次の優先順でCredentialsを構築する：①環境変数JSON ②環境変数base64 ③環境変数パス ④self.credentials_path ⑤PyInstaller近傍。補足：どれも無ければRuntimeErrorを送出。

# 22. （_build_credentials が呼ばれたとき）一致した経路でCredentialsを生成し (credentials, source) を返す
# → base64はデコード→JSON化→from_service_account_info、パスはfrom_service_account_fileを使う。補足：見つからない場合は詳細メッセージをログして失敗させる。