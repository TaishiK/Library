import os
import sys
import sqlite3
import requests
import xml.etree.ElementTree as ET
from flask import Flask, g, render_template, request, jsonify
from datetime import datetime # InstanceID生成用
import nfc
import binascii
import ldap # python-ldap ライブラリをインポート
import ldap.sasl # SASL認証のためにインポート
#from ldap3 import Server, Connection, ALL, SASL, GSSAPI # ldap3ライブラリを使用する場合
#import gssapi # GSSAPI認証のためにインポート

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

# --- LDAP設定 (実際の環境に合わせて調整してください) ---
# VBAコードから推測される設定値を使用。必要に応じて変更してください。
LDAP_SERVER_URL = 'LDAPS://LDAP.jp.sony.com' # ADS_USE_SSLからLDAPSと判断→AccessがLDAP://なので合わせた
LDAP_BASE_DN_FOR_SEARCH = 'OU=Users,OU=JPUsers,DC=jp,DC=sony,DC=com'
# ----------------------------------------------------

# --- PythonでのLDAP検索関数 ---
def get_ldap_user_info_python(gid):
    """
    LDAPサーバーから指定されたGID (社員番号) のユーザー情報を取得します。
    SASL GSSAPI (Kerberos) 認証を試みます。

    :param gid: 検索するユーザーのGID (社員番号)
    :return: ユーザー情報を含む辞書、またはエラー情報を含む辞書
    """
    user_dn = f"CN={gid},{LDAP_BASE_DN_FOR_SEARCH}"
    l = None # LDAPObject インスタンスを初期化

    try:
        # LDAPサーバーに接続
        # ldap.initialize は接続を確立せず、LDAPObject インスタンスを作成するだけです。
        # 実際の接続は bind や search などの操作時に行われます。
        l = ldap.initialize(LDAP_SERVER_URL, trace_level=3) # trace_level=0 はデバッグ出力を抑制
        print(f"Connecting to LDAP server: {LDAP_SERVER_URL}")

        # 接続オプションの設定
        #l.set_option(ldap.OPT_REFERRALS, 0) # リフェラルを自動的に追わない
        #l.set_option(ldap.OPT_PROTOCOL_VERSION, 3) # LDAPv3を使用
        # TLS/SSL設定 (LDAPSの場合)
        # 本番環境では、サーバー証明書を適切に検証してください。
        # 自己署名証明書やプライベートCAの場合は、ca_certs, certfile, keyfileなどのオプション設定が必要な場合があります。
        l.set_option(ldap.OPT_X_TLS_CACERTFILE, "/etc/ssl/certs/Sony_Root_CA2.cer") # CA証明書ファイルのパスを指定
        #l.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_DEMAND, "/etc/ssl/certs/Sony_Intranet_CA2.cer") # 証明書を要求し検証する
        #l.set_option(ldap.OPT_X_TLS_NEWCTX, 0) # 新しいTLSコンテキストを作成 (既存のコンテキストを再利用しない)

        # SASL GSSAPI (Kerberos) 認証
        # SASL bind はユーザー名とパスワードなしで、実行ユーザーのKerberosチケットを使用します。
        # 環境変数 KRB5CCNAME でチケットキャッシュの場所を指定する必要がある場合があります。
        # Windowsの場合は、実行ユーザーがドメインユーザーである必要があります。
        auth_tokens = ldap.sasl.sasl({}, 'GSSAPI') # GSSAPI認証を使用
        print("auth_tokens:", auth_tokens) # デバッグ用に認証トークンを表示
        l.sasl_interactive_bind_s("", auth_tokens)
        print(f"LDAP SASL/GSSAPI Bind successful to {LDAP_SERVER_URL}")

        # 検索オプション
        search_filter = "(objectClass=*)" # baseスコープなのでフィルタは実質不要だが形式的に指定
        search_attributes = [ # VBAコードで参照・コメントアウトされていた属性
            'mail',
            'sn',         # 姓
            'givenName',  # 名
            'displayName',
            'telephoneNumber',
            'physicalDeliveryOfficeName',
            'department',
            'streetAddress',
            'l',          # 市区町村
            'st',         # 都道府県
            'company'
        ]
        search_scope = ldap.SCOPE_BASE # 指定されたDNのオブジェクトのみを検索

        # 検索実行
        # search_s は同期検索
        result_id = l.search(user_dn, search_scope, search_filter, search_attributes)
        # search_s の結果はリストのリスト [(dn, entry), ...]
        results = l.result(result_id, 0)[1] # result() の戻り値は (type, [(dn, entry), ...])

        if not results:
            print(f"User not found with DN: {user_dn}")
            return {"success": False, "error": f"User not found with GID: {gid}"}

        # 最初の検索結果を取得 (baseスコープなので通常は1つ)
        dn, entry = results[0]
        print(f"Found user: {dn}")

        # 属性値をデコードして取得
        user_info = {
            "success": True,
            "ldap_val": True, # 成功時はtrue
            "dn": dn,
            # 属性値はバイト文字列で返されるため、UTF-8などでデコードが必要
            "mail": entry.get('mail', [b''])[0].decode('utf-8', errors='ignore'),
            "sn": entry.get('sn', [b''])[0].decode('utf-8', errors='ignore'),
            "givenName": entry.get('givenName', [b''])[0].decode('utf-8', errors='ignore'),
            "displayName": entry.get('displayName', [b''])[0].decode('utf-8', errors='ignore'),
            "telephoneNumber": entry.get('telephoneNumber', [b''])[0].decode('utf-8', errors='ignore'),
            "physicalDeliveryOfficeName": entry.get('physicalDeliveryOfficeName', [b''])[0].decode('utf-8', errors='ignore'),
            "department": entry.get('department', [b''])[0].decode('utf-8', errors='ignore'),
            "streetAddress": entry.get('streetAddress', [b''])[0].decode('utf-8', errors='ignore'),
            "l": entry.get('l', [b''])[0].decode('utf-8', errors='ignore'), # 市区町村
            "st": entry.get('st', [b''])[0].decode('utf-8', errors='ignore'), # 都道府県
            "company": entry.get('company', [b''])[0].decode('utf-8', errors='ignore'),
            # 他の属性も必要に応じて追加
            "raw_entry": entry # デバッグ用に生の属性も保持
        }
        return user_info

    except ldap.LDAPError as e:
        error_message = f"LDAP operation failed: {e}"
        print(f"[LDAP Error] {error_message}")
        # SASL GSSAPI関連のエラーメッセージをより詳細にする
        if isinstance(e, ldap.SERVER_DOWN):
             error_message += " (Server is down or unreachable)"
        elif isinstance(e, ldap.LOCAL_ERROR) and "sasl" in str(e).lower():
             error_message += " (SASL/GSSAPI error. Check Kerberos ticket and configuration.)"
        elif isinstance(e, ldap.PROTOCOL_ERROR):
             error_message += " (LDAP protocol error)"
        # その他のLDAPエラーコードに応じたメッセージを追加可能

        return {"success": False, "ldap_val": False, "error": error_message}
    except Exception as e:
        # その他の予期せぬエラー
        error_message = f"An unexpected error occurred: {e}"
        print(f"[Unexpected Error] {error_message}")
        return {"success": False, "ldap_val": False, "error": error_message}
    finally:
        # 接続を閉じる
        if l is not None:
            try:
                l.unbind_s()
                print("LDAP Unbind successful.")
            except ldap.LDAPError as e:
                print(f"[LDAP Unbind Error] {e}")

# --- APIエンドポイント: LDAPユーザー情報取得 ---
@app.route('/api/ldap_user/<gid>', methods=['GET'])
def api_get_ldap_user(gid):
    """
    指定されたGIDのLDAPユーザー情報を取得するAPIエンドポイント。
    """
    if not gid:
        return jsonify({"success": False, "error": "GID is required"}), 400

    print(f"Received request for LDAP user with GID: {gid}")
    user_info = get_ldap_user_info_python(gid)

    if user_info.get("success"):
        return jsonify(user_info), 200
    else:
        # LDAP検索関数からのエラー情報をそのまま返す
        return jsonify(user_info), 500 # LDAPエラーはサーバーサイドのエラーとして扱う

# ルートURLへのアクセス処理 - メインメニューを表示
@app.route('/')
def index():
    return render_template('main_menu.html')

@app.route('/scan_IDcard.html')
def scan_idcard():
    return render_template('scan_IDcard.html')

@app.route('/read_IDcard.html')
def read_idcard():
    return render_template('read_IDcard.html')

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

#@app.route('/api/return_book', methods=['POST'])
#def api_return_book():
#    data = request.get_json()
#    employee_id = data.get('employee_id')
#    isbn = data.get('isbn')

#    if not employee_id or not isbn:
###        return jsonify({"error": "社員IDとISBNは必須です"}), 400

#    db = get_db()

    # TODO: 返却処理のロジックを実装する
    # 1. 社員IDとISBNを元に、貸出情報を検索する
    # 2. 貸出情報が存在する場合、返却処理を行う
    # 3. 貸出情報が存在しない場合、エラーを返す

    # ダミーの返却処理
#    return jsonify({"success": True, "message": f"社員ID: {employee_id}, ISBN: {isbn} の書籍を返却しました (実際には処理は行われていません)"})

if __name__ == '__main__':
    # init_db() # init_dbは起動時に一度だけ実行されれば良い
    app.run(debug=True) # デバッグモードで起動