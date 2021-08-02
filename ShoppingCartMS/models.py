from app import db
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema


class ShoppingCart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    reservation_id = db.Column(db.Integer, nullable=False)


class ShoppingCartSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ShoppingCart
        load_instance = True
