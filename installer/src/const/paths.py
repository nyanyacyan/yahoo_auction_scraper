# ==========================================================
# import（標準、プロジェクト内モジュール）  # ここから必要なモジュールを読み込む

import os  # 環境変数の参照に使用
from pathlib import Path  # パス操作をオブジェクト指向的に扱うために使用
from typing import Final  # 「再代入しない」意図を示す型ヒント
    # 空行: ここからリポジトリルート推定と各ディレクトリ定数の定義に入る

# リポジトリルートを頑健に推定（環境変数があれば優先）  # REPO_ROOT が基準パスになる
REPO_ROOT = Path(os.getenv("REPO_ROOT", Path(__file__).resolve().parents[3]))  # REPO_ROOT env が無ければファイル位置から親を辿る

DATA_DIR:  Final[Path] = REPO_ROOT / "data"   # データ保存用ディレクトリ（例: CSV/画像などの実体）
LOG_DIR:   Final[Path] = REPO_ROOT / "logs"   # ログ保存用ディレクトリ
CACHE_DIR: Final[Path] = REPO_ROOT / "cache"  # 一時/キャッシュファイルの保存先
IMG_DIR:   Final[Path] = DATA_DIR / "images"  # 画像の保存先（data/images に固定）
CONF_DIR:  Final[Path] = REPO_ROOT / "installer" / "config"  # 設定ファイル群の格納場所
# 空行: 認証関連ファイルのパス定義に続く

CREDENTIALS_JSON: Final[Path] = CONF_DIR / "credentials.json"  # サービスアカウント認証情報の既定パス
TOKEN_JSON:       Final[Path] = CONF_DIR / "token.json"        # OAuth 等のトークン保存先（必要に応じて使用）
# 空行: 初期化時に必要なディレクトリを作成する補助関数

def ensure_dirs() -> None:  # 必要なディレクトリ群をまとめて作成（存在すれば何もしない）
    for d in (DATA_DIR, LOG_DIR, CACHE_DIR, IMG_DIR, CONF_DIR):  # 作成対象をタプルで列挙
        d.mkdir(parents=True, exist_ok=True)  # 親も含めて作成し、既存ならエラーにしない
