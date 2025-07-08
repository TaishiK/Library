from flask import jsonify, request
from models import db, t02_users, t03_administrators


def api_check_administrator_exists(gid):
    from models import t03_administrators
    row = t03_administrators.query.filter_by(gid=gid).first()
    if row:
        return jsonify({'exists': True})
    else:
        return jsonify({'exists': False, 'error': 'この社員番号は管理者に登録されていません。管理者登録してからご利用下さい。'})

def api_check_user_exists(gid):
    """
    Check if a user exists in the t02_users table.
    Returns a JSON response indicating whether the user exists.
    """
    row = t02_users.query.filter_by(gid=gid).first()
    if row:
        return jsonify({'exists': True})
    else:
        return jsonify({'exists': False, 'error': 'この社員番号はユーザーに登録されていません。ユーザー登録してからご利用下さい。'})