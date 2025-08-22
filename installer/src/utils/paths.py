# ==========================================================
# import（標準、プロジェクト内モジュール）  # ここから必要なモジュールを読み込む

import sys  # 実行環境やバイナリの位置（sys.executable）など、インタプリタ情報にアクセスするための標準モジュール
from pathlib import Path  # ファイルパス操作をオブジェクト指向で扱うためのPathクラスを提供
    # 空行: セクションの見通しを良くするための区切り（機能的な意味はない）


# ==========================================================
# 関数定義

def app_root() -> Path:  # アプリの「ルートディレクトリ」を推定して Path で返すユーティリティ関数
    if getattr(sys, "frozen", False):  # PyInstaller等でバンドルされた実行形式かを判定（sys.frozen が True）
        return Path(sys.executable).resolve().parent  # 実行ファイルのあるディレクトリをルートとみなして返す
    # パッケージ構成に合わせて適宜調整  # ソース実行時のベースをどこに置くかはプロジェクト構造に依存
    return Path(__file__).resolve().parents[2]  # installer/src/utils/ から2階層上を想定
