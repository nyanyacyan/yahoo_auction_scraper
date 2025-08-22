# ==========================================================
# import（標準、プロジェクト内モジュール）  # ここから必要なモジュールを読み込む

import logging  # ログ出力の基盤となる標準ライブラリを読み込む
import os  # 環境変数やファイルパス操作のための標準ライブラリ
import sys  # 実行環境やモジュール検索パスに関する処理で使える（本ファイルでは明示利用なし）
from pathlib import Path  # パス操作を高レベルに扱うための標準ライブラリ
_BOOTSTRAPPED = False  # 初期化済みかを示すフラグ（冪等実行のためのガード）


# ==========================================================
# ログ設定  # このモジュール専用のロガーを取得して以降の情報出力に用いる

_log = logging.getLogger(__name__)  # このモジュール用のロガーを取得


# ==========================================================
# 関数定義

def _repo_root() -> Path:  # リポジトリ直下ディレクトリを推定して返すヘルパー
    """
    <repo>/installer/src/bootstrap.py から、親を遡って
    'installer/src' を含むディレクトリの親（= リポジトリ直下）を返す。
    失敗時はフォールバックで parents[2]。
    """  # 上記はドキュメント文字列（実行時ヘルプ用）。ここでは説明のみ。
    p = Path(__file__).resolve()  # 現在ファイルの絶対パスを取得
    for parent in p.parents:  # 親ディレクトリを順に遡って探索
        if (parent / "installer" / "src").is_dir():  # installer/src が存在するか確認
            return parent  # <- ここが <repo-root>  # 見つかった地点の親をリポジトリ直下とみなす
    # フォールバック（通常の深さ: src→installer→repo なので parents[2] が <repo-root>）  # 見つからない場合の代替経路
    return p.parents[2]  # 想定構造に基づいて2階層上をリポジトリルートとする


# ==========================================================
# 関数定義

def _load_env_files() -> None:  # .env を探索・読み込む内部関数
    root = _repo_root()  # まずリポジトリ直下パスを特定
    candidates = [  # 読み込み候補の .env パス一覧
        root / ".env",  # ルート直下
        root / "config" / ".env",  # config 配下
        root / "installer" / ".env",  # installer 配下
    ]
    for env_path in candidates:  # 各候補を順に確認
        if not env_path.exists():  # ファイルが無ければスキップ
            continue  # 次の候補へ
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():  # 行単位で読み込む
                line = line.strip()  # 前後空白を除去
                if not line or line.startswith("#") or "=" not in line:  # 空行/コメント/無効行は無視
                    continue  # 次の行へ
                k, v = line.split("=", 1)  # KEY=VALUE を左右に分割（=は最初の1つだけ）
                k, v = k.strip(), v.strip()  # キー/値の前後空白を除去
                if k and (k not in os.environ or os.environ[k] == "") and v:  # 既存環境変数が未設定なら適用
                    os.environ[k] = v  # 環境変数へ注入
                    _log.debug(f".env から注入: {k}=*** ({env_path.name})")  # 値は伏せてキーのみログ出力
        except Exception as e:  # 読み込み中の例外は致命ではないため握りつぶす
            _log.debug(f".env 読み込みスキップ: {env_path} ({e})")  # スキップ理由をデバッグ出力


# ==========================================================
# 関数定義

def _ensure_google_credentials() -> None:  # 認証情報の環境変数を必要に応じて自動設定
    if (  # いずれかの方法で認証情報が既に設定済みなら何もしない
        os.environ.get("GOOGLE_CREDENTIALS_JSON")
        or os.environ.get("GOOGLE_CREDENTIALS_JSON_B64")
        or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    ):
        return  # 既存設定を尊重して終了

    root = _repo_root()  # ルートディレクトリを取得
    candidates = [  # 認証ファイルの配置候補パス
        root / "config" / "credentials.json",                 # 推奨: <repo>/config/credentials.json
        root / "installer" / "config" / "credentials.json",   # 旧構成: <repo>/installer/config/...
        Path(__file__).resolve().parent / "config" / "credentials.json",  # installer/src/config/...
    ]
    for p in candidates:  # 候補を順に確認
        if p.exists():  # ファイルが見つかったら
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(p)  # そのパスを環境変数に設定
            _log.info(f"Google認証: {p} を使用します（自動検出）")  # どのファイルを使うか情報ログ
            return  # 設定できたので終了

    _log.warning("Google認証ファイルが見つかりません。config/credentials.json を配置するか環境変数を設定してください。")  # 最終的に見つからなければ警告


# ==========================================================
# class定義

class _HideDateParseDebug(logging.Filter):  # 特定の冗長DEBUGログ（日時パース）を抑止するフィルタ


    # ==========================================================
    # メソッド定義

    def filter(self, record: logging.LogRecord) -> bool:  # ログRecordを受け取り表示可否(True/False)を返す
        return not (  # 条件に一致するログを除外（notで反転）
            record.levelno == logging.DEBUG  # レベルDEBUG
            and record.name == "installer.src.flow.base.utils"  # 対象ロガー名
            and "終了日時パース" in record.getMessage()  # メッセージに特定語句が含まれる
        )


# ==========================================================
# 関数定義

def _configure_logging(debug: bool) -> None:  # ルートロガーとハンドラを構成する内部関数
    level = logging.DEBUG if debug else logging.INFO  # debugフラグに応じてレベルを切替
    logging.basicConfig(level=level, force=True)  # 既存設定を上書きして基本設定を適用
    root = logging.getLogger()  # ルートロガーを取得

    # 既存の StreamHandler を一旦外す（重複防止）  # 以降で付け直すため一度除去
    for h in list(root.handlers):  # ハンドラをコピーしたリストで安全に走査
        if isinstance(h, logging.StreamHandler):  # コンソール向けハンドラだけを対象
            root.removeHandler(h)  # 重複表示を避けるため除去

    # カラー出力（任意ユーティリティがあれば）  # 利用可能なら色付き整形を有効化
    try:
        from installer.src.utils.logger_color import enable_colored_console  # 色付きハンドラ設定関数
        enable_colored_console(  # カラーコンソールハンドラを追加
            level=level,  # ログレベルを合わせる
            fmt="%(levelname)s - %(name)s:%(lineno)d - %(message)s",  # 出力フォーマット
        )
    except Exception:  # ユーティリティが無い/失敗した場合のフォールバック
        sh = logging.StreamHandler()  # デフォルトのストリームハンドラを作成
        sh.setLevel(level)  # ハンドラ側のレベルを設定
        sh.setFormatter(logging.Formatter("%(levelname)s - %(name)s:%(lineno)d - %(message)s"))  # シンプルな整形
        root.addHandler(sh)  # ルートにハンドラを追加

    # 冗長ログの抑止（任意ユーティリティがあれば）  # selenium/urllib3などの成功時ノイズを抑える
    try:
        from installer.src.utils.log_trimmer import install_log_trimmer  # ノイズ抑止ユーティリティ
        install_log_trimmer(console_level=level, mute_ready_state=True)  # 代表的なノイズログをミュート
    except Exception:  # 失敗しても致命ではないので無視
        pass  # そのまま続行

    for h in root.handlers:  # 最終的に残った全ハンドラに対して
        h.addFilter(_HideDateParseDebug())  # 日時パースのDEBUGログを抑止するフィルタを付与


# ==========================================================
# 関数定義

def bootstrap(debug: bool = False) -> None:  # 起動時の共通初期化を一度だけ実行する関数
    """
    起動時の共通初期化（冪等）:
    - ログ初期化
    - .env 読み込み
    - Google 認証ファイルの自動検出
    """  # 利用者向けに初期化内容を説明するドキュメント文字列
    global _BOOTSTRAPPED  # モジュールスコープのフラグを書き換えるためglobal宣言
    if _BOOTSTRAPPED:  # 既に初期化済みなら
        return  # 何もせず終了（冪等性の担保）
    _configure_logging(debug=debug)  # ログの初期化を実施
    _load_env_files()  # .env から環境変数を読み込む
    _ensure_google_credentials()  # Google認証ファイルを自動検出し環境変数を設定
    _BOOTSTRAPPED = True  # 初期化済みフラグを立てる（次回以降スキップ）
