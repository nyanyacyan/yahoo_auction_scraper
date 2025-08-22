# ==========================================================
# import（標準、プロジェクト内モジュール）  # ここから必要なモジュールを読み込む

from . import selectors, paths, sheets, templates, regexes  # 相対インポートで各サブモジュールを読み込み、パッケージ直下から参照可能にする
    # 空行: ここで「このパッケージが外部に何を公開するか」を __all__ で明示するセクション

__all__ = ["selectors", "paths", "sheets", "templates", "regexes"]  # import * 時に公開する名前を制御（不要な内部名の露出を防ぐ）
