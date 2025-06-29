# Yahoo Auction Scraper


## 概要
Yahoo!オークションから商品データを収集するスクレイピングプロジェクトです。
教育用途としてスクレイピングの基礎とチーム開発の流れを学ぶことを目的としています。


## 学習目標
本プロジェクトを通じて、以下の実践的スキルを学習します：

- Seleniumを用いたブラウザ自動操作の基礎
- Webページからの要素抽出・クリック・画像取得
- Googleスプレッドシートとの連携（読み書き）
- Pythonにおける責務分離・クラス設計の基礎
- 仮想環境の構築とパッケージ管理（requirements.txt）
- ファイル分離とモジュール化による可読性の高いコード設計
- GitHubを用いたチーム開発の初歩（README, gitignore, issue, commitなど）


## 全体処理フロー
1.	検索済みのURLへアクセス
2.	「落札相場」ボタンをクリック
3.	最初の商品リンクをクリックし、商品詳細ページへ遷移
4.	以下の情報を取得
    •	商品タイトル
    •	落札価格（例：¥51,700）
    •	終了日
    •	画像URL（可能なら画像保存）
5.	タイトルから「ct数値」を抽出（例：0.508）
6.	計算処理
    •	単価：価格 ÷ ct（例：¥51,700 / 0.508）
    •	-10%（手数料）、さらに -10%（税引き）で最終値算出
7.	Googleスプレッドシートへ出力
    •	日付、タイトル、価格、ct数値、最終単価、画像（可能であれば）


## 開発環境
- Python 3.10.7
- OS: 任意（Mac / Windows / Linux）
- 仮想環境の利用推奨（venv など）


## ディレクトリ構成
```
yahoo_auction_scraper/
├── README.md                      # プロジェクト概要・ルール・処理フローなど
├── .gitignore                     # 不要ファイルのGit管理除外設定
├── requirements.txt               # 必要ライブラリ一覧（開発・教育用）
├── docs/                          # 開発支援資料（納品時は除外）
│   ├── setup_guide.md             # 環境構築・実行手順
│   ├── design.md                  # 設計概要と命名ルール
│   └── flow_spec.md               # 処理フローの詳細定義
├── tests/                         # 単体テスト（教育用、納品時は除外）
│   └── test.py.                   # テストファイル
└── installer/                     # 納品対象一式（以下のみを相手に渡す）
    ├── run.bat                    # Windows用実行スクリプト
    ├── requirements.txt           # 必要ライブラリ一覧（納品用）
    ├── config/
    │   └── credentials.json       # Google Sheets APIキー（Git除外）
    ├── data/
    │   ├── images/                # 商品画像の保存先
    │   └── output/                # 出力CSV等（必要に応じて）
    └── src/
        ├── main.py                # 実行起点（YahooFlowを呼び出し）
        └── flow/
            ├── main_flow.py          # 一連の処理フロー
            ├── detail_page_flow.py   # 詳細ページの処理フロー
            ├── repeater.py           # ※繰り返し処理用（今回は未使用かも）
            └── base/
                ├── chrome.py              # Chrome（クラス名：Chrome）
                ├── selenium.py            # Selenium（クラス名：Selenium）
                ├── spreadsheet_read.py    # スプシ読取（クラス名：SpreadsheetReader）
                ├── spreadsheet_write.py   # スプシ書込（クラス名：SpreadsheetWriter）
                ├── number_calculator.py   # 数値計算（クラス名：PriceCalculator）
                ├── url_builder.py         # URL作成（クラス名：UrlBuilder）
                └── utils.py               # 汎用関数（クラス名なし or Utils）
```

## クラス構成（flow/base）
<!-- TODO 後でまとめる -->

> **注意**：各クラスの中身の実装も指定された責務に沿って行ってください。
> 拡張や追加クラスが必要な場合は、事前に相談すること。


## 命名ルール

本プロジェクトでは、以下の命名ルールとします：

- ファイル名：スネークケース（例：selenium_controller.py）
- クラス名：キャメルケース（例：SeleniumController）
- 関数名：スネークケース（例：get_element_by_xpath）
- クラス名はメンターが指定します。自己定義は禁止。


## コーディング規約（一部）

- `pandas` は `import pandas as pd` を使用
- `gspread` は基本的に `import gspread` のままでOK（as指定なし）



### selenium によるセレクタ優先順位
1.	id  → 最もユニークかつ高速。基本的には第一優先。
2.	name, tag_name → id が無い場合に検討。シンプルな構造で有効。
3.	css selector → 構造に依存するが、柔軟性あり。安定すれば可読性も良い。
4.	xpath → 柔軟だが可読性と保守性に欠けるため、最終手段とする。


## GitHub運用フロー
- `main`：安定版（常に動くコード）
- `dev`：開発中の作業ブランチ
- `feature/〇〇`：個別作業用のブランチ


## コミットメッセージのルール

コミットメッセージは、変更内容に応じて以下のPrefixを**角括弧（[]）で囲って**記述してください。

###  単一の変更

- **[Add]**：新規機能の追加
  - 例）`[Add] ImageDownloaderクラスを追加`

- **[Fix]**：バグ修正・エラー解除
  - 例）`[Fix] スクレイピング中のタイムアウト処理を追加`

- **[Update]**：既存機能の仕様変更や改善
  - 例）`[Update] 画像リサイズ処理を最適化`

- **[Refactor]**：コード整理（動作に影響なし）
  - 例）`[Refactor] コメント削除と関数名のリネーム`

---

###  複数の変更が含まれる場合

複数の変更がある場合は、**スペース区切りで複数のステータスを並べます**。

- **形式：** `[ステータス1] [ステータス2] 説明内容`

#### 例：

- `[Add] [Fix] ImageDownloader追加およびレスポンスエラーの修正`
- `[Update] [Refactor] 終了日判定の見直しと関数の整理`

---

### 補足

- コミットはなるべく **1つの目的に絞って**小まめに行ってください
- やむを得ず複数の変更を含める場合は `[Add] [Fix]` のように2つまで併記を推奨します




### 開発の進め方
1. 作業ごとにIssueを作成（タスク管理）
2. ブランチを切って作業（`feature/〇〇`）
3. コミットしてPush
4. Pull Requestを作成してメンターに提出
5. レビュー後にマージ


## スクリプトの実行方法（概要）
Pythonファイルは `src/main.py` を起点に実行します。



### `.gitignore` の内容
```markdown
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
venv/

# VSCode
.vscode/

# macOS
.DS_Store

# Config (機密情報)
installer/config/credentials.json

# データ出力
installer/data/images/
installer/data/output/
