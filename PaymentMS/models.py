from app import db
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable=False)
    total_money = db.Column(db.String, nullable=False)
    user_email = db.Column(db.String, nullable=False)


class PaymentSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Payment
        load_instance = True
