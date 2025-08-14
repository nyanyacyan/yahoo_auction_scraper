# # ==========================================================
# # import（標準、プロジェクト内モジュール）

# import logging  # ログ出力（処理の進捗やエラー確認に使う）



# # ==========================================================
# # ログ設定

# logger = logging.getLogger(__name__)  # このモジュール専用のロガーを取得



# # ==========================================================
# # class定義

# class WriteGssFlow:  # GSS(スプレッドシート)へレコードを追記する小さなフロークラス
#     """
#     役割：抽出済みレコードのリストを、Googleスプレッドシートへ
#     追記（append的に）書き込むための小さなフロー。
#     前提：gspreadのWorksheetオブジェクトを受け取り、updateで一括反映する。
#     """



#     # ==========================================================
#     # コンストラクタ（インスタンス生成時に実行）

#     def __init__(self, worksheet):
#         self.worksheet = worksheet  # 書き込み対象のワークシート（gspread.Worksheet想定）



#     # ==========================================================
#     # メソッド定義

#     def _safe_sheet_text(self, v):
#         # シート上での自動変換（日付/数値化）を避けるため、先頭に'を付与して「文字列」として扱わせる
#         # すでに'で始まっている場合は二重付与しない
#         s = str(v)  # 値を文字列化（Noneや数値でも安全に扱うため）
#         return s if s.startswith("'") else f"'{s}"  # 先頭'有無で分岐し、必要なら付加して返す



#     # ==========================================================
#     # メソッド定義

#     def format_image_formula(self, url_or_formula):
#         # 画像セルに入れる値を統一：
#         # - 既に"=..."で始まる場合は式としてそのまま使用
#         # - URLだけ渡された場合は、=IMAGE(url, 4, 80, 80) 形式に整形（4はカスタムサイズ、80x80）
#         if not url_or_formula:
#             return ""  # 空なら空文字（セルも空のまま）
#         s = str(url_or_formula).strip()  # 前後空白を除去し、文字列として扱う
#         if s.startswith("="):
#             return s  # 既存の式を尊重
#         return f'=IMAGE("{s}", 4, 80, 80)'  # URLを画像式に変換（スプレッドシートで画像表示）



#     # ==========================================================
#     # メソッド定義

#     def find_first_empty_row(self):
#         # 1列目（A列）の現行値を取得し、その件数+1行目を「追記先」と見なす
#         # gspreadのcol_valuesは末尾の空行を返さないため、このロジックで次の空き行が得られる
#         values = self.worksheet.col_values(1)  # A列の全値を取得（ヘッダ含む）
#         return len(values) + 1  # 現在の最終行の次の行番号を返す



#     # ==========================================================
#     # メソッド定義

#     def build_write_list(self, records):
#         # レコード(dict)から、シートに書き込む2次元配列（行のリスト）を生成する
#         # 想定キー: date, title, price, ct, 1ct_price, image または image_url
#         write_list = []  # ここに各行（リスト）を順次追加していく
#         for rec in records:
#             img_src = rec.get("image_url") or rec.get("image") or ""  # image_url優先、無ければimage、無ければ空

#             row = [
#                 self._safe_sheet_text(rec["date"]),   # ' を付けて文字列として保存（シートの自動日付変換対策）
#                 rec["title"],                          # 件名
#                 rec["price"],                          # 価格（数値想定：USER_ENTEREDで数値として入る）
#                 rec["ct"],                             # カラット数
#                 rec["1ct_price"],                      # 1ctあたりの単価
#                 self.format_image_formula(img_src),    # 画像セル：URL→=IMAGE(...)式に統一
#             ]  # 1件分の行データを作成
#             write_list.append(row)  # 構築した行を出力用リストに追加
#         return write_list  # すべてのレコードを2次元リストにして返す



#     # ==========================================================
#     # メソッド定義

#     def run(self, records):
#         # 一括書き込みフロー本体
#         # 1) 行配列に整形 → 2) 追記先行の算出 → 3) "USER_ENTERED" でupdate
#         #    （USER_ENTEREDにより、数式は評価され、先頭'は文字列扱いになる）
#         logger.info("WriteGssFlow: データの書き込みフローを開始します")  # 開始ログを出力
#         write_list = self.build_write_list(records)  # レコード群をシート用2次元配列へ整形
#         start_row = self.find_first_empty_row()  # 追記開始行を取得
#         start_cell = f"A{start_row}"  # A行から右方向にデータを展開（開始セルをA{n}で指定）
#         self.worksheet.update(start_cell, write_list, value_input_option="USER_ENTERED")  # 一括更新を実行
#         logger.info(f"スプレッドシート書き込み成功: {len(write_list)}件")  # 成功件数を情報ログに出す















# ==========================================================
# import（標準、プロジェクト内モジュール）

import logging  # ログ出力（処理の進捗やエラー確認に使う）



# ==========================================================
# ログ設定

logger = logging.getLogger(__name__)  # このモジュール専用のロガーを取得



# ==========================================================
# class定義

class WriteGssFlow:  # GSS(スプレッドシート)へレコードを追記する小さなフロークラス
    """
    役割：抽出済みレコードのリストを、Googleスプレッドシートへ
    追記（append的に）書き込むための小さなフロー。
    前提：gspreadのWorksheetオブジェクトを受け取り、updateで一括反映する。
    """



    # ==========================================================
    # コンストラクタ（インスタンス生成時に実行）

    def __init__(self, worksheet):
        self.worksheet = worksheet  # 書き込み対象のワークシート（gspread.Worksheet想定）



    # ==========================================================
    # メソッド定義

    def _safe_sheet_text(self, v):
        # シート上での自動変換（日付/数値化）を避けるため、先頭に'を付与して「文字列」として扱わせる
        # すでに'で始まっている場合は二重付与しない
        s = str(v)  # 値を文字列化（Noneや数値でも安全に扱うため）
        return s if s.startswith("'") else f"'{s}"  # 先頭'有無で分岐し、必要なら付加して返す



    # ==========================================================
    # メソッド定義

    def format_image_formula(self, url_or_formula):
        # 画像セルに入れる値を統一：
        # - 既に"=..."で始まる場合は式としてそのまま使用
        # - URLだけ渡された場合は、=IMAGE(url, 4, 80, 80) 形式に整形（4はカスタムサイズ、80x80）
        if not url_or_formula:
            return ""  # 空なら空文字（セルも空のまま）
        s = str(url_or_formula).strip()  # 前後空白を除去し、文字列として扱う
        if s.startswith("="):
            return s  # 既存の式を尊重
        return f'=IMAGE("{s}", 4, 80, 80)'  # URLを画像式に変換（スプレッドシートで画像表示）



    # ==========================================================
    # メソッド定義

    def find_first_empty_row(self):
        # 1列目（A列）の現行値を取得し、その件数+1行目を「追記先」と見なす
        # gspreadのcol_valuesは末尾の空行を返さないため、このロジックで次の空き行が得られる
        values = self.worksheet.col_values(1)  # A列の全値を取得（ヘッダ含む）
        return len(values) + 1  # 現在の最終行の次の行番号を返す



    # ==========================================================
    # メソッド定義

    def build_write_list(self, records):
        # レコード(dict)から、シートに書き込む2次元配列（行のリスト）を生成する
        # 想定キー: date, title, price, ct, 1ct_price, image または image_url
        write_list = []  # ここに各行（リスト）を順次追加していく
        for rec in records:
            img_src = rec.get("image_url") or rec.get("image") or ""  # image_url優先、無ければimage、無ければ空

            row = [
                self._safe_sheet_text(rec["date"]),   # ' を付けて文字列として保存（シートの自動日付変換対策）
                rec["title"],                          # 件名
                rec["price"],                          # 価格（数値想定：USER_ENTEREDで数値として入る）
                rec["ct"],                             # カラット数
                rec["1ct_price"],                      # 1ctあたりの単価
                self.format_image_formula(img_src),    # 画像セル：URL→=IMAGE(...)式に統一
            ]  # 1件分の行データを作成
            write_list.append(row)  # 構築した行を出力用リストに追加
        return write_list  # すべてのレコードを2次元リストにして返す





    # -----------------------------
    # 重複判定ユーティリティ（追加）
    # -----------------------------
    @staticmethod
    def _norm(s) -> str:
        """比較用に正規化（前後空白除去 + 小文字化）。None安全。"""
        if s is None:
            return ""
        return str(s).strip().lower()

    def _header_values(self):
        """1行目をヘッダとして取得。ヘッダが無い場合は空配列。"""
        try:
            return self.worksheet.row_values(1) or []
        except Exception:
            return []

    def _find_url_col_index(self) -> int | None:
        """
        URL列のインデックス(1始まり)を推定。
        見つからなければ None（→A列を既存キー列として扱う）。
        """
        header = [self._norm(h) for h in self._header_values()]
        if not header:
            return None
        candidates = {"url", "detail_url", "link", "リンク"}
        for i, h in enumerate(header, start=1):
            if h in candidates:
                return i
        # 全角/大小の揺れ対策
        for i, h in enumerate(header, start=1):
            if h in {"url", "ｕｒｌ"}:
                return i
        return None

    def _load_existing_url_keys(self) -> set[str]:
        """
        既存シートからURLキー集合を作る。
        - URL列が特定できればその列（2行目以降）
        - 無ければA列（2行目以降）
        """
        col_idx = self._find_url_col_index()
        try:
            if col_idx is None:
                col_vals = self.worksheet.col_values(1)  # A列
            else:
                col_vals = self.worksheet.col_values(col_idx)
        except Exception as e:
            logger.warning(f"既存URL取得に失敗。重複判定をスキップします: {e}")
            return set()

        # 先頭行はヘッダ想定→スキップ
        return {self._norm(v) for v in (col_vals[1:] if len(col_vals) > 1 else []) if v}

    @staticmethod
    def _extract_url_key_from_record(rec, url_key_idx: int | None = None) -> str:
        """
        新規レコードからURLキーを取り出して正規化して返す。
        - dict: 'url'/'detail_url'/'link'/'リンク' を優先
        - list/tuple: url_key_idx 指定時はその列、無ければ先頭要素
        - str: その文字列をURLとみなす
        見つからなければ空文字を返す
        """
        def norm(x): return WriteGssFlow._norm(x)

        if isinstance(rec, dict):
            for k in ("url", "detail_url", "link", "リンク", "URL"):
                if k in rec and rec[k]:
                    return norm(rec[k])
            return ""
        if isinstance(rec, (list, tuple)):
            if url_key_idx and 1 <= url_key_idx <= len(rec):
                return norm(rec[url_key_idx - 1])
            return norm(rec[0]) if rec else ""
        if isinstance(rec, str):
            return norm(rec)
        return ""

    def _filter_duplicates(self, records):
        """
        既存GSSにあるURLと重複するレコードを除外して返す。
        レコード形（dict/list/str）とシート構成（ヘッダ有無）に自動対応。
        """
        existing = self._load_existing_url_keys()
        url_col_idx = self._find_url_col_index()  # list行の列解決に利用
        filtered = []
        dropped = 0

        for rec in records:
            key = self._extract_url_key_from_record(rec, url_key_idx=url_col_idx)
            if key and key in existing:
                dropped += 1
                continue
            filtered.append(rec)
            if key:
                existing.add(key)  # 同一バッチ内重複も弾く

        logger.info(f"重複スキップ: 採用={len(filtered)}件, 除外={dropped}件")
        return filtered
























    # ==========================================================
    # メソッド定義

    def run(self, records):
        logger.info("WriteGssFlow: データの書き込みフローを開始します")

        # ★追加: 既存GSSとの重複除外（URLキー）
        records = self._filter_duplicates(records)
        if not records:
            logger.info("重複のため新規書き込み対象がありません（0件）")
            return 0

        # 以降は既存のまま：
        write_list = self.build_write_list(records)
        start_row = self.find_first_empty_row()
        start_cell = f"A{start_row}"
        self.worksheet.update(start_cell, write_list, value_input_option="USER_ENTERED")
        logger.info(f"スプレッドシート書き込み成功: {len(write_list)}件")
        return len(write_list)

























# ==============
# 実行の順序
# ==============
# 1. モジュール logging をimportする
# → ログ出力の仕組みを使えるようにする準備。補足：この段階では処理は動かず“読み込み”だけ。

# 2. logger = logging.getLogger(name) を実行する
# → このモジュール専用のロガーを取得する。補足：以降の情報/エラーを一箇所に集約して記録できる。

# 3. class WriteGssFlow を定義する
# → スプレッドシートへの一括追記を担う実行フローの器を用意する。補足：ここまでのclass定義は“準備”であり、まだ実行されない。

# 4. メソッド init(self, worksheet) を定義する
# → 書き込み対象のワークシート（gspread.Worksheet想定）を保持する初期化を行う。補足：依存を外から渡す“依存注入”でテストしやすくする。

# 5. メソッド _safe_sheet_text(self, v) を定義する
# → 先頭に’を付けてシートの自動日付/数値変換を防ぎ、文字列として保存できる形にする。補足：既に’で始まる場合は重ねて付けない安全策。

# 6. メソッド format_image_formula(self, url_or_formula) を定義する
# → 値がURLなら =IMAGE(”…”, 4, 80, 80) に整形し、既に式ならそのまま返す。補足：空値は空文字にしてセルを空のままにする。

# 7. メソッド find_first_empty_row(self) を定義する
# → A列の既存値数+1を次の追記行として計算する。補足：gspreadのcol_valuesは末尾の空行を返さない特性を利用。

# 8. メソッド build_write_list(self, records) を定義する
# → 各レコードを1行のリストに変換し、2次元配列（行のリスト）を作る。補足：画像はURLを統一的に=IMAGE式へ変換する。

# 9. メソッド run(self, records) を定義する
# → 一括書き込みの本体フロー（整形→開始行算出→update実行→ログ）をまとめる。補足：ここまで定義であり、呼ばれるまで動かない。

# 10. （メソッド run が呼ばれたとき）開始ログを出力する
# → 書き込みフローの開始を記録する。補足：運用時のトレースに役立つ。

# 11. （メソッド run が呼ばれたとき）build_write_list を呼び出して行データを作る
# → records をシート更新用の2次元配列に整形する。補足：画像列は統一形式に揃う。

# 12. （メソッド run が呼ばれたとき）find_first_empty_row で追記開始行を求める
# → 既存データ末尾の次の行番号を取得する。補足：ヘッダがあっても件数ベースで正しく算出できる。

# 13. （メソッド run が呼ばれたとき）開始セル start_cell を “A{行番号}” で組み立てる
# → A列起点で右方向に行データを書き込む準備をする。補足：開始位置を文字列で指定するgspreadの仕様に合わせる。

# 14. （メソッド run が呼ばれたとき）worksheet.update(…, value_input_option=“USER_ENTERED”) を実行する
# → 2次元配列を一括で貼り付け、式は評価・’付き値は文字列として扱わせる。補足：高速かつセルの解釈をスプレッドシート標準に委ねる。

# 15. （メソッド run が呼ばれたとき）成功件数を情報ログに記録して終了する
# → 何件書き込んだかを明示してフローを締める。補足：後追い検証や障害調査の指標になる。