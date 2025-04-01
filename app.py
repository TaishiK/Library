import os
import sqlite3
import requests
import xml.etree.ElementTree as ET
from flask import Flask, g, render_template, request, jsonify
from datetime import datetime # InstanceID生成用

DATABASE = 'Libraries.db'

app = Flask(__name__, static_folder='static')

app.config['DATABASE'] = DATABASE

# データベース接続を取得する関数
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
        # カラム名でアクセスできるようにする
        db.row_factory = sqlite3.Row
    return db

# アプリケーションコンテキストが終了するときにデータベース接続を閉じる
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# データベーススキーマ定義
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS T00_InstanceIDs (
    InstanceID TEXT PRIMARY KEY,
    ISBN TEXT NOT NULL,
    HitNDLsearch INTEGER,
    LocateNow TEXT,
    LocateInit TEXT,
    CountBorrow INTEGER DEFAULT 0,
    FOREIGN KEY (ISBN) REFERENCES T01_ISBNs(ISBN)
);

CREATE TABLE IF NOT EXISTS T01_ISBNs (
    ISBN TEXT PRIMARY KEY,
    Title TEXT,
    Author TEXT,
    Publisher TEXT,
    IssueYear TEXT,
    Price NUMERIC,
    categoryNumber TEXT,
    Thumbnail INTEGER
);

CREATE TABLE IF NOT EXISTS T04_Locations (
    Location TEXT PRIMARY KEY,
    SerialNumber TEXT,
    LibraryName TEXT,
    AdminMail TEXT,
    CloseTime TEXT,
    DefaultTerm INTEGER,
    categoryTable TEXT,
    MemberOnly INTEGER,
    Department TEXT,
    MonitorType TEXT,
    RemindMail INTEGER
);
"""

# データベースを初期化する関数
def init_db():
    # データベースファイルが存在しない場合のみスキーマを作成
    if not os.path.exists(app.config['DATABASE']):
        print(f"Initializing database: {app.config['DATABASE']}")
        with app.app_context():
            db = get_db()
            try:
                # schema.sqlは使わないので直接SCHEMA_SQL変数を実行
                db.executescript(SCHEMA_SQL)
                db.commit()
                print("Database initialized successfully.")
            except sqlite3.Error as e:
                print(f"An error occurred during database initialization: {e}")
            finally:
                # init_db内で接続を閉じる必要はない (teardown_appcontextで処理される)
                pass
    else:
        print(f"Database {app.config['DATABASE']} already exists.")


# アプリケーション起動時にデータベースを初期化
init_db()

# ルートURLへのアクセス処理 - メインメニューを表示
@app.route('/')
def index():
    return render_template('main_menu.html')

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

# NDL Search API (SRU) から書籍情報を取得する関数
def fetch_from_ndl(isbn):
    base_url = "https://ndlsearch.ndl.go.jp/api/sru"
    params = {
        "operation": "searchRetrieve",
        "version": "1.2",
        "recordSchema": "dcndl",
        "onlyBib": "true",
        "recordPacking": "xml",
        "query": f'isbn="{isbn}" AND dpid="iss-ndl-opac"'
    }
    headers = {'User-Agent': 'MyLibraryApp/1.0'} # 適切なUser-Agentを設定

    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=10) # タイムアウト設定
        response.raise_for_status() # HTTPエラーチェック

        xml_text = response.text
        # print("--- NDL API Response XML ---") # デバッグ用print削除
        # print(xml_text)
        # print("-----------------------------")
        root = ET.fromstring(xml_text)

        # 名前空間の定義 (SRUレスポンスに合わせて調整)
        namespaces = {
            'sru': 'http://www.loc.gov/zing/srw/',
            'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
            'dcndl': 'http://ndl.go.jp/dcndl/terms/',
            'dc': 'http://purl.org/dc/elements/1.1/',
            'dcterms': 'http://purl.org/dc/terms/',
            'foaf': 'http://xmlns.com/foaf/0.1/' # foaf 名前空間を追加
        }

        # XPathで書籍情報を抽出
        record_data = root.find('.//sru:recordData', namespaces)
        if record_data is None:
            return None # レコードデータが見つからない

        bib_resource = record_data.find('.//dcndl:BibResource', namespaces)
        if bib_resource is None:
            return None # 書籍リソースが見つからない

        # 各要素からテキストを取得するヘルパー関数
        def get_text(element, path):
            node = element.find(path, namespaces)
            # XML構造に合わせてXPathを修正
            node = element.find(path, namespaces)
            # 子要素のテキストを取得する場合 (例: dc:title/rdf:Description/rdf:value)
            if node is not None and node.find('./rdf:Description/rdf:value', namespaces) is not None:
                 value_node = node.find('./rdf:Description/rdf:value', namespaces)
                 return value_node.text.strip() if value_node.text else ""
            # 子要素のテキストを取得する場合 (例: dcterms:publisher/foaf:Agent/foaf:name)
            elif node is not None and node.find('./foaf:Agent/foaf:name', namespaces) is not None:
                 name_node = node.find('./foaf:Agent/foaf:name', namespaces)
                 return name_node.text.strip() if name_node.text else ""
            # 要素自身のテキストを取得する場合
            elif node is not None and node.text:
                 return node.text.strip()
            else:
                 return ""

        # タイトル (XPath修正)
        # dc:title/rdf:Description/rdf:value から取得
        title = get_text(bib_resource, './dc:title/rdf:Description/rdf:value')
        # 上記で見つからない場合、直接 dc:title から取得 (フォールバック)
        if not title:
            title = get_text(bib_resource, './dc:title')


        # 著者 (最初の creator を取得 - これは変更なし)
        author = get_text(bib_resource, './dcndl:creator') or get_text(bib_resource, './dc:creator')

        # 出版社 (XPath修正)
        # dcterms:publisher/foaf:Agent/foaf:name から取得
        publisher = get_text(bib_resource, './dcterms:publisher/foaf:Agent/foaf:name')


        # 発行年 (YYYY または YYYY-MM-DD から年のみ抽出 - これは変更なし)
        issued = get_text(bib_resource, './dcterms:issued')
        issue_year = issued[:4] if issued and issued.isdigit() and len(issued) >= 4 else ""
        if not issue_year and '-' in issued: # YYYY-MM-DD形式の場合
             parts = issued.split('-')
             if len(parts[0]) == 4 and parts[0].isdigit():
                 issue_year = parts[0]


        # 価格 (数値のみ抽出)
        price_text = get_text(bib_resource, './dcndl:price')
        price_match = ''.join(filter(str.isdigit, price_text))
        price = int(price_match) if price_match else 0

        # 書籍分類 (NDCの先頭1文字)
        category = ""
        subjects = bib_resource.findall('./dcterms:subject', namespaces)
        for subject in subjects:
            resource_attr = subject.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource')
            if resource_attr and ('/ndc10/' in resource_attr or '/ndc9/' in resource_attr):
                ndc_code = resource_attr.split('/')[-1]
                if ndc_code and ndc_code[0].isdigit():
                    category = ndc_code[0]
                    break # 最初のNDC分類が見つかったら終了

        # 書影有無の確認
        thumbnail_url = f"https://ndlsearch.ndl.go.jp/thumbnail/{isbn}.jpg"
        thumbnail_exists = False
        thumbnail_save_path = None # 保存パスを初期化
        try:
            thumb_response = requests.head(thumbnail_url, timeout=5)
            if thumb_response.status_code == 200 and 'image' in thumb_response.headers.get('Content-Type', ''):
                 thumbnail_exists = True
                 # --- 書影保存処理 ---
                 try:
                     # 保存先ディレクトリ (プロジェクトルート直下の thumbnails)
                     # app.root_path を使うと Flask アプリケーションのルートパスを取得できる
                     thumbnails_dir = os.path.join(app.root_path, 'thumbnails')
                     # ディレクトリが存在しない場合は作成
                     os.makedirs(thumbnails_dir, exist_ok=True)

                     # 保存ファイル名 (ISBN.jpg) - isbn 変数はハイフン除去済み
                     thumbnail_filename = f"{isbn}.jpg"
                     thumbnail_save_path = os.path.join(thumbnails_dir, thumbnail_filename)

                     # 画像データをダウンロードして保存 (既に存在しない場合のみ)
                     if not os.path.exists(thumbnail_save_path):
                         print(f"Downloading thumbnail for {isbn} to {thumbnail_save_path}")
                         img_response = requests.get(thumbnail_url, stream=True, timeout=10)
                         img_response.raise_for_status() # HTTPエラーチェック
                         with open(thumbnail_save_path, 'wb') as f:
                             for chunk in img_response.iter_content(1024):
                                 f.write(chunk)
                         print(f"Thumbnail saved successfully: {thumbnail_save_path}")
                     else:
                         print(f"Thumbnail already exists: {thumbnail_save_path}")

                 except OSError as e:
                     print(f"Error creating thumbnails directory: {e}")
                     # ディレクトリ作成失敗時はログのみ出力し、処理は続行 (thumbnail_exists は True のまま)
                     thumbnail_save_path = None
                 except requests.exceptions.RequestException as e:
                     print(f"Error downloading thumbnail image: {e}")
                     # ダウンロード失敗時もログのみ出力し、処理は続行
                     thumbnail_save_path = None
                 except IOError as e:
                     print(f"Error saving thumbnail image: {e}")
                     # 保存失敗時もログのみ出力し、処理は続行
                     thumbnail_save_path = None
                 # --- 書影保存処理ここまで ---

        except requests.exceptions.RequestException as e:
            print(f"Warning: Error checking thumbnail existence: {e}") # HEADリクエストのエラーもログ出力
            pass # 書影確認エラーは無視するがログは出す

        # 返却する辞書 (thumbnail_save_path は含めない)
        return {
            "title": title,
            "author": author,
            "publisher": publisher,
            "issueYear": issue_year,
            "price": price,
            "category": category,
            "thumbnail_url": thumbnail_url,
            "thumbnail_exists": thumbnail_exists,
            "hit_ndl": True # APIから取得成功
        }

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from NDL API: {e}")
        return None # APIエラー
    except ET.ParseError as e:
        print(f"Error parsing XML from NDL API: {e}")
        return None # XMLパースエラー

# APIエンドポイント: 書籍情報取得
@app.route('/api/fetch_book_info', methods=['POST'])
def api_fetch_book_info():
    data = request.get_json()
    isbn = data.get('isbn')

    if not isbn:
        return jsonify({"error": "ISBN is required"}), 400

    # ハイフンを除去
    isbn_cleaned = isbn.replace('-', '')

    # NDL APIから情報を取得
    book_info = fetch_from_ndl(isbn_cleaned)

    if book_info:
        return jsonify(book_info)
    else:
        # APIで取得できなかった場合、基本的な情報を返す
        return jsonify({
            "title": "",
            "author": "",
            "publisher": "",
            "issueYear": "",
            "price": 0,
            "category": "",
            "thumbnail_url": f"https://ndlsearch.ndl.go.jp/thumbnail/{isbn_cleaned}.jpg",
            "thumbnail_exists": False,
            "hit_ndl": False # APIから取得失敗
        })

# データベース操作関数: T01_ISBNs に登録/更新
def register_isbn_data(db, isbn, title, author, publisher, issueyear, price, category, thumbnail_exists):
    # SQLiteではUPSERT (INSERT OR REPLACE) を使用
    query = """
    INSERT OR REPLACE INTO T01_ISBNs (ISBN, Title, Author, Publisher, IssueYear, Price, categoryNumber, Thumbnail)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """
    try:
        db.execute(query, (isbn, title, author, publisher, issueyear, price, category, 1 if thumbnail_exists else 0))
        db.commit()
        print(f"Registered/Updated ISBN: {isbn}")
        return True
    except sqlite3.Error as e:
        db.rollback() # エラー時はロールバック
        print(f"Error registering/updating ISBN {isbn}: {e}")
        return False

# データベース操作関数: T00_InstanceIDs に登録
def register_instance_data(db, isbn, hit_ndl):
    # InstanceIDを生成 (YYMMDD_HHMMSS)
    instance_id = datetime.now().strftime('%y%m%d_%H%M%S')
    # 初期保管場所 (例)
    locate_init = '登録待機場所'
    locate_now = locate_init

    query = """
    INSERT INTO T00_InstanceIDs (InstanceID, ISBN, HitNDLsearch, LocateNow, LocateInit)
    VALUES (?, ?, ?, ?, ?);
    """
    try:
        db.execute(query, (instance_id, isbn, 1 if hit_ndl else 0, locate_now, locate_init))
        db.commit()
        print(f"Registered InstanceID: {instance_id} for ISBN: {isbn}")
        return instance_id # 登録したInstanceIDを返す
    except sqlite3.Error as e:
        db.rollback() # エラー時はロールバック
        print(f"Error registering InstanceID for ISBN {isbn}: {e}")
        return None

# APIエンドポイント: 書籍登録
@app.route('/api/register_book', methods=['POST'])
def api_register_book():
    data = request.get_json()
    isbn = data.get('isbn')
    title = data.get('title')
    author = data.get('author')
    publisher = data.get('publisher')
    issue_year = data.get('issueYear')
    price = data.get('price')
    category = data.get('category')
    hit_ndl = data.get('hit_ndl', False) # フロントから送られてくる想定
    thumbnail_exists = data.get('thumbnail_exists', False) # フロントから送られてくる想定

    if not isbn:
        return jsonify({"error": "ISBN is required"}), 400

    # ISBNのハイフン除去
    isbn_cleaned = isbn.replace('-', '')

    db = get_db()

    # 1. T01_ISBNs に登録/更新
    isbn_success = register_isbn_data(db, isbn_cleaned, title, author, publisher, issue_year, price, category, thumbnail_exists)

    if not isbn_success:
        return jsonify({"error": "Failed to register ISBN data"}), 500

    # 2. T00_InstanceIDs に登録
    instance_id = register_instance_data(db, isbn_cleaned, hit_ndl)

    if instance_id:
        return jsonify({"success": True, "message": "Book registered successfully", "instance_id": instance_id})
    else:
        # ISBN登録は成功したがInstance登録に失敗した場合、ISBN登録をロールバックすべきか？
        # 今回はシンプルにInstance登録失敗のエラーを返す
        return jsonify({"error": "Failed to register book instance"}), 500


if __name__ == '__main__':
    # init_db() # init_dbは起動時に一度だけ実行されれば良い
    app.run(debug=True) # デバッグモードで起動


import subprocess
import os
import time
from flask import Flask, jsonify

# 既存のコードをそのまま残す
DATABASE = 'Libraries.db'

app = Flask(__name__, static_folder='static')

app.config['DATABASE'] = DATABASE

# データベース接続を取得する関数
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
        # カラム名でアクセスできるようにする
        db.row_factory = sqlite3.Row
    return db

# アプリケーションコンテキストが終了するときにデータベース接続を閉じる
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# データベーススキーマ定義
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS T00_InstanceIDs (
    InstanceID TEXT PRIMARY KEY,
    ISBN TEXT NOT NULL,
    HitNDLsearch INTEGER,
    LocateNow TEXT,
    LocateInit TEXT,
    CountBorrow INTEGER DEFAULT 0,
    FOREIGN KEY (ISBN) REFERENCES T01_ISBNs(ISBN)
);

CREATE TABLE IF NOT EXISTS T01_ISBNs (
    ISBN TEXT PRIMARY KEY,
    Title TEXT,
    Author TEXT,
    Publisher TEXT,
    IssueYear TEXT,
    Price NUMERIC,
    categoryNumber TEXT,
    Thumbnail INTEGER
);

CREATE TABLE IF NOT EXISTS T04_Locations (
    Location TEXT PRIMARY KEY,
    SerialNumber TEXT,
    LibraryName TEXT,
    AdminMail TEXT,
    CloseTime TEXT,
    DefaultTerm INTEGER,
    categoryTable TEXT,
    MemberOnly INTEGER,
    Department TEXT,
    MonitorType TEXT,
    RemindMail INTEGER
);
"""

# データベースを初期化する関数
def init_db():
    # データベースファイルが存在しない場合のみスキーマを作成
    if not os.path.exists(app.config['DATABASE']):
        print(f"Initializing database: {app.config['DATABASE']}")
        with app.app_context():
            db = get_db()
            try:
                # schema.sqlは使わないので直接SCHEMA_SQL変数を実行
                db.executescript(SCHEMA_SQL)
                db.commit()
                print("Database initialized successfully.")
            except sqlite3.Error as e:
                print(f"An error occurred during database initialization: {e}")
            finally:
                # init_db内で接続を閉じる必要はない (teardown_appcontextで処理される)
                pass
    else:
        print(f"Database {app.config['DATABASE']} already exists.")


# アプリケーション起動時にデータベースを初期化
init_db()

# ルートURLへのアクセス処理 - メインメニューを表示
@app.route('/')
def index():
    return render_template('main_menu.html')

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

# NDL Search API (SRU) から書籍情報を取得する関数
def fetch_from_ndl(isbn):
    base_url = "https://ndlsearch.ndl.go.jp/api/sru"
    params = {
        "operation": "searchRetrieve",
        "version": "1.2",
        "recordSchema": "dcndl",
        "onlyBib": "true",
        "recordPacking": "xml",
        "query": f'isbn="{isbn}" AND dpid="iss-ndl-opac"'
    }
    headers = {'User-Agent': 'MyLibraryApp/1.0'} # 適切なUser-Agentを設定

    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=10) # タイムアウト設定
        response.raise_for_status() # HTTPエラーチェック

        xml_text = response.text
        # print("--- NDL API Response XML ---") # デバッグ用print削除
        # print(xml_text)
        # print("-----------------------------")
        root = ET.fromstring(xml_text)

        # 名前空間の定義 (SRUレスポンスに合わせて調整)
        namespaces = {
            'sru': 'http://www.loc.gov/zing/srw/',
            'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
            'dcndl': 'http://ndl.go.jp/dcndl/terms/',
            'dc': 'http://purl.org/dc/elements/1.1/',
            'dcterms': 'http://purl.org/dc/terms/',
            'foaf': 'http://xmlns.com/foaf/0.1/' # foaf 名前空間を追加
        }

        # XPathで書籍情報を抽出
        record_data = root.find('.//sru:recordData', namespaces)
        if record_data is None:
            return None # レコードデータが見つからない

        bib_resource = record_data.find('.//dcndl:BibResource', namespaces)
        if bib_resource is None:
            return None # 書籍リソースが見つからない

        # 各要素からテキストを取得するヘルパー関数
        def get_text(element, path):
            node = element.find(path, namespaces)
            # XML構造に合わせてXPathを修正
            node = element.find(path, namespaces)
            # 子要素のテキストを取得する場合 (例: dc:title/rdf:Description/rdf:value)
            if node is not None and node.find('./rdf:Description/rdf:value', namespaces) is not None:
                 value_node = node.find('./rdf:Description/rdf:value', namespaces)
                 return value_node.text.strip() if value_node.text else ""
            # 子要素のテキストを取得する場合 (例: dcterms:publisher/foaf:Agent/foaf:name)
            elif node is not None and node.find('./foaf:Agent/foaf:name', namespaces) is not None:
                 name_node = node.find('./foaf:Agent/foaf:name', namespaces)
                 return name_node.text.strip() if name_node.text else ""
            # 要素自身のテキストを取得する場合
            elif node is not None and node.text:
                 return node.text.strip()
            else:
                 return ""

        # タイトル (XPath修正)
        # dc:title/rdf:Description/rdf:value から取得
        title = get_text(bib_resource, './dc:title/rdf:Description/rdf:value')
        # 上記で見つからない場合、直接 dc:title から取得 (フォールバック)
        if not title:
            title = get_text(bib_resource, './dc:title')


        # 著者 (最初の creator を取得 - これは変更なし)
        author = get_text(bib_resource, './dcndl:creator') or get_text(bib_resource, './dc:creator')

        # 出版社 (XPath修正)
        # dcterms:publisher/foaf:Agent/foaf:name から取得
        publisher = get_text(bib_resource, './dcterms:publisher/foaf:Agent/foaf:name')


        # 発行年 (YYYY または YYYY-MM-DD から年のみ抽出 - これは変更なし)
        issued = get_text(bib_resource, './dcterms:issued')
        issue_year = issued[:4] if issued and issued.isdigit() and len(issued) >= 4 else ""
        if not issue_year and '-' in issued: # YYYY-MM-DD形式の場合
             parts = issued.split('-')
             if len(parts[0]) == 4 and parts[0].isdigit():
                 issue_year = parts[0]


        # 価格 (数値のみ抽出)
        price_text = get_text(bib_resource, './dcndl:price')
        price_match = ''.join(filter(str.isdigit, price_text))
        price = int(price_match) if price_match else 0

        # 書籍分類 (NDCの先頭1文字)
        category = ""
        subjects = bib_resource.findall('./dcterms:subject', namespaces)
        for subject in subjects:
            resource_attr = subject.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource')
            if resource_attr and ('/ndc10/' in resource_attr or '/ndc9/' in resource_attr):
                ndc_code = resource_attr.split('/')[-1]
                if ndc_code and ndc_code[0].isdigit():
                    category = ndc_code[0]
                    break # 最初のNDC分類が見つかったら終了

        # 書影有無の確認
        thumbnail_url = f"https://ndlsearch.ndl.go.jp/thumbnail/{isbn}.jpg"
        thumbnail_exists = False
        thumbnail_save_path = None # 保存パスを初期化
        try:
            thumb_response = requests.head(thumbnail_url, timeout=5)
            if thumb_response.status_code == 200 and 'image' in thumb_response.headers.get('Content-Type', ''):
                 thumbnail_exists = True
                 # --- 書影保存処理 ---
                 try:
                     # 保存先ディレクトリ (プロジェクトルート直下の thumbnails)
                     # app.root_path を使うと Flask アプリケーションのルートパスを取得できる
                     thumbnails_dir = os.path.join(app.root_path, 'thumbnails')
                     # ディレクトリが存在しない場合は作成
                     os.makedirs(thumbnails_dir, exist_ok=True)

                     # 保存ファイル名 (ISBN.jpg) - isbn 変数はハイフン除去済み
                     thumbnail_filename = f"{isbn}.jpg"
                     thumbnail_save_path = os.path.join(thumbnails_dir, thumbnail_filename)

                     # 画像データをダウンロードして保存 (既に存在しない場合のみ)
                     if not os.path.exists(thumbnail_save_path):
                         print(f"Downloading thumbnail for {isbn} to {thumbnail_save_path}")
                         img_response = requests.get(thumbnail_url, stream=True, timeout=10)
                         img_response.raise_for_status() # HTTPエラーチェック
                         with open(thumbnail_save_path, 'wb') as f:
                             for chunk in img_response.iter_content(1024):
                                 f.write(chunk)
                         print(f"Thumbnail saved successfully: {thumbnail_save_path}")
                     else:
                         print(f"Thumbnail already exists: {thumbnail_save_path}")

                 except OSError as e:
                     print(f"Error creating thumbnails directory: {e}")
                     # ディレクトリ作成失敗時はログのみ出力し、処理は続行 (thumbnail_exists は True のまま)
                     thumbnail_save_path = None
                 except requests.exceptions.RequestException as e:
                     print(f"Error downloading thumbnail image: {e}")
                     # ダウンロード失敗時もログのみ出力し、処理は続行
                     thumbnail_save_path = None
                 except IOError as e:
                     print(f"Error saving thumbnail image: {e}")
                     # 保存失敗時もログのみ出力し、処理は続行
                     thumbnail_save_path = None
                 # --- 書影保存処理ここまで ---

        except requests.exceptions.RequestException as e:
            print(f"Warning: Error checking thumbnail existence: {e}") # HEADリクエストのエラーもログ出力
            pass # 書影確認エラーは無視するがログは出す

        # 返却する辞書 (thumbnail_save_path は含めない)
        return {
            "title": title,
            "author": author,
            "publisher": publisher,
            "issueYear": issue_year,
            "price": price,
            "category": category,
            "thumbnail_url": thumbnail_url,
            "thumbnail_exists": thumbnail_exists,
            "hit_ndl": True # APIから取得成功
        }

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from NDL API: {e}")
        return None # APIエラー
    except ET.ParseError as e:
        print(f"Error parsing XML from NDL API: {e}")
        return None # XMLパースエラー

# APIエンドポイント: 書籍情報取得
@app.route('/api/fetch_book_info', methods=['POST'])
def api_fetch_book_info():
    data = request.get_json()
    isbn = data.get('isbn')

    if not isbn:
        return jsonify({"error": "ISBN is required"}), 400

    # ハイフンを除去
    isbn_cleaned = isbn.replace('-', '')

    # NDL APIから情報を取得
    book_info = fetch_from_ndl(isbn_cleaned)

    if book_info:
        return jsonify(book_info)
    else:
        # APIで取得できなかった場合、基本的な情報を返す
        return jsonify({
            "title": "",
            "author": "",
            "publisher": "",
            "issueYear": "",
            "price": 0,
            "category": "",
            "thumbnail_url": f"https://ndlsearch.ndl.go.jp/thumbnail/{isbn_cleaned}.jpg",
            "thumbnail_exists": False,
            "hit_ndl": False # APIから取得失敗
        })

# データベース操作関数: T01_ISBNs に登録/更新
def register_isbn_data(db, isbn, title, author, publisher, issueyear, price, category, thumbnail_exists):
    # SQLiteではUPSERT (INSERT OR REPLACE) を使用
    query = """
    INSERT OR REPLACE INTO T01_ISBNs (ISBN, Title, Author, Publisher, IssueYear, Price, categoryNumber, Thumbnail)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """
    try:
        db.execute(query, (isbn, title, author, publisher, issueyear, price, category, 1 if thumbnail_exists else 0))
        db.commit()
        print(f"Registered/Updated ISBN: {isbn}")
        return True
    except sqlite3.Error as e:
        db.rollback() # エラー時はロールバック
        print(f"Error registering/updating ISBN {isbn}: {e}")
        return False

# データベース操作関数: T00_InstanceIDs に登録
def register_instance_data(db, isbn, hit_ndl):
    # InstanceIDを生成 (YYMMDD_HHMMSS)
    instance_id = datetime.now().strftime('%y%m%d_%H%M%S')
    # 初期保管場所 (例)
    locate_init = '登録待機場所'
    locate_now = locate_init

    query = """
    INSERT INTO T00_InstanceIDs (InstanceID, ISBN, HitNDLsearch, LocateNow, LocateInit)
    VALUES (?, ?, ?, ?, ?);
    """
    try:
        db.execute(query, (instance_id, isbn, 1 if hit_ndl else 0, locate_now, locate_init))
        db.commit()
        print(f"Registered InstanceID: {instance_id} for ISBN: {isbn}")
        return instance_id # 登録したInstanceIDを返す
    except sqlite3.Error as e:
        db.rollback() # エラー時はロールバック
        print(f"Error registering InstanceID for ISBN {isbn}: {e}")
        return None

# APIエンドポイント: 書籍登録
@app.route('/api/register_book', methods=['POST'])
def api_register_book():
    data = request.get_json()
    isbn = data.get('isbn')
    title = data.get('title')
    author = data.get('author')
    publisher = data.get('publisher')
    issue_year = data.get('issueYear')
    price = data.get('price')
    category = data.get('category')
    hit_ndl = data.get('hit_ndl', False) # フロントから送られてくる想定
    thumbnail_exists = data.get('thumbnail_exists', False) # フロントから送られてくる想定

    if not isbn:
        return jsonify({"error": "ISBN is required"}), 400

    # ISBNのハイフン除去
    isbn_cleaned = isbn.replace('-', '')

    db = get_db()

    # 1. T01_ISBNs に登録/更新
    isbn_success = register_isbn_data(db, isbn_cleaned, title, author, publisher, issue_year, price, category, thumbnail_exists)

    if not isbn_success:
        return jsonify({"error": "Failed to register ISBN data"}), 500

    # 2. T00_InstanceIDs に登録
    instance_id = register_instance_data(db, isbn_cleaned, hit_ndl)

    if instance_id:
        return jsonify({"success": True, "message": "Book registered successfully", "instance_id": instance_id})
    else:
        # ISBN登録は成功したがInstance登録に失敗した場合、ISBN登録をロールバックすべきか？
        # 今回はシンプルにInstance登録失敗のエラーを返す
        return jsonify({"error": "Failed to register book instance"}), 500


@app.route('/execute_yorimichi')
def execute_yorimichi():
    try:
        # 1. プロセスの実行
        process_z = subprocess.Popen([os.path.join("exes", "yorimichi_z.exe")], creationflags=subprocess.CREATE_NO_WINDOW)
        process_z2 = subprocess.Popen([os.path.join("exes", "yorimichi_z2.exe")], creationflags=subprocess.CREATE_NO_WINDOW)

        # 2. タイムアウト設定
        timeout = 20  # 秒

        # 3. プロセスの監視とタイムアウト処理
        start_time = time.time()
        while True:
            # プロセスの終了をポーリング
            return_code_z = process_z.poll()
            return_code_z2 = process_z2.poll()

            # いずれかのプロセスが終了した場合
            if return_code_z is not None or return_code_z2 is not None:
                break

            # タイムアウトチェック
            elapsed_time = time.time() - start_time
            if elapsed_time > timeout:
                print("タイムアウト: プロセスを強制終了します")
                process_z.terminate()
                process_z2.terminate()
                return jsonify({'status': 'timeout', 'message': '社員証が検出されませんでした。'})

            # 短いスリープ
            time.sleep(0.1)

        # 4. プロセスの終了コードの確認
        if return_code_z == 0 and return_code_z2 == 0:
            print("プロセスは正常に終了しました")
            return jsonify({'status': 'success', 'message': 'プロセスは正常に終了しました'})
        else:
            print(f"プロセスはエラーで終了しました (終了コード: {return_code_z}, {return_code_z2})")
            return jsonify({'status': 'error', 'message': f'プロセスはエラーで終了しました (終了コード: {return_code_z}, {return_code_z2})'})

    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    app.run(debug=True)