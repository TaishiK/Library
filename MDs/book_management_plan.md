# 書籍管理システム フロントエンド実装計画

**1. 目的:**
ユーザー指定の仕様に基づき、書籍管理システムのメインメニュー画面、管理メニュー画面のHTML/CSS/JSを作成し、Flask (`app.py`) のルーティングを修正する。

**2. 成果物:**
*   `/templates/main_menu.html` (新規作成)
*   `/templates/control_menu.html` (新規作成)
*   `/static/css/style.css` (新規作成)
*   `/static/js/navigation.js` (新規作成)
*   `app.py` の修正箇所 (コードスニペット)

**3. 実装ステップ:**

**Step 1: ファイルの準備**
*   以下の空ファイルを作成します。
    *   `/templates/main_menu.html`
    *   `/templates/control_menu.html`
    *   `/static/css/style.css`
    *   `/static/js/navigation.js`
    *   (必要に応じて `/static/css` と `/static/js` ディレクトリも作成)

**Step 2: HTMLの実装 (`main_menu.html`)**
*   基本的なHTML5構造 (`<!DOCTYPE html>`, `<html>`, `<head>`, `<body>`) を記述します。
*   `<head>` 内で `/static/css/style.css` をリンクします。
*   `<body>` 内に以下の要素を配置します。
    *   ヘッダー領域 (Flexbox等で左右配置):
        *   左側: 「管理メニュー」ボタン (`id="gotoControlMenu"`, `class="btn btn-small"`), 「棚番号確認」ボタン (`class="btn btn-small"`)
        *   右側: 「終了」ボタン (`class="btn btn-small"`), 「最終操作確認」ボタン (`class="btn btn-small"`)
    *   フッター領域 (Flexbox等で中央寄せまたは均等配置):
        *   「貸出」ボタン (`class="btn btn-large"`), 「返却」ボタン (`class="btn btn-large"`)
*   `<body>` の末尾で `/static/js/navigation.js` を読み込みます (`<script src="/static/js/navigation.js" defer></script>`)。

**Step 3: HTMLの実装 (`control_menu.html`)**
*   基本的なHTML5構造を記述します。
*   `<head>` 内で `/static/css/style.css` をリンクします。
*   `<body>` 内に以下の要素を配置します。
    *   メインコンテンツ領域 (Grid Layout 5x3):
        *   指定されたラベルを持つ15個のボタン (`class="btn btn-medium"`) を配置します。
        *   「日本書籍登録」ボタンに `id="gotoBookRegistration"` を付与します。
        *   「メインメニュー」ボタンに `id="gotoMainMenu"` を付与します。
*   `<body>` の末尾で `/static/js/navigation.js` を読み込みます。

**Step 4: CSSの実装 (`style.css`)**
*   基本的なスタイルを設定します (例: `box-sizing: border-box;`)。
*   `body` のフォントなどを設定します。
*   `main_menu.html` 用のレイアウトスタイル:
    *   ヘッダーとフッターのコンテナ要素に `display: flex` を適用し、`justify-content` や `align-items` で配置を調整します。
*   `control_menu.html` 用のレイアウトスタイル:
    *   ボタンを配置するコンテナ要素に `display: grid` を適用し、`grid-template-columns: repeat(3, 1fr);` や `gap` を設定します。
*   ボタン共通スタイル (`.btn`):
    *   `padding`, `margin`, `border`, `text-align`, `cursor: pointer` などを設定します。
*   ボタンサイズ別スタイル:
    *   `.btn-small`: 小さめの `padding`, `font-size`。
    *   `.btn-medium`: 中くらいの `padding`, `font-size`。
    *   `.btn-large`: 大きめの `padding`, `font-size`。
*   アクセシビリティ: ボタンの `:focus` スタイルを定義します (例: `outline: 2px solid blue;`)。

**Step 5: JavaScriptの実装 (`navigation.js`)**
*   `DOMContentLoaded` イベント内で処理を開始します。
*   `main_menu.html` 用:
    *   `document.getElementById('gotoControlMenu')` でボタンを取得し、nullチェックを行います。
    *   クリックイベントリスナーを追加し、`window.location.href = '/control_menu';` を実行します。
*   `control_menu.html` 用:
    *   `document.getElementById('gotoBookRegistration')` でボタンを取得し、nullチェックを行います。
    *   クリックイベントリスナーを追加し、`window.location.href = '/book_registration';` を実行します。
    *   `document.getElementById('gotoMainMenu')` でボタンを取得し、nullチェックを行います。
    *   クリックイベントリスナーを追加し、`window.location.href = '/';` を実行します。
*   (任意) 他のボタンにもイベントリスナーを追加し、`console.log` で未実装メッセージを表示します。

**Step 6: Flaskバックエンドの修正 (`app.py`)**
*   `index()` 関数を修正:
    *   `render_template('book_registration.html', books=books)` を `render_template('main_menu.html')` に変更します。
    *   `books` 変数を取得するデータベースクエリは不要になります。
*   新しいルートを追加:
    ```python
    @app.route('/control_menu')
    def control_menu():
        return render_template('control_menu.html')

    @app.route('/book_registration')
    def book_registration():
        # templates/book_registration.html が一覧表示を必要とするため、
        # 元の index() と同様のデータ取得処理を行う
        db = get_db()
        query = """
        SELECT
            i.InstanceID, i.ISBN,
            COALESCE(b.Title, 'N/A') AS Title, COALESCE(b.Author, 'N/A') AS Author,
            COALESCE(b.Publisher, 'N/A') AS Publisher, COALESCE(b.IssueYear, 'N/A') AS IssueYear,
            COALESCE(b.Price, 'N/A') AS Price, COALESCE(b.categoryNumber, 'N/A') AS categoryNumber
        FROM T00_InstanceIDs i
        LEFT JOIN T01_ISBNs b ON i.ISBN = b.ISBN
        ORDER BY i.InstanceID DESC;
        """
        books = db.execute(query).fetchall()
        return render_template('book_registration.html', books=books)
    ```

**4. 画面遷移図:**

```mermaid
graph LR
    A[/ (main_menu.html)] -- "管理メニュー" --> B[/control_menu (control_menu.html)];
    B -- "日本書籍登録" --> C[/book_registration (book_registration.html)];
    B -- "メインメニュー" --> A;
    C -- (ブラウザバック等) --> B;
    A -- (その他ボタン) --> A;
    B -- (その他ボタン) --> B;