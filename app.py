import os
import sys
import requests
import xml.etree.ElementTree as ET
from flask import Flask, g, render_template, request, jsonify
from datetime import datetime # instanceid生成用
#import nfc
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
import logging 
logging.getLogger('salalchemy.engine').setLevel(logging.WARNING)  # SQLAlchemyのログレベルをINFO or WARNINGに設定
from models import db, t01_isbns, t00_instance_ids, t02_users, t03_administrators, t04_locations, t05_lent_records, t06_return_records
from models import db, t07_categories_ndc, t07_categories_c, t07_categories_port_sc, t07_categories_port_scmm
from ldap_utils import get_ldap_user_info_python
from book_utils import api_fetch_book_info, api_register_book, register_isbn_data, register_instance_data
from book_utils import api_fetch_book_info_google
from lent_utils import api_register_lent_record, api_return_book, api_check_lent_status

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

db.init_app(app)

# --- DB初期化関数 ---
def init_db():
    with app.app_context():
        db.create_all()

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
    import socket
    pc_name = socket.gethostname()
    row = t04_locations.query.filter_by(pc_name=pc_name).first()
    library_name = row.library_name if row else '図書館'
    return render_template('main_menu.html', library_name=library_name)

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

@app.route('/control_menu.html')
def control_menu():
    return render_template('control_menu.html')

@app.route('/register_administrator.html')
def register_administrator():
    return render_template('register_administrator.html')

@app.route('/register_user.html')
def register_user():
    return render_template('register_user.html')

@app.route('/print_QRcode.html')
def print_qrcode_page():
    return render_template('print_QRcode.html')

@app.route('/book_registration')
def book_registration():
    # SQLAlchemyで一覧取得
    books = db.session.query(
        t00_instance_ids.instance_id.label('instance_id'),
        t00_instance_ids.isbn.label('isbn'),
        func.coalesce(t01_isbns.title, 'N/A').label('title'),
        func.coalesce(t01_isbns.author, 'N/A').label('author'),
        func.coalesce(t01_isbns.publisher, 'N/A').label('publisher'),
        func.coalesce(t01_isbns.issue_year, 'N/A').label('issue_year'),
        func.coalesce(t01_isbns.price, 0).label('price'),
        func.coalesce(t01_isbns.category_id, 'N/A').label('category_id')
    ).outerjoin(t01_isbns, t00_instance_ids.isbn == t01_isbns.isbn)
    books = books.order_by(t00_instance_ids.instance_id.desc()).all()
    return render_template('book_registration.html', books=books)

@app.route('/book_regist_by_google')
def book_regist_by_google():
    books = db.session.query(
        t00_instance_ids.instance_id.label('instance_id'),
        t00_instance_ids.isbn.label('isbn'),
        func.coalesce(t01_isbns.title, 'N/A').label('title'),
        func.coalesce(t01_isbns.author, 'N/A').label('author'),
        func.coalesce(t01_isbns.publisher, 'N/A').label('publisher'),
        func.coalesce(t01_isbns.issue_year, 'N/A').label('issue_year'),
        func.coalesce(t01_isbns.price, 0).label('price'),
        func.coalesce(t01_isbns.category_id, 'N/A').label('category_id')
    ).outerjoin(t01_isbns, t00_instance_ids.isbn == t01_isbns.isbn)
    books = books.order_by(t00_instance_ids.instance_id.desc()).all()
    return render_template('book_regist_by_google.html', books=books)

# --- NDL検索・書籍登録・インスタンス登録API ---
@app.route('/api/fetch_book_info', methods=['POST'])
def fetch_book_info_route():
    return api_fetch_book_info()

@app.route('/api/fetch_book_info_google', methods=['POST'])
def fetch_book_info_google_route():
    return api_fetch_book_info_google()

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
    location = data.get('location')
    own_category_id = data.get('own_category_id')  # 追加: 独自分類ID
    thumbnail_exists = data.get('thumbnail_exists', False)
    if not isbn:
        return jsonify({"error": "isbn is required"}), 400
    isbn_cleaned = isbn.replace('-', '')
    isbn_success = register_isbn_data(isbn_cleaned, title, author, publisher, issue_year, price, category, thumbnail_exists)
    if not isbn_success:
        return jsonify({"error": "Failed to register isbn data"}), 500
    instance_id = register_instance_data(isbn_cleaned, hit_ndl, location, own_category_id)
    if instance_id:
        return jsonify({"success": True, "message": "Book registered successfully", "instance_id": instance_id})
    else:
        return jsonify({"error": "Failed to register book instance"}), 500

# --- 返却処理API ---
@app.route('/api/return_book', methods=['POST'])
def return_book():
    return api_return_book()

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
    return api_register_lent_record()

# --- PCシリアルからlocation取得API ---
@app.route('/api/get_location_by_serial')
def get_location_by_serial():
    serial = socket.gethostname()
    row = t04_locations.query.filter_by(pc_name=serial).first()
    location = row.location if row else ''
    return jsonify({'location': location})

# --- 貸出状態チェックAPI ---
@app.route('/api/check_lent_status')
def check_lent_status():
    return api_check_lent_status()

# --- 管理者チェックAPI ---
@app.route('/api/check_administrator_exists/<gid>', methods=['GET'])
def check_administrator_exists(gid):
    from id_utils import api_check_administrator_exists
    return api_check_administrator_exists(gid)

# --- ユーザーチェックAPI ---
@app.route('/api/check_user_exists/<gid>', methods=['GET'])
def check_user_exists(gid):
    from id_utils import api_check_user_exists
    return api_check_user_exists(gid)
@app.route('/api/locations', methods=['GET'])
def api_get_locations():
    try:
        locations = t04_locations.query.all()
        location_list = [{"location": loc.location, "library_name": loc.library_name} for loc in locations]
        return jsonify({"success": True, "locations": location_list}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/register_user', methods=['POST'])
def api_register_user():
    data = request.get_json()
    gid = data.get('gid')
    email = data.get('email')

    if not gid or not email:
        return jsonify({"success": False, "error": "GID and email are required"}), 400

    try:
        user = t02_users.query.filter_by(gid=gid).first()
        if user:
            # 既存ユーザーのメールアドレスを更新
            user.email = email
            db.session.commit()
            return jsonify({"success": True, "message": "User email updated successfully"}), 200
        else:
            # 新規ユーザーを登録
            new_user = t02_users(gid=gid, email=email)
            db.session.add(new_user)
            db.session.commit()
            return jsonify({"success": True, "message": "User registered successfully"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/register_administrator', methods=['POST'])
def api_register_administrator():
    data = request.get_json()
    gid = data.get('gid')
    location = data.get('location')

    if not gid or not location:
        return jsonify({"success": False, "error": "GID and location are required"}), 400

    try:
        administrator = t03_administrators.query.filter_by(gid=gid).first()
        if administrator:
            # 既存管理者のlocationを更新
            administrator.location = location
            db.session.commit()
            return jsonify({"success": True, "message": "Administrator location updated successfully"}), 200
        else:
            # 新規管理者を登録
            new_administrator = t03_administrators(gid=gid, location=location)
            db.session.add(new_administrator)
            db.session.commit()
            return jsonify({"success": True, "message": "Administrator registered successfully"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
# --- locationからcategory_table取得API ---
@app.route('/api/location_category_table', methods=['GET'])
def get_location_category_table():
    location = request.args.get('location')
    if not location:
        return jsonify({"success": False, "error": "Location is required"}), 400

    try:
        row = t04_locations.query.filter_by(location=location).first()
        if not row:
            return jsonify({"success": False, "error": "Location not found"}), 404

        category_table = row.category_table
        return jsonify({"success": True, "category_table": category_table}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# --- カテゴリ情報取得API ---
@app.route('/api/categories', methods=['GET'])
def get_categories():
    table_name = request.args.get('table_name')
    if not table_name:
        return jsonify({"success": False, "error": "Table name is required"}), 400

    try:
        # テーブル名に基づいて適切なモデルを選択
        if table_name == 't07_categories_port_sc':
            model = t07_categories_port_sc
        elif table_name == 't07_categories_port_scmm':
            model = t07_categories_port_scmm
        elif table_name == 't07_categories_ndc':  # 追加: NDC
            model = t07_categories_ndc
        else:
            return jsonify({"success": False, "error": "Invalid table name"}), 400

        # データベースからカテゴリ情報を取得
        categories = model.query.all()
        category_list = [{"category_id": cat.category_id, "category": cat.category} for cat in categories]
        return jsonify({"success": True, "categories": category_list}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/instances_by_location')
def api_instances_by_location():
    location = request.args.get('location')
    if not location:
        return jsonify({'success': False, 'error': 'location is required'}), 400
    try:
        # instance_id DESC で取得（仕様上のSQLに合わせる）
        rows = db.session.query(
            t00_instance_ids.instance_id,
            t00_instance_ids.isbn,
            t01_isbns.title
        ).join(t01_isbns, t00_instance_ids.isbn == t01_isbns.isbn)
        rows = rows.filter(t00_instance_ids.locate_now == location).order_by(t00_instance_ids.instance_id.desc()).all()
        data = [
            {
                'instance_id': r.instance_id,
                'isbn': r.isbn,
                'title': r.title if r.title else ''
            } for r in rows
        ]
        return jsonify({'success': True, 'records': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/location_detail')
def api_location_detail():
    location = request.args.get('location')
    if not location:
        return jsonify({'success': False, 'error': 'location is required'}), 400
    try:
        row = t04_locations.query.filter_by(location=location).first()
        if not row:
            return jsonify({'success': False, 'error': 'not found'}), 404
        # logo列未定義対応: getattrで安全取得
        logo = getattr(row, 'logo', None)
        return jsonify({'success': True, 'location': row.location, 'library_name': row.library_name, 'logo': logo})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    #init_db() # init_dbは起動時に一度だけ実行されれば良い
    app.run(debug=True) # デバッグモードで起動