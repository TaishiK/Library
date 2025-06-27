import os
import xml.etree.ElementTree as ET
import requests
from flask import jsonify, request, current_app as app
from datetime import datetime
from sqlalchemy import func
from models import db, t01_isbns, t00_instance_ids, t04_locations

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
    headers = {'User-Agent': 'MyLibraryApp/1.0'}
    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        xml_text = response.text
        root = ET.fromstring(xml_text)
        namespaces = {
            'sru': 'http://www.loc.gov/zing/srw/',
            'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
            'dcndl': 'http://ndl.go.jp/dcndl/terms/',
            'dc': 'http://purl.org/dc/elements/1.1/',
            'dcterms': 'http://purl.org/dc/terms/',
            'foaf': 'http://xmlns.com/foaf/0.1/'
        }
        record_data = root.find('.//sru:recordData', namespaces)
        if record_data is None:
            return None
        bib_resource = record_data.find('.//dcndl:BibResource', namespaces)
        if bib_resource is None:
            return None
        def get_text(element, path):
            node = element.find(path, namespaces)
            if node is not None:
                # dc:title/rdf:Description/rdf:value のような多段構造
                value_node = node.find('./rdf:Description/rdf:value', namespaces)
                if value_node is not None and value_node.text:
                    return value_node.text.strip()
                # dcterms:publisher/foaf:Agent/foaf:name のような多段構造
                name_node = node.find('./foaf:Agent/foaf:name', namespaces)
                if name_node is not None and name_node.text:
                    return name_node.text.strip()
                # それ以外は直接テキスト
                if node.text:
                    return node.text.strip()
            return ""
        title = get_text(bib_resource, './dc:title/rdf:Description/rdf:value')
        if not title:
            title = get_text(bib_resource, './dc:title')
        author = get_text(bib_resource, './dcndl:creator') or get_text(bib_resource, './dc:creator')
        publisher = get_text(bib_resource, './dcterms:publisher/foaf:Agent/foaf:name')
        issued = get_text(bib_resource, './dcterms:issued')
        issue_year = issued [:4] if issued and issued.isdigit() and len(issued) >= 4 else ""
        if not issue_year and '-' in issued:
            parts = issued.split('-')
            if len(parts[0]) == 4 and parts[0].isdigit():
                issue_year = parts[0]
        price_text = get_text(bib_resource, './dcndl:price')
        price_match = ''.join(filter(str.isdigit, price_text))
        price = int(price_match) if price_match else 0
        category = ""
        subjects = bib_resource.findall('./dcterms:subject', namespaces)
        for subject in subjects:
            resource_attr = subject.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource')
            if resource_attr and ('/ndc10/' in resource_attr or '/ndc9/' in resource_attr):
                ndc_code = resource_attr.split('/')[-1]
                if ndc_code and ndc_code[0].isdigit():
                    category = ndc_code[0]
                    break
        thumbnail_url = f"https://ndlsearch.ndl.go.jp/thumbnail/{isbn}.jpg"
        thumbnail_exists = False
        thumbnail_save_path = None
        try:
            thumb_response = requests.head(thumbnail_url, timeout=5)
            if thumb_response.status_code == 200 and 'image' in thumb_response.headers.get('Content-Type', ''):
                thumbnail_exists = True
                try:
                    thumbnails_dir = os.path.join(app.root_path, 'static', 'thumbnails')
                    os.makedirs(thumbnails_dir, exist_ok=True)
                    thumbnail_filename = f"{isbn}.jpg"
                    thumbnail_save_path = os.path.join(thumbnails_dir, thumbnail_filename)
                    if not os.path.exists(thumbnail_save_path):
                        img_response = requests.get(thumbnail_url, stream=True, timeout=10)
                        img_response.raise_for_status()
                        with open(thumbnail_save_path, 'wb') as f:
                            for chunk in img_response.iter_content(1024):
                                f.write(chunk)
                except Exception:
                    thumbnail_save_path = None
        except Exception:
            pass
        return {
            "title": title,
            "author": author,
            "publisher": publisher,
            "issueyear": issue_year,
            "price": price,
            "category": category,
            "thumbnail_url": thumbnail_url,
            "thumbnail_exists": thumbnail_exists,
            "hit_ndl": True
        }
    except Exception as e:
        print(f"NDL API error: {e}")
        return None

def register_isbn_data(isbn, title, author, publisher, issueyear, price, category, thumbnail_exists):
    try:
        # 型変換・必須値チェック
        if price in (None, ""): price = 0
        try:
            price = float(price)
        except Exception:
            price = 0
        thumbnail_val = bool(thumbnail_exists)
        # サムネイル画像が必要ならサーバー保存を保証
        if thumbnail_val:
            thumbnails_dir = os.path.join(app.root_path, 'static', 'thumbnails')
            os.makedirs(thumbnails_dir, exist_ok=True)
            thumbnail_filename = f"{isbn}.jpg"
            thumbnail_save_path = os.path.join(thumbnails_dir, thumbnail_filename)
            if not os.path.exists(thumbnail_save_path):
                thumbnail_url = f"https://ndlsearch.ndl.go.jp/thumbnail/{isbn}.jpg"
                try:
                    img_response = requests.get(thumbnail_url, stream=True, timeout=10)
                    img_response.raise_for_status()
                    with open(thumbnail_save_path, 'wb') as f:
                        for chunk in img_response.iter_content(1024):
                            f.write(chunk)
                except Exception as e:
                    print(f"Error downloading thumbnail for {isbn}: {e}")
        obj = db.session.get(t01_isbns, isbn)
        if obj:
            obj.title = title
            obj.author = author
            obj.publisher = publisher
            obj.issue_year = issueyear
            obj.price = price
            obj.category_number = category
            obj.thumbnail = thumbnail_val
        else:
            obj = t01_isbns(
                isbn=isbn,
                title=title,
                author=author,
                publisher=publisher,
                issue_year=issueyear,
                price=price,
                category_number=category,
                thumbnail=thumbnail_val
            )
            db.session.add(obj)
        db.session.commit()
        return True, None
    except Exception as e:
        db.session.rollback()
        print(f"Error registering/updating isbn {isbn}: {e}")
        return False, str(e)

def register_instance_data(isbn, hit_ndl):
    import socket
    pc_name = socket.gethostname()
    row = t04_locations.query.filter_by(pc_name=pc_name).first()
    locate_init = row.location if row else '登録待機場所'
    locate_now = locate_init
    try:
        hit_ndl_val = bool(hit_ndl)  # ←ここを修正
        obj = t00_instance_ids(
            instance_id=datetime.now().strftime('%y%m%d_%H%M%S'),
            isbn=isbn,
            hit_ndl_search=hit_ndl_val,
            locate_now=locate_now,
            locate_init=locate_init
        )
        db.session.add(obj)
        db.session.commit()
        return obj.instance_id, None
    except Exception as e:
        db.session.rollback()
        print(f"Error registering instanceid for isbn {isbn}: {e}")
        return None, str(e)

def api_fetch_book_info():
    data = request.get_json()
    isbn = data.get('isbn')
    if not isbn:
        return jsonify({"error": "isbn is required"}), 400
    isbn_cleaned = isbn.replace('-', '')
    book_info = fetch_from_ndl(isbn_cleaned)
    if book_info:
        return jsonify(book_info)
    else:
        return jsonify({
            "title": "",
            "author": "",
            "publisher": "",
            "issueyear": "",
            "price": 0,
            "category": "",
            "thumbnail_url": f"https://ndlsearch.ndl.go.jp/thumbnail/{isbn_cleaned}.jpg",
            "thumbnail_exists": False,
            "hit_ndl": False
        })

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
    # 型変換・必須値チェック
    if price in (None, ""): price = 0
    try:
        price = float(price)
    except Exception:
        price = 0
    isbn_success, isbn_err = register_isbn_data(isbn_cleaned, title, author, publisher, issue_year, price, category, thumbnail_exists)
    if not isbn_success:
        return jsonify({"error": "Failed to register isbn data", "detail": isbn_err}), 500
    instance_id, inst_err = register_instance_data(isbn_cleaned, hit_ndl)
    if instance_id:
        return jsonify({"success": True, "message": "Book registered successfully", "instance_id": instance_id})
    else:
        return jsonify({"error": "Failed to register book instance", "detail": inst_err}), 500
