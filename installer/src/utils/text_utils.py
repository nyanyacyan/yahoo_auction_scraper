# # ==========================================================
# # import（標準、プロジェクト内モジュール）

# import re        # 正規表現を使って文字列から数値を抽出するために使用
# import logging   # エラー発生時のログ出力に使用



# # ==========================================================
# # ログ設定

# logger = logging.getLogger(__name__)  # このモジュール専用のロガー



# # ==========================================================
# # class定義

# class NumExtractor:  # 商品タイトル等から「◯◯ct」の数値部分を抽出するクラス
#     """
#     役割：テキスト（例：商品タイトル）から「◯◯ct」の数値部分を抽出するユーティリティ。
#     想定入力例："ダイヤ 0.50ct ルース" → 0.50 を float で返す。
#     """



#     # ==========================================================
#     # 静的メソッド（インスタンス化不要で利用可能）

#     @staticmethod  # 静的メソッド化：インスタンス生成せず NumExtractor.extract_ct_value(...) と呼べる
#     def extract_ct_value(text: str) -> float:  # 与えられた文字列から「数値+ct」を抽出してfloatで返す
#         """
#         引数: text … "0.5ct" のように「数値 + ct」を含む文字列
#         戻り値: ct値（float）。複数ある場合は最後のものを採用（例："0.3ct 0.5ct" → 0.5）
#         例外: 該当パターンが見つからない/数値変換失敗時には ValueError を送出
#         """
#         try:  # 例外が起きても呼び出し側に明確に知らせるため、まずtryで囲む
#             # パターン説明:
#             #  - [0-9]+(?:\.[0-9]+)? : 整数または小数（例 0.5）
#             #  - \s*                 : 数値と"ct"の間の任意の空白を許容
#             #  - ct                  : 単位。大文字小文字は re.IGNORECASE で無視
#             pattern = r'([0-9]+(?:\.[0-9]+)?)\s*ct'  # 「数値 + 任意空白 + ct」にマッチする正規表現
#             # findallは一致した数値部分のリストを返す。複数ある場合があるため注意
#             matches = re.findall(pattern, text, re.IGNORECASE)  # すべての一致を取得（大文字小文字無視）
#             if not matches:  # マッチが1件もない場合のガード
#                 # 初学者ポイント：例外を投げることで呼び出し元に「失敗」を明確に通知する
#                 raise ValueError(f"'ct'直前の数値が見つかりません: {text}")  # 想定外フォーマットとしてValueError

#             # 複数マッチした場合、慣例として「最後の値」を採用（最新・主要情報を末尾に書くタイトル想定）
#             ct_value = float(matches[-1])  # 文字列の数値をfloatへ変換（例："0.50" → 0.5）
#             return ct_value  # 抽出・変換に成功した数値を返す

#         except Exception as e:  # あらゆる例外を捕捉し、内容をログに残してから再送出
#             # 何が原因で失敗したか（textとエラー内容）をログに残す。デバッグ時に有用
#             logger.error(f"ct数値抽出エラー: {e} | text='{text}'")  # 失敗時の詳細ログ
#             raise  # ここで握りつぶさず、上位に例外を再送出
























import re
import logging
import unicodedata
from typing import Optional

logger = logging.getLogger(__name__)

class NumExtractor:
    """
    タイトルから ct の数値を抽出するユーティリティ。

    仕様:
    - タイトル中に ct が複数ある場合、**最初に出現したもの**を採用
    - 「0.5ct」「0.50 ct」「ct0.5」「ct 0.5」「０．５ｃｔ」など表記ゆれに対応
    - 桁区切り(,)と全角→半角を正規化して float に変換
    - 見つからない/不正値は ValueError
    """

    # 数値（半角/全角 & 小数/カンマ対応）
    _NUM = r"[0-9０-９]+(?:[.,．][0-9０-９]+)?"

    # 「数値 + ct」または「ct + 数値」のどちらも拾う複合パターン
    # 例: 0.5ct / 0.5 ct / ct0.5 / ct 0.5 / ０．５ｃｔ / ｃｔ０．５
    _RE_CT_BOTH = re.compile(
        rf"(?i)(?:(?P<pre>{_NUM})\s*ct(?![A-Za-z0-9０-９])|(?<![A-Za-z0-9０-９])ct\s*[:：]?\s*(?P<post>{_NUM}))"
    )

    @staticmethod
    def _normalize_text(s: str) -> str:
        # 全角→半角, 機種依存の小数点「．」→「.」
        s = unicodedata.normalize("NFKC", s)
        return s.replace("．", ".")

    @classmethod
    def _parse_number(cls, raw: str) -> float:
        raw = raw.replace(",", "")
        try:
            v = float(raw)
        except Exception as e:
            logger.error(f"ct数値の変換に失敗: raw='{raw}', err={e}")
            raise ValueError("ct数値の変換に失敗")
        if v <= 0:
            logger.error(f"ct数値が0以下: value={v}")
            raise ValueError("ct数値が0以下")
        return v

    @classmethod
    def extract_ct_value(cls, title: str) -> float:
        """
        タイトルに含まれるct数値を返す（最初に出現したctを採用）
        """
        if not isinstance(title, str):
            raise ValueError("titleはstrを期待します")
        text = cls._normalize_text(title)

        # ★ 最初の一致（.search）= 最初のctを採用
        m = cls._RE_CT_BOTH.search(text)
        if not m:
            logger.error(f"ct表記が見つかりません: title='{title}'")
            raise ValueError("ct表記が見つかりません")

        # 「数値+ct」なら 'pre'、 「ct+数値」なら 'post' に入る
        raw = m.group("pre") or m.group("post")
        value = cls._parse_number(raw)
        logger.debug(f"ct抽出: title='{title}', match='{m.group(0)}', value={value}")
        return value













# ==============
# 実行の順序
# ==============
# 1. モジュール re / logging をimportする
# → 文字列検索（正規表現）とログ出力を使えるようにする準備。補足：ここでは処理はまだ動かない（読み込みだけ）。

# 2. logger = logging.getLogger(name) を実行する
# → このモジュール専用のロガーを取得する。補足：以降のエラー内容を一箇所に記録できる。

# 3. class NumExtractor を定義する
# → 「◯◯ct」の数値部分を取り出すためのユーティリティclassを用意する。補足：定義時点では動かず、呼び出されて初めて処理する。

# 4. 静的メソッド extract_ct_value(text: str) を定義する（@staticmethod）
# → インスタンス不要で NumExtractor.extract_ct_value(…) と呼べるメソッドを用意する。補足：classの責務を保ったまま手軽に使える。

# 5. （メソッドが呼ばれたとき）try ブロックを開始する
# → 以降の処理で起きた例外を捕捉して記録・再送出できるようにする。補足：失敗時の原因追跡を容易にするため。

# 6. （メソッドが呼ばれたとき）正規表現パターン pattern を用意する
# → 「数値（小数可）＋任意空白＋’ct’」にマッチする表現を組み立てる。補足：大文字小文字は無視（IGNORECASE）。

# 7. （メソッドが呼ばれたとき）re.findall で一致する数値文字列のリストを取得する
# → text内のすべての「◯◯ct」に対応する数値部分を抜き出す。補足：複数見つかる可能性がある。

# 8. （メソッドが呼ばれたとき）一致が無ければ ValueError を送出する
# → 想定フォーマットでないことを明確に呼び出し元へ知らせる。補足：早めに失敗させることで不正データの混入を防ぐ。

# 9. （メソッドが呼ばれたとき）一致があれば最後の要素を float に変換して返す
# → タイトル末尾が最新情報という想定で matches[-1] を採用する。補足：例：“0.3ct 0.5ct” → 0.5 を返す。

# 10. （例外発生時のみ）except で logger.error に詳細を記録し、例外を再送出する
# → 失敗の内容と入力textをログに残し、呼び出し元へ例外を渡す。補足：握りつぶさずに原因追跡と上位でのハンドリングを両立する。