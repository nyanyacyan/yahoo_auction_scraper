# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$%$$$$$$$$$$$$$$$$$$$
# import
<<<<<<< HEAD


# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$


# **********************************************************************************
# class定義


    # ------------------------------------------------------------------------------
    # 関数定義


    # ------------------------------------------------------------------------------
    # 関数定義


    # ------------------------------------------------------------------------------

# **********************************************************************************
=======
import logging  # ログ出力用（エラーや進捗管理、デバッグに必須）

logger = logging.getLogger(__name__)  # このファイル専用のロガーを取得
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$%$$$$$$$$$$$$$$$$$$$

# **********************************************************************************
# class定義
class WriteGssFlow:

    # ------------------------------------------------------------------------------
    # 関数定義
    def __init__(self, worksheet):
        # コンストラクタ。書き込み対象のworksheetオブジェクト（gspreadのWorksheetなど）を受け取る
        self.worksheet = worksheet

    # ------------------------------------------------------------------------------
    # 関数定義
    def format_image_formula(self, url):
        # Google SheetsのIMAGE関数を作る（セルに画像を埋め込む用途。サイズ指定あり）
        # =IMAGE("画像URL", 4, 80, 80) → 4はカスタムサイズ指定、80x80px
        return f'=IMAGE("{url}", 4, 80, 80)'

    # ------------------------------------------------------------------------------
    # 関数定義
    def find_first_empty_row(self):
        # シートのA列（1列目）を上から順にチェックし、最初に空になる行番号を返す
        # col_values(1)でA列の全値をリスト取得。既存行数+1が最初の空行
        values = self.worksheet.col_values(1)
        return len(values) + 1

    # ------------------------------------------------------------------------------
    # 関数定義
    def build_write_list(self, records):
        # records（辞書リスト）から、シート書き込み用の2次元リスト（行リスト）を作る
        write_list = []
        for rec in records:  # 1件ずつ処理
            # 日付は空・None・空白なら空文字列にして日付変換エラー回避
            date_value = rec.get('date')
            if not date_value or str(date_value).strip() == "":
                safe_date = ""
            else:
                # 先頭に'をつけて文字列化（日付変換防止）
                safe_date = f"'{date_value}"

            # 他のフィールドは存在しなければ空文字にフォールバック
            title = rec.get("title", "")
            price = rec.get("price", "")
            ct = rec.get("ct", "")
            ct_price = rec.get("1ct_price", "")
            image_url = rec.get("image", "")

            # IMAGE関数用の安全な画像URL
            image_formula = self.format_image_formula(image_url) if image_url else ""

            row = [
                safe_date,
                title,
                price,
                ct,
                ct_price,
                image_formula
            ]
            write_list.append(row)
        return write_list  # 2次元リスト（[行][列]）

    # ------------------------------------------------------------------------------
    # 関数定義
    def run(self, records):
        # このフローの実行本体。渡されたレコードリストをシートにまとめて書き込む
        logger.info("WriteGssFlow: データの書き込みフローを開始します")
        write_list = self.build_write_list(records)  # まずデータを2次元リストに変換
        start_row = self.find_first_empty_row()      # 書き込み開始位置（A列の一番下）を特定
        start_cell = f"A{start_row}"                 # "A5" のような開始セル文字列
        # 指定セルから下に向かってwrite_listを書き込む（value_input_option="USER_ENTERED"で式も有効）
        self.worksheet.update(start_cell, write_list, value_input_option="USER_ENTERED")
        logger.info(f"スプレッドシート書き込み成功: {len(write_list)}件")
# **********************************************************************************



























# # $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$%$$$$$$$$$$$$$$$$$$$
# # import
# import logging  # ログ出力用（エラーや進捗管理、デバッグに必須）

# logger = logging.getLogger(__name__)  # このファイル専用のロガーを取得
# # $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$%$$$$$$$$$$$$$$$$$$$

# # **********************************************************************************
# # class定義
# class WriteGssFlow:

#     # ------------------------------------------------------------------------------
#     # 関数定義
#     def __init__(self, worksheet):
#         # コンストラクタ。書き込み対象のworksheetオブジェクト（gspreadのWorksheetなど）を受け取る
#         self.worksheet = worksheet

#     # ------------------------------------------------------------------------------
#     # 関数定義
#     def format_image_formula(self, url):
#         # Google SheetsのIMAGE関数を作る（セルに画像を埋め込む用途。サイズ指定あり）
#         # =IMAGE("画像URL", 4, 80, 80) → 4はカスタムサイズ指定、80x80px
#         return f'=IMAGE("{url}", 4, 80, 80)'

#     # ------------------------------------------------------------------------------
#     # 関数定義
#     def find_first_empty_row(self):
#         # シートのA列（1列目）を上から順にチェックし、最初に空になる行番号を返す
#         # col_values(1)でA列の全値をリスト取得。既存行数+1が最初の空行
#         values = self.worksheet.col_values(1)
#         return len(values) + 1

#     # ------------------------------------------------------------------------------
#     # 関数定義
#     def build_write_list(self, records):
#         # records（辞書リスト）から、シート書き込み用の2次元リスト（行リスト）を作る
#         write_list = []
#         for rec in records:  # 1件ずつ処理
#             row = [
#                 f"'{rec['date']}",                   # 日付（先頭に'をつけて文字列化し日付変換を防止）
#                 rec["title"],                        # 商品タイトル
#                 rec["price"],                        # 価格
#                 rec["ct"],                           # カラット数
#                 rec["1ct_price"],                    # 1ctあたり価格
#                 self.format_image_formula(rec["image"])  # 画像URLをIMAGE関数に変換して埋め込み
#             ]
#             write_list.append(row)  # 行ごとに追加
#         return write_list  # 2次元リスト（[行][列]）

#     # ------------------------------------------------------------------------------
#     # 関数定義
#     def run(self, records):
#         # このフローの実行本体。渡されたレコードリストをシートにまとめて書き込む
#         logger.info("WriteGssFlow: データの書き込みフローを開始します")
#         write_list = self.build_write_list(records)  # まずデータを2次元リストに変換
#         start_row = self.find_first_empty_row()      # 書き込み開始位置（A列の一番下）を特定
#         start_cell = f"A{start_row}"                 # "A5" のような開始セル文字列
#         # 指定セルから下に向かってwrite_listを書き込む（value_input_option="USER_ENTERED"で式も有効）
#         self.worksheet.update(start_cell, write_list, value_input_option="USER_ENTERED")
#         logger.info(f"スプレッドシート書き込み成功: {len(write_list)}件")
# # **********************************************************************************