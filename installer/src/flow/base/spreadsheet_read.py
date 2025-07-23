import os
import logging
from typing import List, Dict, Any
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import GSpreadException

logger = logging.getLogger(__name__)

class SpreadsheetReader:
    """
    Googleスプレッドシートからデータフレーム形式で検索条件情報を取得するクラス
    """

    def __init__(
        self,
        spreadsheet_id: str,
        worksheet_name: str,
        credentials_path: str = "installer/config/credentials.json"
    ):
        logger.debug("SpreadsheetReaderの初期化: spreadsheet_id=%s, worksheet_name=%s, credentials_path=%s",spreadsheet_id, worksheet_name, credentials_path)
        self.spreadsheet_id = spreadsheet_id
        self.worksheet_name = worksheet_name
        self.credentials_path = credentials_path
        self._client = None

    def _authorize(self):
        logger.info("Google Sheets APIの認証処理を開始します。")
        try:
            if not os.path.exists(self.credentials_path):
                logger.error(f"認証ファイルが見つかりません: {self.credentials_path}")
                raise FileNotFoundError(f"credentials.json not found at {self.credentials_path}")

            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
                ]
            credentials = Credentials.from_service_account_file(
                self.credentials_path,
                scopes=scopes
            )
            self._client = gspread.authorize(credentials)
            logger.info("Google Sheets APIの認証に成功しました。")
        except Exception as e:
            logger.error(f"Google認証時にエラー: {e}")
            raise

    def get_search_conditions(self) -> List[Dict[str, Any]]:
        logger.info("検索条件データの取得処理を開始します。")
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
            logger.debug(f"DataFrame情報: shape={df.shape}")

            return df.to_dict(orient="records")
        except GSpreadException as ge:
            logger.error(f"gspread APIエラー: {ge}")
            raise
        except Exception as e:
            logger.error(f"スプレッドシート読取時にエラー: {e}")
            raise

    def get_dataframe(self) -> pd.DataFrame:
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
            print()
        except Exception as e:
            logger.error(f"DataFrame取得時にエラー: {e}")
            raise
        
    def get_worksheet(self, sheet_name: str) -> gspread.Worksheet:
        """
        認証後に指定ワークシートオブジェクトを返す
        """
        logger.info(f"ワークシート[{sheet_name}]を取得します。")
        if self._client is None:
            self._authorize()

        spreadsheet = self._client.open_by_key(self.spreadsheet_id)
        worksheet = spreadsheet.worksheet(sheet_name)
        return worksheet