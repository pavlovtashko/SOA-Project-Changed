from functools import wraps
import connexion
from flask import request, abort
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import jwt
import requests
from datetime import date
import json

JWT_SECRET = 'MY JWT SECRET'
SHOPPING_CART_APIKEY = 'SHOPPING CART MS SECRET'

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


def reserve_book(reservation_body):
    # auth ms!
    body = {
        'apikey': SHOPPING_CART_APIKEY
    }
    jwt_token = requests.post(url='http://localhost:5002/api/auth_microservice', json=body)

    auth_value = "Bearer {}".format(jwt_token.json())
    AUTH_HEADER = {"AUTHORIZATION": auth_value}

    user_details = requests.get(url='http://localhost:5002/api//user/{}/details'.format(reservation_body['username']),
                                headers=AUTH_HEADER)
    book_details = requests.post(url='http://localhost:5000/api/book/details',
                                 headers=AUTH_HEADER,
                                 json={'book_title': reservation_body['book_title']})
    response = requests.post(url='http://localhost:5000/api/book/{}/reserve'.format(book_details.json()['id']),
                             headers=AUTH_HEADER,
                             json={'no_copies': reservation_body['no_copies']})

    # inventory_response = requests.get(url='http://localhost:5000/api/books', headers=AUTH_HEADER)
    #
    # inventory_response


connexion_app = connexion.App(__name__, specification_dir="./")
app = connexion_app.app
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)
connexion_app.add_api("api.yml")

from models import ShoppingCart, ShoppingCartSchema

payment_schema = ShoppingCartSchema()
if __name__ == "__main__":
    connexion_app.run(host='0.0.0.0', port=5004, debug=True)
