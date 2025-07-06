# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$%$$$$$$$$$$$$$$$$$$$
# import
import os
import logging
from typing import List, Dict, Any
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import GSpreadException

logger = logging.getLogger(__name__)
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

# **********************************************************************************
# class定義
class SpreadsheetReader:
    """
    Googleスプレッドシートからデータフレーム形式で検索条件情報を取得するクラス
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
        Args:
            spreadsheet_id (str): スプレッドシートのID（URLの一部）
            worksheet_name (str): 取得対象のワークシート名
            credentials_path (str): サービスアカウントキーのパス
        """
        self.spreadsheet_id = spreadsheet_id
        self.worksheet_name = worksheet_name
        self.credentials_path = credentials_path
        self._client = None
    # ------------------------------------------------------------------------------
    # 関数定義
    def _authorize(self):
        """
        Google認証 & gspreadクライアント生成
        """
        try:
            if not os.path.exists(self.credentials_path):
                logger.error(f"認証ファイルが見つかりません: {self.credentials_path}")
                raise FileNotFoundError(f"credentials.json not found at {self.credentials_path}")

            scopes = [
                "https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/drive.readonly"
            ]
            credentials = Credentials.from_service_account_file(
                self.credentials_path,
                scopes=scopes
            )
            self._client = gspread.authorize(credentials)
        except Exception as e:
            logger.error(f"Google認証時にエラー: {e}")
            raise
    # ------------------------------------------------------------------------------
    # 関数定義
    def get_search_conditions(self) -> List[Dict[str, Any]]:
        """
        検索条件情報を辞書リスト形式で取得

        Returns:
            List[Dict[str, Any]]: 検索条件データの辞書リスト
        """
        try:
            if self._client is None:
                self._authorize()

            # スプレッドシートとワークシートを取得
            spreadsheet = self._client.open_by_key(self.spreadsheet_id)
            worksheet = spreadsheet.worksheet(self.worksheet_name)

            # データ取得（ヘッダー付き）
            records = worksheet.get_all_records()
            df = pd.DataFrame(records)

            # 必要に応じて空行・不正行除去などの前処理を追加可
            # df = df.dropna(how="all")  # 全てNaNの行を削除

            return df.to_dict(orient="records")
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
        検索条件情報をDataFrameで取得

        Returns:
            pd.DataFrame: 検索条件データ
        """
        try:
            if self._client is None:
                self._authorize()
            spreadsheet = self._client.open_by_key(self.spreadsheet_id)
            worksheet = spreadsheet.worksheet(self.worksheet_name)
            records = worksheet.get_all_records()
            df = pd.DataFrame(records)
            return df
        except Exception as e:
            logger.error(f"DataFrame取得時にエラー: {e}")
            raise
    # ------------------------------------------------------------------------------
# **********************************************************************************