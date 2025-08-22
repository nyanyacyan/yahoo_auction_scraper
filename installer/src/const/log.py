# ---- 既定のコンソール出力 ----  # コンソール（標準出力など）に出すログの基本設定セクション
CONSOLE_FORMAT = "%(levelname)s:%(name)s:%(message)s"  # 出力フォーマット（レベル:ロガー名:本文）
CONSOLE_LEVEL = "INFO"         # "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL" のいずれかを文字列で指定
URLLIB3_LEVEL = "WARNING"      # urllib3 ロガーのレベル（通信系の冗長ログを抑える）

# ---- ノイズ源ロガー（必要に応じて編集）----  # うるさいログを出しがちなロガー名の一覧
NOISY_LOGGERS = (  # ここに列挙されたロガーにはフィルタやレベルを個別適用する想定
    "selenium.webdriver.remote.remote_connection",  # SeleniumのHTTP送受信ログ
    "selenium.webdriver.common.selenium_manager",   # Selenium Managerのセットアップログ
    "urllib3.connectionpool",                       # urllib3の接続プールログ
)

# ---- フィルタのON/OFF ----  # どの種類のメッセージを抑制するかを個別に切り替える
ENABLE_FILTER_HTTP200       = True  # …"HTTP/1.1" 200 … の成功ログをミュートするか
ENABLE_FILTER_STATUS_2XX    = True  # …status=200… 等の2xx成功レスポンスをミュートするか
ENABLE_FILTER_FINISHED_REQ  = True  # …Finished Request の完了通知をミュートするか
ENABLE_FILTER_READY_STATE   = True  # document.readyState ポーリング系のデバッグログをミュートするか

# ---- パターン（必要なら上書き）----  # 抑制対象を検出するための正規表現パターン
RE_HTTP200   = r'HTTP/1\.1"\s+200\b'                 # HTTP/1.1 200 成功行を検出
RE_STATUS    = r'status=(\d{3})'                     # "status=XXX" からステータスコードを抽出
RE_READY     = r'execute/sync.*document\.readyState' # readyState ポーリングを示す行にマッチ
RE_FINISHED  = r'Finished Request'                   # 処理完了通知を示す行にマッチ

# ---- 既定挙動 ----  # 全体のふるまいに関わる基本フラグ
DEFAULT_MUTE_READY_STATE = True  # log_trimmer の既定として readyState ログを抑制するか
DISABLE_PROPAGATION = True       # 該当ロガーのログを親ロガー（ルート）へ伝播させない

# 空行: ここから色付き出力関連の設定（必要に応じてターミナルで可読性を上げる）

# ---- 追加（色の有効/無効やマップ）----  # カラーリングの有効化や色割り当てに関する設定
ENABLE_COLOR = True            # 色付き出力を有効にするか
COLOR_TTY_ONLY = True          # TTY（端末）接続時のみ色を付けるか（非TTYのログ収集先では無色にする）
FORCE_COLOR = False            # True にすると TTY 判定に関わらず常に色を付ける

COLOR_RESET = "\033[0m"        # 色リセットのANSIエスケープコード
COLOR_LEVEL_MAP = {            # ログレベルごとの前景色（ANSIコード）
    "DEBUG":    "\033[90m",   # gray（デバッグ）
    "INFO":     "\033[94m",   # blue（情報）
    "WARNING":  "\033[93m",   # yellow（警告）
    "ERROR":    "\033[91m",   # red（エラー）
    "CRITICAL": "\033[95m",   # magenta（致命的）
}

# 既定フォーマット（未指定時の既定値）  # 色付き時などの標準フォーマットと日付書式
CONSOLE_DATEFMT = "%H:%M:%S"  # 時刻の表示形式（例: 14:05:33）
CONSOLE_FORMAT_COLORED = "%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s"  # カラー前提の詳細書式

# 出力先（"stdout" / "stderr"）  # コンソール出力を標準出力か標準エラーへ振り分ける
CONSOLE_STREAM = "stdout"  # 既定は標準出力（必要に応じて "stderr" に変更）
