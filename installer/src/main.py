# ==========================================================
# import（標準、プロジェクト内モジュール）

import sys  # Pythonの実行環境やパス操作に使う標準モジュール
import os  # 環境変数の参照/設定やファイルパス操作に使用
import logging  # ログ出力（INFO/ERRORなどのメッセージ記録）
from pathlib import Path  # パス操作をオブジェクト指向的に扱えるヘルパ

# ----------------------------------------------------------
# パッケージ解決用にリポジトリルートを sys.path へ追加
# このファイル: installer/src/main.py
# 2階層上: <repo_root>（例: /Users/.../yahoo_auction_scraper）
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # リポジトリ直下をimport探索パスの先頭に追加
# ----------------------------------------------------------

from installer.src.flow.main_flow import MainFlow, Config  # noqa: E402  （sys.path 追加後に import）  # 実行フロー本体と設定クラスを読み込む（E402は意図的に無視）



# ==========================================================
# ログ設定

logging.basicConfig(level=logging.INFO)  # ルートロガーにINFOレベルの基本設定を行う



# ==========================================================
# 関数定義

def app_root() -> Path:  # 実行形態（ソース/バイナリ）に応じて基準ディレクトリを返す関数
    if getattr(sys, "frozen", False):  # PyInstaller等で凍結（単一バイナリ）されているか判定
        # PyInstaller --onefile 時、exe の場所
        return Path(sys.executable).resolve().parent  # 実行ファイルのあるディレクトリを返す
    # ソース実行時は installer/ を返す
    return Path(__file__).resolve().parents[1]  # このファイルの1つ上（installer/）を返す
# 資格情報の自動検出（未設定なら config/credentials.json を使う）
CRED_PATH = app_root() / "config" / "credentials.json"  # 既定の資格情報パスを組み立てる
if (  # 既に環境変数で資格情報が与えられていない場合のみ、デフォルトパスを設定
    "GOOGLE_CREDENTIALS_JSON" not in os.environ
    and "GOOGLE_CREDENTIALS_JSON_B64" not in os.environ
    and "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ
    and CRED_PATH.exists()
):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(CRED_PATH)  # gspread等が参照する環境変数をセット



# ==========================================================
# 関数定義

def main():  # アプリのエントリーポイントとなる関数
    config = Config()           # 設定情報の取得（スプレッドシートIDやUAなど）
    flow = MainFlow(config)     # 実行フローのインスタンスを生成（依存注入）
    flow.run()                  # 全体フローを実行（条件読込→巡回→書き込み）



# ==========================================================
# 実行エントリーポイント

if __name__ == "__main__":  # モジュールとしてimportされた場合は実行せず、直接起動時のみmain()を呼ぶ
    main()  # メイン関数を起動して処理を開始





# ==============
# 実行の順序
# ==============
# 1. 標準モジュール（sys/os/logging/pathlib）をimportする
# → 以降のパス操作・環境変数設定・ログ出力に使う準備。補足：ここは単に“使えるようにする”段階。

# 2. sys.path にリポジトリ直下（2階層上）を先頭追加する
# → 自作パッケージ（installer配下）をimportできるようにするためのパス通し。補足：順序が重要で、これより前に自作モジュールはimportしない。

# 3. class MainFlow / class Config をimportする（E402は意図的に無視）
# → 直前で通したパスを使って実行フロー本体と設定classを読み込む。補足：ここで読み込みに失敗したらパス設定を疑う。

# 4. 関数 app_root を定義する
# → 実行形態（PyInstallerの単一バイナリ or ソース）に応じた基準ディレクトリを返す。補足：“frozen”がTrueならexeの場所、Falseならinstaller/。

# 5. 既定の資格情報パス CRED_PATH を組み立てる
# → app_root()/config/credentials.json を指すPathオブジェクトを作る。補足：存在チェックのためにPathで持っておく。

# 6. 資格情報の環境変数を未設定かつCRED_PATHが存在する場合にのみ既定値を設定する
# → GOOGLE_APPLICATION_CREDENTIALS にCRED_PATHをセットし、gspread等が認証を見つけられるようにする。補足：既に明示設定があればそちらを優先。

# 7. logging.basicConfig(level=INFO) でログの基本設定を行う
# → 以降のINFO以上のメッセージが標準出力に出るようになる。補足：format/handlerは必要に応じてここで拡張可能。

# 8. 関数 main を定義する（この時点では実行しない）
# → エントリーポイントとして後で呼ばれる処理をまとめる。補足：定義＝準備であり、ここでは動かない。

# 9. main 内：class Config のインスタンスを生成する
# → スプレッドシートIDやUAなど、実行に必要な設定をオブジェクト化する。補足：設定の集約点として扱う。

# 10. main 内：class MainFlow のインスタンスを設定付きで生成する
# → 実行フローに設定を“依存注入”して準備完了にする。補足：テスト容易性と責務分離のためにConfigを渡す。

# 11. main 内：メソッド run を呼び出す
# → 条件読込→巡回（スクレイピング等）→書き込みの全体処理を実行する。補足：実際の仕事はこの呼び出しで始まる。

# 12. if name == “main” ガードで“直接実行”かどうか判定する
# → このファイルがスクリプトとして起動された時だけmainを動かす。補足：他モジュールからimportされた時に勝手に動かないための慣習。

# 13. ガードの中で関数 main を呼び出す
# → ここで初めて処理が開始され、以降のログ出力や外部アクセスが走る。補足：実行開始地点はこの1行。