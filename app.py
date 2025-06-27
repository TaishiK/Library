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
import logging 
logging.getLogger('salalchemy.engine').setLevel(logging.WARNING)  # SQLAlchemyのログレベルをINFO or WARNINGに設定
from models import db, t01_isbns, t00_instance_ids, t04_locations, t05_lent_records, t06_return_records
from ldap_utils import get_ldap_user_info_python
from book_utils import api_fetch_book_info, api_register_book, register_isbn_data, register_instance_data
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

@app.route('/control_menu')
def control_menu():
    return render_template('control_menu.html')

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
        func.coalesce(t01_isbns.category_number, 'N/A').label('category_number')
    ).outerjoin(t01_isbns, t00_instance_ids.isbn == t01_isbns.isbn)
    books = books.order_by(t00_instance_ids.instance_id.desc()).all()
    return render_template('book_registration.html', books=books)

# --- NDL検索・書籍登録・インスタンス登録API ---
@app.route('/api/fetch_book_info', methods=['POST'])
def fetch_book_info_route():
    return api_fetch_book_info()

@app.route('/api/register_book', methods=['POST'])
def register_book_route():
    return api_register_book()

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

if __name__ == '__main__':
    #init_db() # init_dbは起動時に一度だけ実行されれば良い
    app.run(debug=True) # デバッグモードで起動