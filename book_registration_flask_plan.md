# 書籍登録Webアプリケーション開発計画 (Flask + SQLite + NDL API)

## 1. 目的

Python FlaskフレームワークとSQLite3データベースを使用し、`book_registration.html` をフロントエンドテンプレートとして利用した書籍登録Webアプリケーションを開発する。国立国会図書館サーチAPI (NDL Search API) と連携し、ISBNに基づいた書籍情報の取得とデータベースへの登録機能を実現する。

## 2. プロジェクト構成

ご指定の通り、以下の構成とします。

```
/ (プロジェクトルート)
|-- app.py             # Flaskアプリケーション本体、DB初期化、ルーティング、API連携
|-- templates/
|   |-- book_registration.html # 書籍情報入力・表示用HTMLテンプレート (既存ファイルを修正)
|-- thumbnails/        # 書影画像保存用 (今回はディレクトリ作成のみ)
|-- Libraries.db       # SQLiteデータベースファイル (app.py実行時に自動生成)
```

## 3. 開発ステップ

### ステップ 1: 環境設定と基本構造の準備

1.  **必要なライブラリのインストール:**
    ```bash
    pip install Flask requests
    ```
2.  **プロジェクトディレクトリとファイルの作成:**
    *   プロジェクトルートディレクトリを作成。
    *   `app.py` ファイルを作成。
    *   `templates` ディレクトリを作成し、既存の `book_registration.html` を配置。
    *   `thumbnails` ディレクトリを作成。

### ステップ 2: データベース初期化処理の実装 (`app.py`)

1.  `app.py` 内に、`Libraries.db` が存在しない場合に、指定されたスキーマ（`T00_InstanceIDs`, `T01_ISBNs`, `T04_Locations`）でテーブルを作成する関数 `init_db()` を実装する。
2.  Flaskアプリケーション起動時に `init_db()` が呼び出されるようにする。

### ステップ 3: Flaskルーティングと基本HTML表示 (`app.py`)

1.  Flaskアプリケーションインスタンスを作成する。
2.  ルート `/` へのGETリクエストに対して `templates/book_registration.html` をレンダリングするルート `@app.route('/')` を定義する。
    *   初期表示では、データベースから登録済みの書籍データ（`T00_InstanceIDs` と `T01_ISBNs` をJOIN）を取得し、テンプレートに渡す処理も追加する。

### ステップ 4: NDL Search API連携バックエンド処理 (`app.py`)

1.  `/api/fetch_book_info` というエンドポイント (POSTリクエスト) を作成する。
2.  フロントエンドから送信されたISBNを受け取る。
3.  `requests` ライブラリを使用して、NDL Search API (SRUエンドポイント: `https://ndlsearch.ndl.go.jp/api/sru`) に問い合わせる関数 `fetch_from_ndl(isbn)` を実装する。
    *   XMLレスポンスをパースし、書名 (`Title`)、著者 (`Author`)、出版社 (`Publisher`)、発行年 (`IssueYear`)、書影有無 (`Thumbnail` フラグ) を抽出する。
    *   書影有無は、`https://ndlsearch.ndl.go.jp/thumbnail/{isbn}.jpg` へのアクセス可否（例: `requests.head` で確認）で判断する。
4.  取得した書籍情報と書影有無フラグ、書影URL (`thumbnail_url`) を含むJSONレスポンスをフロントエンドに返す。
5.  APIからの取得成否を示すフラグ (`hit_ndl`) もJSONに含める。

### ステップ 5: 書籍登録バックエンド処理 (`app.py`)

1.  `/api/register_book` というエンドポイント (POSTリクエスト) を作成する。
2.  フロントエンドから送信された書籍データ（ISBN, Title, Author, Publisher, IssueYear, Price, categoryNumber など）と、ステップ4で取得した `hit_ndl`, `thumbnail_exists` フラグを受け取る。
3.  データベース操作関数を実装する:
    *   `register_isbn_data(isbn, title, author, publisher, issueyear, price, category, thumbnail_exists)`: `T01_ISBNs` テーブルにデータを登録または更新する。`Thumbnail` カラムには `thumbnail_exists` フラグの値を保存する。
    *   `register_instance_data(isbn, hit_ndl)`: `T00_InstanceIDs` テーブルに新しい書籍インスタンスを登録する。
        *   `InstanceID` を `YYMMDD_HHMMSS` 形式で生成する。
        *   `HitNDLsearch` カラムには `hit_ndl` フラグの値を保存する。
        *   `LocateInit`, `LocateNow` には初期値（例: '登録待機場所'）を設定する。`CountBorrow` はデフォルトの0。
4.  受け取ったデータを用いて上記関数を呼び出し、データベースに登録する。
5.  登録成功を示すJSONレスポンスを返す。

### ステップ 6: フロントエンド (`book_registration.html`) の修正

1.  **`fetchBookInfo()` 関数の修正:**
    *   `fetch` APIの送信先を Flask の `/api/fetch_book_info` エンドポイントに変更する (POSTメソッド)。
    *   リクエストボディに `{ "isbn": isbn }` を含める。
    *   レスポンスJSONを受け取り、フォームの各フィールド (`title`, `author`, `publisher`, `issueYear`, `price`, `category`) に値を設定する。
    *   レスポンス内の書影URL (`thumbnail_url`) と書影有無フラグ (`thumbnail_exists`) を使用して、書影画像 (`#bookThumbnail`) または「書影が見つかりません」メッセージ (`#thumbnailMessage`) を表示/非表示する。
    *   API取得成否フラグ (`hit_ndl`) と書影有無フラグ (`thumbnail_exists`) を、後の登録処理で使えるように保持する（例: hidden input や JavaScript 変数）。
2.  **`registerBook()` 関数の修正:**
    *   `event.preventDefault()` を呼び出す。
    *   フォームから書籍データを取得する。
    *   `fetchBookInfo` で保持した `hit_ndl`, `thumbnail_exists` フラグも取得する。
    *   `fetch` APIを使用して、Flask の `/api/register_book` エンドポイントに書籍データとフラグをPOSTリクエストで送信する。
    *   **localStorage関連の処理 (`saveBookData`, `localStorage.setItem` など) を削除またはコメントアウトする。**
    *   登録成功後、ページをリロードするか、非同期で一覧を更新する（今回はリロードが簡単）。
3.  **登録データ一覧表示の修正:**
    *   `displayBookData()` 関数と `localStorage.getItem` 関連の処理を削除またはコメントアウトする。
    *   テーブル (`#bookTable tbody`) の内容は、Flaskが `/` ルートでレンダリング時に渡すデータに基づいてサーバーサイドで生成されるようにする (Jinja2テンプレートを使用)。
4.  **その他:**
    *   `generateInstanceID()` 関数は不要になるため削除。
    *   `clearForm()` 関数は残し、登録成功後にフォームをクリアするために使用できる。

## 4. データベーススキーマ

ご指定の通り、以下の3テーブル構成とします。

*   `T00_InstanceIDs` (InstanceID PK, ISBN FK, HitNDLsearch, LocateNow, LocateInit, CountBorrow)
*   `T01_ISBNs` (ISBN PK, Title, Author, Publisher, IssueYear, Price, categoryNumber, Thumbnail)
*   `T04_Locations` (Location PK, SerialNumber, LibraryName, AdminMail, CloseTime, DefaultTerm, categoryTable, MemberOnly, Department, MonitorType, RemindMail) - ※初期化のみ行い、今回の機能では直接的なデータの追加・更新は行わない。

## 5. 処理フロー (Mermaid シーケンス図)

```mermaid
sequenceDiagram
    participant User as ユーザー
    participant Browser as ブラウザ (book_registration.html)
    participant FlaskApp as Flaskアプリ (app.py)
    participant NDLSearchAPI as 国立国会図書館サーチAPI
    participant Database as SQLite (Libraries.db)

    User->>Browser: ページアクセス (/)
    Browser->>FlaskApp: GET /
    FlaskApp->>Database: 登録済み書籍データを取得
    Database-->>FlaskApp: 書籍データ
    FlaskApp->>Browser: HTML (書籍データ含む) をレンダリング
    Browser->>User: 登録フォームと一覧を表示

    User->>Browser: ISBNを入力
    User->>Browser: 「書籍情報取得」ボタンをクリック
    Browser->>Browser: fetchBookInfo() 実行
    Browser->>FlaskApp: POST /api/fetch_book_info (ISBN)
    FlaskApp->>NDLSearchAPI: 書籍情報をリクエスト (ISBN)
    NDLSearchAPI-->>FlaskApp: 書籍情報 (XML)
    FlaskApp->>FlaskApp: XMLをパース、書影有無確認
    FlaskApp->>Browser: JSON (書籍情報, 書影URL, hit_ndl, thumbnail_exists)
    Browser->>Browser: フォームに情報自動入力、書影表示/メッセージ表示
    Browser->>User: フォーム更新

    User->>Browser: (必要なら情報を修正)
    User->>Browser: 「登録」ボタンをクリック
    Browser->>Browser: registerBook() 実行
    Browser->>FlaskApp: POST /api/register_book (フォームデータ, フラグ)
    FlaskApp->>Database: T01_ISBNs に登録/更新
    Database-->>FlaskApp: 成功/失敗
    FlaskApp->>Database: T00_InstanceIDs に登録 (InstanceID生成)
    Database-->>FlaskApp: 成功/失敗
    FlaskApp->>Browser: JSON (登録成功)
    Browser->>Browser: フォームクリア、ページリロード or 一覧更新
    User->>User: 登録完了を確認 (リロード後の画面)