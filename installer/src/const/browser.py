# ==========================================================
# import（標準、プロジェクト内モジュール）  # ここから必要なモジュールを読み込む

from typing import Final, Tuple, Dict, Any, Optional  # 型ヒント用。Finalで「変更しない定数」を表現する意図を示す
import os as _os  # 環境変数から既定値を上書きするために os を _os 名で読み込む

HEADLESS_DEFAULT: Final[bool] = _os.environ.get("HEADLESS", "").lower() in ("1", "true", "yes", "on")  # ヘッドレス起動の既定値（文字列環境変数を真偽値に正規化）
USER_AGENT_DEFAULT: Final[Optional[str]] = _os.environ.get("USER_AGENT") or None  # UA を環境変数で差し替え可能（未設定なら None）

# 例: 1366x864 / 1280x800 / 1920x1080  # 推奨解像度例。値は "幅,高さ" 形式
WINDOW_SIZE: Final[str] = _os.environ.get("CHROME_WINDOW_SIZE", "1366,864")  # ウィンドウサイズの既定（環境変数で上書き可）

# "normal" | "eager" | "none"  # Selenium の pageLoadStrategy の候補値
PAGE_LOAD_STRATEGY: Final[str] = _os.environ.get("PAGE_LOAD_STRATEGY", "normal")  # ページ読み込み戦略の既定

# ドライバ起動後ブラウザを自動で閉じない（デバッグ用）  # True にするとプロセスが残るので画面を確認しやすい
DETACH: Final[bool] = _os.environ.get("CHROME_DETACH", "").lower() in ("1", "true", "yes", "on")  # デタッチ動作の有無

# Chrome 本体のパス（カスタムビルドやポータブル使用時）  # 既定は None（Chrome 自動検出に任せる）
CHROME_BINARY: Final[Optional[str]] = _os.environ.get("CHROME_BINARY") or None  # 実行ファイルパスを直接指定する場合に使用

# ダウンロード先（必要なら設定）  # None の場合は Chrome の既定ダウンロードディレクトリ
DOWNLOAD_DIR: Final[Optional[str]] = _os.environ.get("CHROME_DOWNLOAD_DIR") or None  # 既定のダウンロードディレクトリ

BASE_ARGS: Final[Tuple[str, ...]] = (  # Chrome 起動時に常に付与する引数（必要に応じて追加で拡張）
    "--no-sandbox",  # サンドボックス無効（コンテナ/CI等での安定性向上目的）
    "--disable-dev-shm-usage",  # /dev/shm 使用を抑制（メモリ領域不足対策）
    "--disable-gpu",  # GPU を使わない（サーバ環境での互換性向上）
    "--disable-extensions",  # 拡張機能を無効化（動作の再現性を担保）
    "--remote-allow-origins=*",  # リモート接続の許可範囲を緩める（Selenium 新仕様の回避策）
    "--disable-notifications",  # 通知ポップアップを無効化（UI操作を邪魔しないように）
    "--lang=ja-JP",  # ブラウザ言語を日本語へ（サイトの表示言語に影響）
)  # タプル終端（不変であることを強調）

# ダウンロード/通知などの既定 prefs  # Chrome のプロファイル設定（実行時に options.add_experimental_option で適用）
PREFS: Final[Dict[str, Any]] = {  # 実験的オプションとして渡すプリファレンスの辞書
    "profile.default_content_setting_values.notifications": 2,  # ブロック  # 通知を常に拒否（0=許可,1=質問,2=ブロック）
    "download.prompt_for_download": False,  # ダウンロード確認ダイアログを出さない（自動保存）
    # "download.default_directory": は必要に応じて実行時に付与  # ダウンロード先を固定したい場合にのみ設定する
}  # 辞書終端
