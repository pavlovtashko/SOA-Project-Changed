from app import db
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema


class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String, nullable=False)
    title = db.Column(db.String, nullable=False)
    no_pages = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    copies = db.Column(db.Integer, nullable=False)
    available = db.Column(db.Boolean, nullable=False)
    price_per_day = db.Column(db.Float, nullable=False)


class BookSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Book
        load_instance = True
