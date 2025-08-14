from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship

db = SQLAlchemy()

class t01_isbns(db.Model):
    __tablename__ = 't01_isbns'
    isbn = db.Column(db.String, primary_key=True)
    title = db.Column(db.String)
    author = db.Column(db.String)
    publisher = db.Column(db.String)
    issue_year = db.Column(db.String)
    price = db.Column(db.Numeric)
    category_id = db.Column(db.String)
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
    own_category_id = db.Column(db.Integer)
    # リレーション
    isbn_ref = relationship('t01_isbns', back_populates='instances')

class t02_users(db.Model):
    __tablename__ = 't02_users'
    gid = db.Column(db.String, primary_key=True)
    email = db.Column(db.String)

class t03_administrators(db.Model):
    __tablename__ = 't03_administrators'
    gid = db.Column(db.String, primary_key=True)
    location = db.Column(db.String)

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

class t07_categories_ndc(db.Model):
    __tablename__ = 't07_categories_ndc'
    category_id = db.Column(db.Integer, primary_key=True, autoincrement=False)
    category = db.Column(db.String)

class t07_categories_c(db.Model):
    __tablename__ = 't07_categories_c'
    category_id = db.Column(db.Integer, primary_key=True, autoincrement=False)
    category = db.Column(db.String)
    
class t07_categories_port_sc(db.Model):
    __tablename__ = 't07_categories_port_sc'
    category_id = db.Column(db.Integer, primary_key=True, autoincrement=False)
    category  = db.Column(db.String)
    
class t07_categories_port_scmm(db.Model):
    __tablename__ = 't07_categories_port_scmm'
    category_id = db.Column(db.Integer, primary_key=True, autoincrement=False)
    category = db.Column(db.String)
