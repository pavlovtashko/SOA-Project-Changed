from functools import wraps
import connexion
from flask import request, abort
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import jwt
import requests
from datetime import date
import json

JWT_SECRET = 'RESERVATIONS MS SECRET'
JWT_LIFETIME_SECONDS = 600000


def has_role(arg):
    def has_role_inner(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            try:
                headers = request.headers
                if headers.environ['HTTP_AUTHORIZATION']:
                    token = headers.environ['HTTP_AUTHORIZATION']
                    decoded_token = decode_token(token)
                    if 'admin' in decoded_token['roles']:
                        return fn(*args, **kwargs)
                    for role in arg:
                        if role in decoded_token['roles']:
                            return fn(*args, **kwargs)
                    abort(401)
                return fn(*args, **kwargs)
            except Exception as e:
                abort(401)

        return decorated_view

    return has_role_inner


def decode_token(token):
    return jwt.decode(token, JWT_SECRET, algorithms=['HS256'])


def make_reservation(reservation_body):
    #user_id, book_id, no_copies, from_date, to_date
    result = db.session.query(Reservation).filter_by(user_id=reservation_body['user_id']).all()
    if result:
        active_reservations = 0
        for i in result:
            if i.active:
                active_reservations += 1
            if i.book_id == reservation_body['book_id']:
                return {'error': 'You can not reserve the same book again!'}, 404
        if active_reservations >= 3:
            return {'error': 'User can not have more than 3 reservations'}, 404
    user_id = reservation_body['user_id']
    book_id = reservation_body['book_id']
    no_copies = reservation_body['no_copies']
    date_from_year, date_from_month, date_from_day = reservation_body['from_date'].split('-')
    date_to_year, date_to_month, date_to_day = reservation_body['to_date'].split('-')
    to_date = date(year=int(date_to_year), month=int(date_to_month), day=int(date_to_day))
    from_date = date(year=int(date_from_year), month=int(date_from_month), day=int(date_from_day))
    new_reservation = Reservation(user_id=user_id, book_id=book_id, no_copies=no_copies, to_date=to_date, from_date=from_date, active=True)
    db.session.add(new_reservation)
    db.session.commit()
    return payment_schema.dump(new_reservation)


def return_book(return_body):
    # user_id, book_id
    reservations = db.session.query(Reservation).filter_by(user_id=return_body['user_id']).all()
    for res in reservations:
        if res.book_id == return_body['book_id']:
            res.active = False
            db.session.commit()
            return {'success': 'Successfully returned book!'}, 200
    return {'error': 'Something went wrong!'}, 404


def get_all_reservations():
    reservations = db.session.query(Reservation).all()
    return payment_schema.dump(reservations, many=True)


def get_reservation_details(reservation_id):
    res = db.session.query(Reservation).get(reservation_id)
    if res:
        return payment_schema.dump(res)
    else:
        return {'error': 'No reservation with id {}'.format(reservation_id)}, 404


connexion_app = connexion.App(__name__, specification_dir="./")
app = connexion_app.app
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)
connexion_app.add_api("api.yml")

from models import Reservation, ReservationSchema
payment_schema = ReservationSchema()
if __name__ == "__main__":
    connexion_app.run(host='0.0.0.0', port=5004, debug=True)