# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$%$$$$$$$$$$$$$$$$$$$
# import
import os                  # OSファイル操作用（認証ファイルの存在チェックなどに使用）
import logging             # ログ出力用（進捗・エラー記録）
from typing import List, Dict, Any  # 型ヒント用：List/Dict/Any
import pandas as pd        # データ処理・テーブル化（DataFrame）用途
import gspread             # Google Sheets APIラッパー
from google.oauth2.service_account import Credentials  # サービスアカウント認証用
from gspread.exceptions import GSpreadException        # gspread専用例外（API失敗時など）

logger = logging.getLogger(__name__)  # このファイル専用ロガー（上位でlevel設定が必要）
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$%$$$$$$$$$$$$$$$$$$$


# **********************************************************************************
# class定義
class SpreadsheetReader:
    """
    Googleスプレッドシートからデータフレーム形式で検索条件情報を取得するクラス

    - サービスアカウント認証を用いた安全なAPI利用
    - データ取得はdictリストまたはDataFrameとして取得可能
    - エラー時は全てログ記録＋raise
    """

    # ------------------------------------------------------------------------------
    # 関数定義
    def __init__(
        self,
        spreadsheet_id: str,
        worksheet_name: str,
        credentials_path: str = "installer/config/credentials.json"
    ):
        """
        SpreadsheetReaderインスタンス生成（認証は必要に応じて後で実施）

        :param spreadsheet_id: GoogleスプレッドシートのID（URL中の長い文字列）
        :param worksheet_name: 参照するシート名
        :param credentials_path: サービスアカウント認証jsonファイルのパス
        """
        logger.debug("SpreadsheetReaderの初期化: spreadsheet_id=%s, worksheet_name=%s, credentials_path=%s",spreadsheet_id, worksheet_name, credentials_path)
        self.spreadsheet_id = spreadsheet_id      # スプレッドシートID
        self.worksheet_name = worksheet_name      # シート名
        self.credentials_path = credentials_path  # 認証ファイルパス
        self._client = None                      # gspread認証済みクライアント（初回アクセス時にセット）

    # ------------------------------------------------------------------------------
    # 関数定義
    def _authorize(self):
        """
        Google Sheets APIの認証（gspreadクライアント生成）。
        サービスアカウント認証ファイルが必要。初回アクセス時だけ呼ばれる。
        """
        logger.info("Google Sheets APIの認証処理を開始します。")
        try:
            if not os.path.exists(self.credentials_path):
                # 認証jsonが無い場合はエラー
                logger.error(f"認証ファイルが見つかりません: {self.credentials_path}")
                raise FileNotFoundError(f"credentials.json not found at {self.credentials_path}")

            # Google Sheets/Drive APIへのアクセス権限を指定
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
                ]
            # サービスアカウントで認証トークン生成
            credentials = Credentials.from_service_account_file(
                self.credentials_path,
                scopes=scopes
            )
            # gspread認証済みクライアント生成
            self._client = gspread.authorize(credentials)
            logger.info("Google Sheets APIの認証に成功しました。")
        except Exception as e:
            logger.error(f"Google認証時にエラー: {e}")
            raise

    # ------------------------------------------------------------------------------
    # 関数定義
    def get_search_conditions(self) -> List[Dict[str, Any]]:
        """
        シート内の全データ（1行=1レコード）をdict形式でリスト化し取得する
        :return: [{col1:val1, col2:val2,...}, ...] のリスト
        """
        logger.info("検索条件データの取得処理を開始します。")
        try:
            # 初回のみ認証
            if self._client is None:
                logger.debug("まだ認証されていないため、認証処理を実施します。")
                self._authorize()

            # 指定IDのスプレッドシートを開き、指定シートのWorksheet取得
            spreadsheet = self._client.open_by_key(self.spreadsheet_id)
            worksheet = spreadsheet.worksheet(self.worksheet_name)
            logger.info(f"スプレッドシート[{self.spreadsheet_id}]・シート[{self.worksheet_name}]からデータを取得します。")

            # 全レコードを辞書リスト形式で取得
            records = worksheet.get_all_records()
            logger.info(f"データの取得が完了しました。取得件数: {len(records)}件")
            if records:
                logger.debug(f"先頭レコード例: {records[0]}")  # 1件目を例としてデバッグ出力
            else:
                logger.warning("スプレッドシートのデータが空です。")

            # DataFrameで一旦整形し、recordsで返却（カラム順や整合性確保のため）
            df = pd.DataFrame(records)
            logger.debug(f"DataFrame情報: shape={df.shape}")

            return df.to_dict(orient="records")  # [{カラム:値, ...}, ...]で返却
        except GSpreadException as ge:
            logger.error(f"gspread APIエラー: {ge}")
            raise
        except Exception as e:
            logger.error(f"スプレッドシート読取時にエラー: {e}")
            raise

    # ------------------------------------------------------------------------------
    # 関数定義
    def get_dataframe(self) -> pd.DataFrame:
        """
        シート内データをpandas.DataFrame形式で返す
        :return: DataFrame（1行1レコード）
        """
        logger.info("DataFrame形式で検索条件データを取得します。")
        try:
            if self._client is None:
                logger.debug("まだ認証されていないため、認証処理を実施します。")
                self._authorize()
            spreadsheet = self._client.open_by_key(self.spreadsheet_id)
            worksheet = spreadsheet.worksheet(self.worksheet_name)
            logger.info(f"スプレッドシート[{self.spreadsheet_id}]・シート[{self.worksheet_name}]からデータを取得します。")

            records = worksheet.get_all_records()
            logger.info(f"データの取得が完了しました。取得件数: {len(records)}件")
            if records:
                logger.debug(f"先頭レコード例: {records[0]}")
            else:
                logger.warning("スプレッドシートのデータが空です。")

            df = pd.DataFrame(records)
            logger.debug(f"DataFrame情報:shape={df.shape}")
            return df
            print()  # ※このprint()は実行されません（returnの後なので死文）
        except Exception as e:
            logger.error(f"DataFrame取得時にエラー: {e}")
            raise

    # ------------------------------------------------------------------------------
    # 関数定義
    def get_worksheet(self, sheet_name: str) -> gspread.Worksheet:
        """
        （認証後に）指定名のWorksheetオブジェクトを返す
        :param sheet_name: 取得したいシート名
        :return: gspread.Worksheetインスタンス
        """
        logger.info(f"ワークシート[{sheet_name}]を取得します。")
        if self._client is None:
            self._authorize()

        spreadsheet = self._client.open_by_key(self.spreadsheet_id)
        worksheet = spreadsheet.worksheet(sheet_name)
        return worksheet