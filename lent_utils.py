from flask import jsonify, request
from datetime import datetime
from models import db, t05_lent_records, t06_return_records, t04_locations

def api_register_lent_record():
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
        traceback.print_exc()
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

def api_check_lent_status():
    inst_id = request.args.get('instid')
    row = t05_lent_records.query.filter_by(inst_id=inst_id).first()
    return jsonify({'exists': bool(row)})

