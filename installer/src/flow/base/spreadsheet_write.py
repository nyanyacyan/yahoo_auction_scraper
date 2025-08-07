import logging  # ログ出力用

logger = logging.getLogger(__name__)

class SpreadsheetWriter:
    """
    Googleスプレッドシートなどのworksheet（gspread等）への
    行データ書き込みをサポートするユーティリティクラス
    """

    def __init__(self, worksheet):
        """
        :param worksheet: 書き込み対象のworksheet（gspreadのWorksheet等を想定）
        """
        self.worksheet = worksheet

    def find_first_empty_row(self):
        """
        A列（1列目）の最初の空セルの行番号を返す  
        1行目（ヘッダー）は飛ばして、2行目以降のみ対象
        もし全て埋まっていれば、その下の行番号を返す
        :return: 書き込み開始するべき行番号（1始まり）
        """
        col_values = self.worksheet.col_values(1)
        for idx, val in enumerate(col_values[1:], start=2):
            if not val:
                return idx
        return len(col_values) + 1

    def append_rows(self, list_of_lists):
        """
        複数行（list of lists）をシート末尾にまとめて追記する
        :param list_of_lists: [[行1], [行2], ...]
        """
        try:
            # gspread worksheetのappend_rowsを呼び出す（新しいgspreadでサポート）
            result = self.worksheet.append_rows(list_of_lists, value_input_option='USER_ENTERED')
            logger.info(f"{len(list_of_lists)}行を追記しました")
            return result
        except AttributeError:
            # append_rowsが無い場合はappend_rowをループで対応
            for row in list_of_lists:
                self.worksheet.append_row(row, value_input_option='USER_ENTERED')
            logger.info(f"{len(list_of_lists)}行をループで追記しました（append_row）")
            return None