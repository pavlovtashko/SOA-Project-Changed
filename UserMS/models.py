from app import db
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable=False)
    password = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)
    surname = db.Column(db.String, nullable=False)
    age = db.Column(db.Integer)
    address = db.Column(db.String, nullable=False)
    phone = db.Column(db.String)
    is_admin = db.Column(db.Boolean, nullable=False)


class UserSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True
