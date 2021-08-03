from functools import wraps
import connexion
from flask import request, abort
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import jwt
import requests
from datetime import date
import json
from consul import Consul, Check

JWT_SECRET = 'MY JWT SECRET'
JWT_LIFETIME_SECONDS = 600000

# Adding MS to consul

consul_port = 8500
service_name = "reserve"
service_port = 5005


def register_to_consul():
    consul = Consul(host='consul', port=consul_port)

    agent = consul.agent

    service = agent.service

    check = Check.http(f"http://{service_name}:{service_port}/api/ui", interval="10s", timeout="5s", deregister="1s")

    service.register(service_name, service_id=service_name, port=service_port, check=check)


def get_service(service_id):
    consul = Consul(host="consul", port=consul_port)

    agent = consul.agent

    service_list = agent.services()

    service_info = service_list[service_id]


def has_role(arg):
    def has_role_inner(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            try:
                headers = request.headers
                if headers.environ['HTTP_AUTHORIZATION']:
                    token = headers.environ['HTTP_AUTHORIZATION'].split(' ')[1]
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


@has_role(["shopping_cart"])
def make_reservation(reservation_body):
    result = db.session.query(Reservation).filter_by(user_id=reservation_body['user_id']).all()
    if result:
        active_reservations = 0
        for i in result:
            if i.active:
                active_reservations += 1
            if i.book_id == reservation_body['book_id'] and i.active:
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


@has_role(['shopping_cart'])
def return_book(return_body):
    # user_id, book_id
    reservations = db.session.query(Reservation).filter_by(user_id=return_body['user_id']).all()
    for res in reservations:
        if res.book_id == return_body['book_id'] and res.active:
            res.active = False
            db.session.commit()
            return {'success': 'Successfully returned book!',
                    'book_copies': res.no_copies}, 200
    return {'error': 'Something went wrong!'}, 404


def get_all_reservations():
    reservations = db.session.query(Reservation).all()
    return payment_schema.dump(reservations, many=True)


@has_role(['shopping_cart'])
def get_reservation_details(user_id):
    res = db.session.query(Reservation).filter_by(user_id=user_id).all()
    if res:
        return payment_schema.dump(res, many=True)
    else:
        return {'error': 'No reservation with uses_id {}'.format(user_id)}, 404


connexion_app = connexion.App(__name__, specification_dir="./")
app = connexion_app.app
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)
connexion_app.add_api("api.yml")

from models import Reservation, ReservationSchema
payment_schema = ReservationSchema()
#register_to_consul()

if __name__ == "__main__":
    connexion_app.run(host='0.0.0.0', port=5005, debug=True)
