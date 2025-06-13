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
from ldap3 import Server, Connection, Tls, SASL, KERBEROS, ALL
import gssapi
import ssl

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





#def get_ldap_user_info_python(gid):
def get_ldap_user_info_python(gid):
    # サーバーアドレスと証明書のパスを設定
    server_address = "LDAP.jp.sony.com"  # FQDNを使用
    root_ca_path = "/etc/ssl/certs/Sony_Root_CA2.cer"
    intermediate_ca_path = "/etc/ssl/certs/Sony_Intranet_CA2.cer"
    
    try:
        # TLS設定を構成
        tls_configuration = Tls(
            validate=ssl.CERT_REQUIRED,
            version=ssl.PROTOCOL_TLS,
            ca_certs_file=root_ca_path,
            ca_certs_path=intermediate_ca_path
        )
        bind_dn = f"cn={os.environ['UserName']},ou=Users,ou=JPUsers,dc=jp,dc=sony,dc=com"
        # LDAPサーバーの情報を設定（ポート636を指定）
        #server = Server(server_address, port=636, use_ssl=True, tls=tls_configuration, get_info=ALL)
        server = Server(server_address, port=3269, use_ssl=True, get_info=ALL)
        # Kerberos認証を使用して接続
        #conn = Connection(server, authentication=SASL, sasl_mechanism=KERBEROS, sasl_credentials=None, auto_bind=True)
        #環境変数を利用して接続
        conn = Connection(server, user=bind_dn, password=os.environ['PASSWORD'], auto_bind=True)
        #conn = Connection(server)　＃匿名で接続可能か確認、下の行も同様→　結果はNG 
        #conn = Connection(server, auto_bind='NONE', version=3, authentication='ANONYMOUS',client_strategy='SYNC', auto_referrals=True, read_only=False, lazy=False, raise_exceptions=False)
        # 接続確認
        if not conn.bind():
            print(f"LDAP接続に失敗しました: {conn.result}")
            return None
        
        print("LDAP接続に成功しました。")
        
        # 検索条件を設定
        search_base = "OU=Users,OU=JPUsers,DC=jp,DC=sony,DC=com"
        search_filter = f"(cn={gid})"
        attributes = ['mail', 'sn', 'givenName', 'department', 'company']
        
        # LDAP検索を実行
        if not conn.search(search_base, search_filter, attributes=attributes):
            print(f"LDAP検索に失敗しました: {conn.result}")
            return None
        
        # 結果を取得
        if conn.entries:
            user_info = conn.entries[0]
            print(f"ユーザー情報が見つかりました: {user_info}")                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            
            # 必要な属性を辞書形式で返す
            user_info = {
                "success": True,
                "ldap_val": True,  # 成功時はTrue
                #"dn": user_info.entry_dn,
                "mail": user_info.mail.value if 'mail' in user_info else None,
                #"sn": user_info.sn.value if 'sn' in user_info else None,
                #"givenName": user_info.givenName.value if 'givenName' in user_info else None,
                #"department": user_info.department.value if 'department' in user_info else None,
                #"company": user_info.company.value if 'company' in user_info else None,
                # 他の必要な属性も追加可能
            }
 
            return user_info
        else:
            print("指定したユーザーが見つかりませんでした。")
            return None

    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return None
# --- LDAPユーザー情報取得のAPIエンドポイント ---

# --- APIエンドポイント: LDAPユーザー情報取得 ---
@app.route('/api/ldap_user/<gid>', methods=['GET'])
def api_get_ldap_user(gid):
    
    #指定されたGIDのLDAPユーザー情報を取得するAPIエンドポイント。
    if not gid:
        return jsonify({"success": False, "error": "GID is required"}), 400

    print(f"Received request for LDAP user with GID: {gid}")
    user_info = get_ldap_user_info_python(gid)

    if user_info:
        #print(f"LDAP user found: {user_info}")
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

@app.route('/scan_QRcode.html')
def scan_qrcode():
    return render_template('scan_QRcode.html')

@app.route('/exec_borrow.html')
def exec_borrow():
    return render_template('exec_borrow.html')

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
                     thumbnails_dir = os.path.join(app.root_path, 'static', 'thumbnails')
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

# APIエンドポイント: インスタンス情報取得
@app.route('/api/instance_info/<instid>', methods=['GET'])
def api_instance_info(instid):
    db = get_db()
    # T00_InstanceIDsからISBN取得
    cur = db.execute('SELECT ISBN FROM T00_InstanceIDs WHERE InstanceID = ?', (instid,))
    row = cur.fetchone()
    if not row:
        return jsonify({'success': False, 'error': '該当するインスタンスIDがありません。'})
    isbn = row['ISBN']
    # T01_ISBNsから書籍情報取得
    cur2 = db.execute('SELECT Title, Author, Publisher, IssueYear FROM T01_ISBNs WHERE ISBN = ?', (isbn,))
    book = cur2.fetchone()
    if not book:
        return jsonify({'success': False, 'error': '該当するISBNの書籍情報がありません。'})
    # サムネイル存在チェック
    thumbnail_path = os.path.join(app.root_path, 'static', 'thumbnails', f'{isbn}.jpg')
    thumbnail_exists = os.path.exists(thumbnail_path)
    thumbnail_url = f'/static/thumbnails/{isbn}.jpg' if thumbnail_exists else None
    return jsonify({
        'success': True,
        'instance_id': instid,
        'isbn': isbn,
        'title': book['Title'],
        'author': book['Author'],
        'publisher': book['Publisher'],
        'issue_year': book['IssueYear'],
        'thumbnail_exists': thumbnail_exists,
        'thumbnail_url': thumbnail_url
    })

if __name__ == '__main__':
    # init_db() # init_dbは起動時に一度だけ実行されれば良い
    app.run(debug=True) # デバッグモードで起動