from functools import wraps
import connexion
from flask import request, abort
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import jwt
import requests
from datetime import date
import json

JWT_SECRET = 'PAYMENT MS SECRET'
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


def get_total_money(request_body):
    id = request_body['book_id']
    book = requests.get(url=f'http://localhost:5000/api/book/{id}/details')

    if request_body['date_from'] > request_body['date_to']:
        return {'error': 'Date from is after day from!'}, 404

    date_from_year, date_from_month, date_from_day = request_body['date_from'].split('-')
    date_to_year, date_to_month, date_to_day = request_body['date_to'].split('-')
    day_diff = (date(year=int(date_to_year), month=int(date_to_month), day=int(date_to_day)) - date(year=int(date_from_year), month=int(date_from_month), day=int(date_from_day))).days
    total_price = int(book.text.split(',')[5].split(':')[1].split('.')[0]) * day_diff * int(request_body['copies'])

    return {'Total Price': f'{total_price}'}, 200


def make_payment(payment_body):
    user = requests.get(url='http://localhost:5002/api/user/{}/details'.format(payment_body['user_id']))
    user = json.loads(user.text)
    payment = Payment(username=user['username'], total_money=payment_body['money'], user_email=user['email'])
    db.session.add(payment)
    db.session.commit()
    return payment_schema.dump(payment)


connexion_app = connexion.App(__name__, specification_dir="./")
app = connexion_app.app
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)
connexion_app.add_api("api.yml")

from models import Payment, PaymentSchema
payment_schema = PaymentSchema()
if __name__ == "__main__":
    connexion_app.run(host='0.0.0.0', port=5001, debug=True)