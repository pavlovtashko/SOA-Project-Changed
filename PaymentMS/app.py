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
PAYMENT_APIKEY = 'PAYMENT MS SECRET'

# Adding MS to consul

consul_port = 8500
service_name = "payment"
service_port = 5001


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
def get_total_money(request_body):
    if request_body['date_from'] > request_body['date_to']:
        return {'error': 'Date from is after day from!'}, 404

    date_from_year, date_from_month, date_from_day = request_body['date_from'].split('-')
    date_to_year, date_to_month, date_to_day = request_body['date_to'].split('-')
    day_diff = (date(year=int(date_to_year), month=int(date_to_month), day=int(date_to_day)) - date(year=int(date_from_year), month=int(date_from_month), day=int(date_from_day))).days
    total_price = int(request_body['price_per_day']) * day_diff * int(request_body['copies'])

    return {'Total Price': f'{total_price}'}, 200


@has_role(["shopping_cart"])
def make_payment(payment_body):
    payment = Payment(username=payment_body['username'], total_money=payment_body['money'], user_email=payment_body['email'])

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
#register_to_consul()
if __name__ == "__main__":
    connexion_app.run(host='0.0.0.0', port=5001, debug=True)
