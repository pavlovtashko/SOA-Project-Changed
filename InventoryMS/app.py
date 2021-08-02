from functools import wraps
import connexion
from flask import request, abort
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import jwt

JWT_SECRET = 'MY JWT SECRET'
JWT_LIFETIME_SECONDS = 600000


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


@has_role(["admin"])
def create_book(book_body):
    found_book = db.session.query(Book).filter_by(title=book_body['title']).first()
    if found_book:
        return {'error': 'Book with title {} already exists!'.format(book_body['title'])}, 404
    author = book_body['author']
    title = book_body['title']
    no_pages = book_body['no_pages']
    year = book_body['year']
    copies = book_body['copies']
    available = book_body['available']
    price_per_day = book_body['price_per_day']
    new_book = Book(author=author, title=title, no_pages=no_pages, year=year, copies=copies, available=available,
                    price_per_day=price_per_day)
    db.session.add(new_book)
    db.session.commit()

    return book_schema.dump(new_book)


@has_role(["shopping_cart"])
def get_book(request_body):
    found_book = db.session.query(Book).filter_by(title=request_body['book_title']).first()
    if found_book:
        return book_schema.dump(found_book)
    else:
        return {'error': 'Book with title: {} was not found!'.format(request_body['book_title'])}, 404


def update_book(book_id, book_body):
    found_book = db.session.query(Book).get(book_id)
    if not found_book:
        return {'error': 'Book with id: {} was not found!'.format(book_id)}, 404
    found_book.title = book_body['title']
    found_book.author = book_body['author']
    found_book.no_pages = book_body['no_pages']
    found_book.year = book_body['year']
    found_book.copies = book_body['copies']
    found_book.available = book_body['available']
    found_book.price_per_day = book_body['price_per_day']

    db.session.commit()
    found_book = db.session.query(Book).get(book_id)
    return book_schema.dump(found_book)


def get_all_books():
    books = db.session.query(Book).all()
    return book_schema.dump(books, many=True)


@has_role(["shopping_cart"])
def reserve_book(book_id, book_copies):
    book = db.session.query(Book).get(book_id)
    if book.available:
        if book.copies - book_copies['no_copies'] >= 0:
            book.copies -= book_copies['no_copies']
            if book.copies == 0:
                book.available = False
            db.session.commit()
            return {'success': 'Book is successfully Reserved!'}, 200
        else:
            return {'error': 'Not available copies!'}, 404
    else:
        return {'error': 'Book is currently not available'}, 404


def return_book(book_id, book_copies):
    book = db.session.query(Book).get(book_id)
    if book:
        book.copies += book_copies['no_copies']
        if not book.available:
            book.available = True
        db.session.commit()
        return {'Success': 'Successfully returned book'}, 200
    else:
        return {'Error': 'The book with id: {} does not exist'.format(book_id)}, 404


connexion_app = connexion.App(__name__, specification_dir="./")
app = connexion_app.app
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)
connexion_app.add_api("api.yml")
from models import Book, BookSchema

book_schema = BookSchema()

if __name__ == "__main__":
    connexion_app.run(host='0.0.0.0', port=5000, debug=True)
