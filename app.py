import os
import sys
import requests
import xml.etree.ElementTree as ET
from flask import Flask, g, render_template, request, jsonify
from datetime import datetime # instanceid生成用
import nfc
import binascii
import ldap # python-ldap ライブラリをインポート
import ldap.sasl # SASL認証のためにインポート
#from ldap3 import Server, Connection, ALL, SASL, GSSAPI # ldap3ライブラリを使用する場合
#import gssapi # GSSAPI認証のためにインポート
from ldap3 import Server, Connection, Tls, SASL, KERBEROS, ALL
import gssapi
import ssl
from dotenv import load_dotenv
import socket # ソケット通信のためにインポート
import platform # プラットフォーム情報取得のためにインポート
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, ForeignKey
from sqlalchemy.orm import relationship

#DATABASE = 'Libraries.db' # SQLite用のデータベースファイル名
DATABASE = 'libraries'  # Postgresql用のデータベース名
app = Flask(__name__, static_folder='static')

# SQLAlchemy設定
echo_setting = True  # SQL発行ログを有効化
def get_db_uri():
    return 'postgresql+psycopg2://kunori:taishi@localhost:5432/libraries'

app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = echo_setting

db = SQLAlchemy(app)

# --- モデル定義 ---
class t01_isbns(db.Model):
    __tablename__ = 't01_isbns'
    isbn = db.Column(db.String, primary_key=True)
    title = db.Column(db.String)
    author = db.Column(db.String)
    publisher = db.Column(db.String)
    issue_year = db.Column(db.String)
    price = db.Column(db.Numeric)
    category_number = db.Column(db.String)
    thumbnail = db.Column(db.Integer)
    # リレーション
    instances = relationship('t00_instance_ids', back_populates='isbn_ref')

class t00_instance_ids(db.Model):
    __tablename__ = 't00_instance_ids'
    instance_id = db.Column(db.String, primary_key=True)
    isbn = db.Column(db.String, db.ForeignKey('t01_isbns.isbn'), nullable=False)
    hit_ndl_search = db.Column(db.Integer)
    locate_now = db.Column(db.String)
    locate_init = db.Column(db.String)
    count_lent = db.Column(db.Integer, default=0)
    # リレーション
    isbn_ref = relationship('t01_isbns', back_populates='instances')

class t04_locations(db.Model):
    __tablename__ = 't04_locations'
    location = db.Column(db.String, primary_key=True)
    pc_name = db.Column(db.String)
    library_name = db.Column(db.String)
    admin_mail = db.Column(db.String)
    close_time = db.Column(db.String)
    default_term = db.Column(db.Integer)
    category_table = db.Column(db.String)
    member_only = db.Column(db.Integer)
    department = db.Column(db.String)
    monitor_type = db.Column(db.String)
    remind_mail = db.Column(db.Integer)
    mail_by_automate = db.Column(db.Integer)

class t05_lent_records(db.Model):
    __tablename__ = 't05_lent_records'
    lent_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    inst_id = db.Column(db.String)
    location = db.Column(db.String)
    gid = db.Column(db.String)
    date_lent = db.Column(db.String)
    date_return_expected = db.Column(db.String)
    email = db.Column(db.String)
    return_request = db.Column(db.Integer)

class t06_return_records(db.Model):
    __tablename__ = 't06_return_records'
    return_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    lent_id = db.Column(db.Integer, db.ForeignKey('t05_lent_records.lent_id'))
    inst_id = db.Column(db.String)
    location = db.Column(db.String)
    gid = db.Column(db.String)
    date_lent = db.Column(db.String)
    date_return = db.Column(db.String)
    reference = db.Column(db.String)

# --- DB初期化関数 ---
def init_db():
    with app.app_context():
        db.create_all()

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
        load_dotenv('.env')
        bind_dn = f"cn={os.getenv('UserName')},ou=Users,ou=JPUsers,dc=jp,dc=sony,dc=com"
        #print('UserName = ', os.getenv('UserName'))
        #print('pwd = ', os.getenv('PASSWORD'))
        # LDAPサーバーの情報を設定（ポート636を指定）
        server = Server(server_address, port=636, use_ssl=True, tls=tls_configuration, get_info=ALL)
        #server = Server(server_address, port=636, use_ssl=True, get_info=ALL)
        # Kerberos認証を使用して接続
        #conn = Connection(server, authentication=SASL, sasl_mechanism=KERBEROS, sasl_credentials=None, auto_bind=True)
        #環境変数を利用して接続
        conn = Connection(server, user=bind_dn, password=os.getenv('PASSWORD'), auto_bind=True)
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

@app.route('/exec_return.html')
def exec_return():
    return render_template('exec_return.html')

@app.route('/control_menu')
def control_menu():
    return render_template('control_menu.html')

@app.route('/book_registration')
def book_registration():
    # SQLAlchemyで一覧取得
    books = db.session.query(
        t00_instance_ids.instance_id,
        t00_instance_ids.isbn,
        func.coalesce(t01_isbns.title, 'N/A').label('title'),
        func.coalesce(t01_isbns.author, 'N/A').label('author'),
        func.coalesce(t01_isbns.publisher, 'N/A').label('publisher'),
        func.coalesce(t01_isbns.issue_year, 'N/A').label('issue_year'),
        func.coalesce(t01_isbns.price, 0).label('Price'),  # 数値型は0でcoalesce
        func.coalesce(t01_isbns.category_number, 'N/A').label('category_number')
    ).outerjoin(t01_isbns, t00_instance_ids.isbn == t01_isbns.isbn)
    books = books.order_by(t00_instance_ids.instance_id.desc()).all()
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

                     # 保存ファイル名 (isbn.jpg) - isbn 変数はハイフン除去済み
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
            "issueyear": issue_year,
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
        return jsonify({"error": "isbn is required"}), 400

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
            "issueyear": "",
            "price": 0,
            "category": "",
            "thumbnail_url": f"https://ndlsearch.ndl.go.jp/thumbnail/{isbn_cleaned}.jpg",
            "thumbnail_exists": False,
            "hit_ndl": False # APIから取得失敗
        })

# --- isbn登録/更新 ---
def register_isbn_data(isbn, title, author, publisher, issueyear, price, category, thumbnail_exists):
    try:
        obj = db.session.get(t01_isbns, isbn)
        if obj:
            obj.title = title
            obj.author = author
            obj.publisher = publisher
            obj.issue_year = issueyear
            obj.price = price
            obj.category_number = category
            obj.Thumbnail = 1 if thumbnail_exists else 0
        else:
            obj = t01_isbns(
                isbn=isbn,
                title=title,
                author=author,
                publisher=publisher,
                issue_year=issueyear,
                price=price,
                category_number=category,
                Thumbnail=1 if thumbnail_exists else 0
            )
            db.session.add(obj)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error registering/updating isbn {isbn}: {e}")
        return False

# --- instanceid登録 ---
def register_instance_data(isbn, hit_ndl):
    instance_id = datetime.now().strftime('%y%m%d_%H%M%S')
    locate_init = '登録待機場所'
    locate_now = locate_init
    try:
        obj = t00_instance_ids(
            instance_id=instance_id,
            isbn=isbn,
            hit_ndl_search=1 if hit_ndl else 0,
            locate_now=locate_now,
            locate_init=locate_init
        )
        db.session.add(obj)
        db.session.commit()
        return instance_id
    except Exception as e:
        db.session.rollback()
        print(f"Error registering instanceid for isbn {isbn}: {e}")
        return None

# APIエンドポイント: 書籍登録
@app.route('/api/register_book', methods=['POST'])
def api_register_book():
    data = request.get_json()
    isbn = data.get('isbn')
    title = data.get('title')
    author = data.get('author')
    publisher = data.get('publisher')
    issue_year = data.get('issueyear')
    price = data.get('price')
    category = data.get('category')
    hit_ndl = data.get('hit_ndl', False)
    thumbnail_exists = data.get('thumbnail_exists', False)
    if not isbn:
        return jsonify({"error": "isbn is required"}), 400
    isbn_cleaned = isbn.replace('-', '')
    isbn_success = register_isbn_data(isbn_cleaned, title, author, publisher, issue_year, price, category, thumbnail_exists)
    if not isbn_success:
        return jsonify({"error": "Failed to register isbn data"}), 500
    instance_id = register_instance_data(isbn_cleaned, hit_ndl)
    if instance_id:
        return jsonify({"success": True, "message": "Book registered successfully", "instance_id": instance_id})
    else:
        return jsonify({"error": "Failed to register book instance"}), 500

# --- 返却処理API ---
@app.route('/api/return_book', methods=['POST'])
def api_return_book():
    data = request.get_json()
    inst_id = data.get('inst_id')
    if not inst_id:
        return jsonify({'success': False, 'error': 'inst_id is required'})
    lent_row = t05_lent_records.query.filter_by(inst_id=inst_id).first()
    if not lent_row:
        return jsonify({'success': False, 'error': '貸出レコードが見つかりません'})
    lent_info = {
        'LentID': lent_row.lent_id,
        'location': lent_row.location,
        'GID': lent_row.gid,
        'DateLent': lent_row.date_lent
    }
    print(f"Returning book with inst_id: {inst_id}, LentID: {lent_info['LentID']}, Location: {lent_info['location']}, GID: {lent_info['GID']}, DateLent: {lent_info['DateLent']}")
    try:
        db.session.delete(lent_row)
        now = datetime.now().strftime('%Y%m%d %H%M%S')
        ret = t06_return_records(
            lent_id=lent_row.lent_id,
            inst_id=inst_id,
            location=lent_row.location,
            gid=lent_row.gid,
            date_lent=lent_row.date_lent,
            date_return=now,
            reference=''
        )
        db.session.add(ret)
        db.session.commit()
        return jsonify({'success': True, 'lent_info': lent_info})
    except Exception as e:
        import traceback
        print('返却処理で例外発生:', str(e))
        traceback.print_exc()
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# --- インスタンス情報取得API ---
@app.route('/api/instance_info/<instid>', methods=['GET'])
def api_instance_info(instid):
    row = t00_instance_ids.query.filter_by(instance_id=instid).first()
    if not row:
        return jsonify({'success': False, 'error': '該当するインスタンスIDがありません。'})
    isbn = row.isbn
    book = t01_isbns.query.filter_by(isbn=isbn).first()
    if not book:
        return jsonify({'success': False, 'error': '該当するisbnの書籍情報がありません。'})
    thumbnail_path = os.path.join(app.root_path, 'static', 'thumbnails', f'{isbn}.jpg')
    thumbnail_exists = os.path.exists(thumbnail_path)
    thumbnail_url = f'/static/thumbnails/{isbn}.jpg' if thumbnail_exists else None
    return jsonify({
        'success': True,
        'instance_id': instid,
        'isbn': isbn,
        'title': book.title,    
        'author': book.author,
        'publisher': book.publisher,
        'issue_year': book.issue_year,
        'thumbnail_exists': thumbnail_exists,
        'thumbnail_url': thumbnail_url
    })

# --- PCシリアル取得API（ダミー: 環境変数やホスト名で代用）
@app.route('/api/get_pc_serial')
def get_pc_serial():
    import socket
    serial = os.environ.get('PC_SERIAL') or socket.gethostname()
    return jsonify({'serial': serial})

# --- 返却予定日計算API ---
@app.route('/api/get_return_expected')
def get_return_expected():
    serial = request.args.get('serial')
    row = t04_locations.query.filter_by(pc_name=serial).first()
    days = int(row.defaultterm) if row and row.defaultterm else 14
    from datetime import timedelta
    dt = datetime.now() + timedelta(days=days)
    date_return_expected = dt.strftime('%Y%m%d %H:%M:%S')
    return jsonify({'date_return_expected': date_return_expected})

# --- 貸出レコード登録API ---
@app.route('/api/register_lent_record', methods=['POST'])
def register_lent_record():
    data = request.get_json()
    inst_id = data.get('inst_id')
    location = data.get('location')
    gid = data.get('gid')
    date_lent = data.get('date_lent')
    date_return_expected = data.get('date_return_expected')
    email = data.get('email')
    return_request = data.get('return_request', 0)
    try:
        rec = t05_lent_records(
            inst_id=inst_id,
            location=location,
            gid=gid,
            date_lent=date_lent,
            date_return_expected=date_return_expected,
            email=email,
            return_request=return_request
        )
        db.session.add(rec)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# --- PCシリアルからlocation取得API ---
@app.route('/api/get_location_by_serial')
def get_location_by_serial():
    serial = socket.gethostname()
    row = t04_locations.query.filter_by(pc_name=serial).first()
    location = row.location if row else ''
    return jsonify({'location': location})

# --- 貸出状態チェックAPI ---
@app.route('/api/check_lent_status')
def api_check_lent_status():
    inst_id = request.args.get('instid')
    row = t05_lent_records.query.filter_by(inst_id=inst_id).first()
    return jsonify({'exists': bool(row)})

if __name__ == '__main__':
    #init_db() # init_dbは起動時に一度だけ実行されれば良い
    app.run(debug=True) # デバッグモードで起動