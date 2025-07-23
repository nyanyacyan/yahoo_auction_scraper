# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$%$$$$$$$$$$$$$$$$$$$
# import
import logging
from typing import List, Dict, Any
import gspread

logger = logging.getLogger(__name__)
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

# **********************************************************************************
# class定義
class SpreadsheetWriter:
    """
    Yahoo!オークションの商品情報を1行ずつGoogleスプレッドシートへ書き込むクラス
    """
    # ------------------------------------------------------------------------------
    # 関数定義
    def __init__(self, worksheet: gspread.Worksheet):
        """
        :param worksheet: 書き込み先 gspread ワークシートオブジェクト
        """
        self.worksheet = worksheet
    # ------------------------------------------------------------------------------
    # 関数定義
    def _find_first_empty_row(self) -> int:
        """
        A列(日付列)で最初に空のセルが現れる行番号を取得
        :return: 1始まりの行番号
        """
        try:
            dates = self.worksheet.col_values(1)
            for idx, val in enumerate(dates, 1):  # 1始まり
                if not val:
                    return idx
            return len(dates) + 1  # 末尾に追記
        except Exception as e:
            logger.error(f"A列の空セル検索に失敗: {e}")
            raise
    # ------------------------------------------------------------------------------
    # 関数定義
    def write_record(self, record: Dict[str, Any]):
        """
        1レコード分のデータを書き込む
        :param record: 商品情報（date, title, price, ct, 1ct_price, image）
        """
        try:
            # 画像は =IMAGE("url", 4, 80, 80) に加工
            image_url = record.get("image", "")
            if image_url and not image_url.startswith("=IMAGE"):
                image_cell = f'=IMAGE("{image_url}", 4, 80, 80)'
            elif image_url:
                image_cell = image_url  # すでに=IMAGE形式ならそのまま
            else:
                image_cell = ""

            # データ整形（列順に注意）
            row_data = [
                str(record.get("date", "")),  # A列: 日付
                record.get("title", ""),      # B列: タイトル
                record.get("price", ""),      # C列: 価格
                record.get("ct", ""),         # D列: カラット
                record.get("1ct_price", ""),  # E列: 1ct単価
                image_cell,                   # F列: 画像
            ]

            # 書き込み開始行取得
            start_row = self._find_first_empty_row()
            start_cell = f"A{start_row}"
            logger.info(f"スプレッドシート書き込み行: {start_row}, データ: {row_data}")

            # 1行ぶんだけ2次元リストでupdate
            # self.worksheet.update(start_cell, [row_data], value_input_option="USER_ENTERED")
            # ✅ 日付だけ文字列化して左寄せにする
            row_data[0] = f"'{row_data[0]}"  # 頭にシングルクォート

            # ✅ 書き込みは USER_ENTERED のまま（画像数式も反映させるため）
            self.worksheet.update(start_cell, [row_data], value_input_option="USER_ENTERED")
            logger.info(f"スプレッドシート書き込み成功: {row_data}")
            logger.info(f"スプレッドシート書き込み成功: {row_data}")
        except Exception as e:
            logger.error(f"スプレッドシート書き込み失敗: {e}")
            raise