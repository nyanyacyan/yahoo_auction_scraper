# ==========================================================
# import（標準、プロジェクト内モジュール）

import sys
import os
import logging

# ----------------------------------------------------------
# 1. os.path.dirname(__file__) → このファイル(main.py)のパスを取得
# 2. os.path.join(..., "..", "..") → そこから ".." を2回使って、2階層上のフォルダに移動
# 3. os.path.abspath(...) → そのパスを絶対パスに変換（/Users/xxx/path/to/yahoo_auction_scraper-main のような形）。
# 4. sys.path.insert(0, 絶対パス) → yahoo_auction_scraper-mainを絶対パスとして追加（設定する）
sys.path.insert( 0 , os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
# ----------------------------------------------------------

from installer.src.flow.main_flow import MainFlow, Config   # 先ほど追加した検索パスを使って MainFlow と Config を読み込む


# ==========================================================
# ログ設定

logging.basicConfig(level=logging.INFO) # INFOレベル以上出力


# ==========================================================
# 関数
# メイン処理実行関数

def main():
    config = Config()    # 設定情報の取得（Configインスタンス生成）
    flow = MainFlow(config)    # 情報収集フローのインスタンス生成
    flow.run()    # 情報収集フローを実行


# ==========================================================
# スクリプト直実行時のエントリーポイント

if __name__ == "__main__":
    main()





# ==============
# 実行の順序
# ==============
# 1. import各種モジュール
# → 標準（logging）とプロジェクト内の必要クラスを読み込む。

# 2. sys.path.insert(0, ...)
# → main.py から2階層上（＝プロジェクトルート）を 検索パスの先頭に追加。

# 3. from installer.src.flow.main_flow import MainFlow, Config
# → いま追加した検索パスを使って MainFlow と Config を読み込む。

# 4. logger設定
# → ログ設定（INFO以上を出力）。

# 5. def main(): ...
# → 関数 main を定義（この時点では実行されない）。


# 6. if __name__ == "__main__": main()
# → スクリプトが直接実行された場合に main() を呼ぶ。

# 7. main() 実行
# config = Config()（設定生成）
# flow = MainFlow(config)（フロー構築）
# flow.run()（収集フローを実行）
# flow.run() 内で main_flow.py 側の処理へ移行














