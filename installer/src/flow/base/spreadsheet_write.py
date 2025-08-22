# ==========================================================
# import（標準、プロジェクト内モジュール）  # ここから必要なモジュールを読み込む

import logging  # ログ出力のための標準ライブラリ
from typing import Any, List  # 型ヒント用。可読性と保守性を高める
from installer.src.const import sheets as C_SHEET  # シート名や列名、既定値などの設定を参照する
    # 空行: import セクションとログ設定の区切り。論理的なまとまりを分けて読みやすくする


# ==========================================================
# ログ設定  # このモジュール専用のロガーを取得して以降のログ出力に使う

logger: logging.Logger = logging.getLogger(__name__)  # モジュール名に紐づくロガー（ハンドラは上位で設定想定）
# 空行: ここからクラス定義セクションに切り替えるための区切り


# ==========================================================
# class定義

class SpreadsheetWriter:  # ワークシートに対する追記位置の判定と書き込み周辺の責務を持つクラス
    """
    Googleスプレッドシートなどのワークシートに対して、
    データ書き込み用の機能をまとめたクラス。
    - 追記開始行の判定に使う列・ヘッダ行数は const/sheet.py で一元管理
    """
        # 空行: 上のdocstringはこのクラスの目的や設計方針を説明（コードの動作には影響しない）


    # ==========================================================
    # コンストラクタ

    def __init__(self, worksheet: Any) -> None:  # コンストラクタ。対象ワークシートを受け取り内部に保持する
        """
        :param worksheet: 書き込み対象のワークシートオブジェクト（gspread.Worksheet想定）
        """
        self.worksheet: Any = worksheet  # 実際の操作対象。型はAnyだがgspread.Worksheetを想定

        # const が未定義の場合は安全なデフォルトにフォールバック  # getattrで存在しない定数に備える
        self._append_base_col_index: int = int(getattr(C_SHEET, "APPEND_BASE_COLUMN_INDEX", 1))  # A列  # 追記基準に使う列番号（1始まり）
        self._header_row_count: int = int(getattr(C_SHEET, "HEADER_ROWS", 1))                    # 見出し1行  # 見出し行数（データ開始位置の基準）


    # ==========================================================
    # メソッド定義

    def find_first_empty_row(self) -> int:  # 追記すべき「最初の空行」の行番号を計算して返す
        """
        「最初の空行番号」を返す。
        - APPEND_BASE_COLUMN_INDEX 列の埋まり具合を見て判定
        - データ開始行は (HEADER_ROWS + 1)
        """
        try:  # まず基準列（通常はA列）の値一覧を取得する
            column_values: List[Any] = self.worksheet.col_values(self._append_base_col_index)  # 指定列の全セル値を上から取得
        except Exception as e:  # 列取得に失敗した場合のフォールバック
            logger.warning(
                "col_values の取得に失敗したため末尾追記で代替します: col=%s, error=%s",
                self._append_base_col_index, e
            )  # どの列で何が起きたかを記録（デバッグしやすくする）
            # 取得できない場合は最終行の次（gspreadは row_count も持つが、
            # 標準の挙動に合わせて「既存値の次」に置く）
            try:  # A列だけでも取れないか再試行（環境依存の失敗に備え堅牢性を上げる）
                # A列の値だけでも試す（より堅牢に）
                column_values = self.worksheet.col_values(1)  # 最も一般的な列で代替取得
            except Exception:  # それでもダメなら安全側でデータ開始行を返す
                # それも不可なら安全側で2行目（見出し1行想定）
                return int(self._header_row_count) + 1  # ヘッダ直下の行を返し、最低限の書き込み位置を保証

        data_start_row: int = int(self._header_row_count) + 1  # データ開始行（例: ヘッダ1行なら2行目）  # ここより上は見出し扱い

        # gspread.col_values は末尾の空行は返さないため、
        # 途中に空きがあればそこ、無ければ len(column_values)+1 で次行を返す。
        for row_index, cell_value in enumerate(column_values[data_start_row - 1 :], start=data_start_row):  # データ開始行以降を走査
            if not cell_value:  # セルが空（=まだ値が入っていない）なら
                return row_index  # その行番号が追記開始位置となる

        return len(column_values) + 1  # 途中に空きが無ければ最終値の次の行（末尾追記）を返す
    