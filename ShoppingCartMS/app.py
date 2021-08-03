from functools import wraps
import connexion
from flask import request, abort
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import jwt
import requests
from consul import Consul, Check
from datetime import date
import json

JWT_SECRET = 'MY JWT SECRET'
SHOPPING_CART_APIKEY = 'SHOPPING CART MS SECRET'


# Adding MS to consul

consul_port = 8500
service_name = "sc"
service_port = 5004


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

    return service_info['Address'], service_info['Port']


def get_service_url(service_name):
    address, port = get_service(service_name)

    url = "{}:{}".format(address, port)

    if not url.startswith("http"):
        url = "http://{}".format(url)

    return url


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


def create_new_book(book_body):
    #auth user!
    body = {
        'username': book_body['username'],
        'password': book_body['password']
    }
    jwt_token = requests.post(url='http://localhost:5002/api/auth',
                              json=body)

    auth_value = "Bearer {}".format(jwt_token.json())
    AUTH_HEADER = {"AUTHORIZATION": auth_value}
    body = {
        'author': book_body['author'],
        'title': book_body['title'],
        'no_pages': book_body['no_pages'],
        'year': book_body['year'],
        'copies': book_body['copies'],
        'available': book_body['available'],
        'price_per_day': book_body['price_per_day']
    }
    response = requests.post(url='http://localhost:5000/api/book/add',
                             headers=AUTH_HEADER,
                             json=body)

    if response.status_code == 200:
        return {'success': 'Successfully added book!'}, 200
    else:
        return {'error': 'Something went wrong!'}, 404


def check_reservations(username):
    # auth ms!
    body = {
        'apikey': SHOPPING_CART_APIKEY
    }
    jwt_token = requests.post(url='http://localhost:5002/api/auth_microservice',
                              json=body)

    auth_value = "Bearer {}".format(jwt_token.json())
    AUTH_HEADER = {"AUTHORIZATION": auth_value}

    user_details = requests.get(url='http://localhost:5002/api/user/{}/details'.format(username),
                                headers=AUTH_HEADER)

    reservations = requests.get(url='http://localhost:5005/api/reservation/{}/details'.format(user_details.json()['id']),
                                headers=AUTH_HEADER)

    if reservations.status_code == 200:
        return reservations.json(), 200
    else:
        return {'error': 'Something went wrong'}, 404


def return_book(return_body):
    # auth ms!
    body = {
        'apikey': SHOPPING_CART_APIKEY
    }
    jwt_token = requests.post(url='http://localhost:5002/api/auth_microservice',
                              json=body)

    auth_value = "Bearer {}".format(jwt_token.json())
    AUTH_HEADER = {"AUTHORIZATION": auth_value}

    user_details = requests.get(url='http://localhost:5002/api/user/{}/details'.format(return_body['username']),
                                headers=AUTH_HEADER)

    if user_details.status_code != 200:
        return {'error': 'username does not exist!'}, 404

    book_details = requests.post(url='http://localhost:5000/api/book/details',
                                 headers=AUTH_HEADER,
                                 json={'book_title': return_body['book_title']})

    if book_details.status_code != 200:
        return {'error': 'Book with title {} does not exist!'.format(return_body['book_title'])}, 404

    response = requests.post(url='http://localhost:5005/api/return_book',
                             headers=AUTH_HEADER,
                             json={'user_id': int(user_details.json()['id']),
                                   'book_id': int(book_details.json()['id'])
                                   })
    if response.status_code != 200:
        return {'error': 'Something went wrong!'}, 404

    response = requests.post(url='http://localhost:5000/api/book/{}/return'.format(book_details.json()['id']),
                             headers=AUTH_HEADER,
                             json={'no_copies': response.json()['book_copies']})

    if response.status_code == 200:
        return {'success': 'Successfully returned book!'}, 200
    else:
        return {'error': 'Something went wrong'}, 404


def reserve_book(reservation_body):
    # auth ms!
    body = {
        'apikey': SHOPPING_CART_APIKEY
    }
    jwt_token = requests.post(url='http://localhost:5002/api/auth_microservice', json=body)

    auth_value = "Bearer {}".format(jwt_token.json())
    AUTH_HEADER = {"AUTHORIZATION": auth_value}

    user_details = requests.get(url='http://localhost:5002/api/user/{}/details'.format(reservation_body['username']),
                                headers=AUTH_HEADER)

    if user_details.status_code != 200:
        return {'error': 'username does not exist!'}, 404

    book_details = requests.post(url='http://localhost:5000/api/book/details',
                                 headers=AUTH_HEADER,
                                 json={'book_title': reservation_body['book_title']})

    if book_details.status_code != 200:
        return {'error': 'Book with title {} does not exist!'.format(reservation_body['book_title'])}, 404

    response = requests.post(url='http://localhost:5000/api/book/{}/reserve'.format(book_details.json()['id']),
                             headers=AUTH_HEADER,
                             json={'no_copies': reservation_body['no_copies']})

    body = {
        'user_id': user_details.json()['id'],
        'book_id': book_details.json()['id'],
        'no_copies': reservation_body['no_copies'],
        'from_date': reservation_body['from_date'],
        'to_date': reservation_body['to_date']
    }
    response = requests.post(url='http://localhost:5005/api/make_reservation',
                             headers=AUTH_HEADER,
                             json=body)
    shopping_cart_for_user = ShoppingCart(user_id=int(user_details.json()['id']),
                                          reservation_id=int(response.json()['id']))
    db.session.add(shopping_cart_for_user)
    db.session.commit()

    body = {
        'date_to': reservation_body['to_date'],
        'date_from': reservation_body['from_date'],
        'copies': reservation_body['no_copies'],
        'book_id': book_details.json()['id'],
        'price_per_day': int(book_details.json()['price_per_day'])
    }
    response_money = requests.post(url='http://localhost:5001/api/get_total_money/',
                             headers=AUTH_HEADER,
                             json=body)
    body = {
        'money': int(response_money.json()['Total Price']),
        'username': user_details.json()['username'],
        'email': user_details.json()['email']
    }

    response = requests.post(url='http://localhost:5001/api/make_payment/',
                             headers=AUTH_HEADER,
                             json=body)

    if response.status_code == 200:
        return {'description': 'Successfully created and paid reservation',
                'book_reserved': reservation_body['book_title'],
                'total_money': response_money.json()['Total Price'],
                'username': user_details.json()['username'],
                'age': user_details.json()['age'],
                'name': user_details.json()['name'],
                'surname': user_details.json()['surname']}, 200
    else:
        return {'error': 'something went wrong!'}, 404


connexion_app = connexion.App(__name__, specification_dir="./")
app = connexion_app.app
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)
connexion_app.add_api("api.yml")

from models import ShoppingCart, ShoppingCartSchema

payment_schema = ShoppingCartSchema()
# register_to_consul()
if __name__ == "__main__":
    connexion_app.run(host='0.0.0.0', port=5004, debug=True)
