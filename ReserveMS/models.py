from app import db
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema


class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    book_id = db.Column(db.Integer, nullable=False)
    no_copies = db.Column(db.Integer, nullable=False)
    from_date = db.Column(db.Date, nullable=False)
    to_date = db.Column(db.Date, nullable=False)
    active = db.Column(db.Boolean, nullable=False)


class ReservationSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Reservation
        load_instance = True
