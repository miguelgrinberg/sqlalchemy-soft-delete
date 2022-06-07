import os
from flask import Flask, request, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy, BaseQuery
from flask_migrate import Migrate

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(
    basedir, 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)


class QueryWithSoftDelete(BaseQuery):
    _with_deleted = False

    def __new__(cls, *args, **kwargs):
        obj = super(QueryWithSoftDelete, cls).__new__(cls)
        obj._with_deleted = kwargs.pop('_with_deleted', False)
        if len(args) > 0:
            super(QueryWithSoftDelete, obj).__init__(*args, **kwargs)
            return obj.filter_by(deleted=False) if not obj._with_deleted else obj
        return obj

    def __init__(self, *args, **kwargs):
        pass

    def with_deleted(self):
        return self.__class__(self._only_full_mapper_zero('get'),
                              session=db.session(), _with_deleted=True)

    def _get(self, *args, **kwargs):
        # this calls the original query.get function from the base class
        return super(QueryWithSoftDelete, self).get(*args, **kwargs)

    def get(self, *args, **kwargs):
        # the query.get method does not like it if there is a filter clause
        # pre-loaded, so we need to implement it using a workaround
        obj = self.with_deleted()._get(*args, **kwargs)
        return obj if obj is None or self._with_deleted or not obj.deleted else None


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    deleted = db.Column(db.Boolean(), default=False, nullable=False)

    query_class = QueryWithSoftDelete

    def to_dict(self):
        return {'id': self.id, 'name': self.name,
                'url': url_for('get_user', id=self.id)
                if not self.deleted else None}


class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(256))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('User')

    def to_dict(self):
        return {'id': self.id, 'message': self.message,
                'url': url_for('get_message', id=self.id),
                'user_url': url_for('get_user', id=self.user_id)
                if not self.user.deleted else None}


@app.route('/users', methods=['POST'])
def new_user():
    user = User(**request.get_json())
    db.session.add(user)
    db.session.commit()
    return '', 201, {'Location': url_for('get_user', id=user.id)}


@app.route('/users', methods=['GET'])
def get_users():
    users = User.query
    return jsonify({'users': [u.to_dict() for u in users]})


@app.route('/users/<id>', methods=['GET'])
def get_user(id):
    user = User.query.get_or_404(id)
    return jsonify(user.to_dict())


@app.route('/users/<id>', methods=['DELETE'])
def delete_user(id):
    user = User.query.get_or_404(id)
    user.deleted = True
    db.session.commit()
    return '', 204


@app.route('/users/<id>/messages', methods=['POST'])
def new_message(id):
    user = User.query.get_or_404(id)
    message = Message(user_id=user.id, **request.get_json())
    db.session.add(message)
    db.session.commit()
    return '', 201, {'Location': url_for('get_message', id=message.id)}


@app.route('/messages')
def get_messages():
    messages = Message.query
    return jsonify({'messages': [m.to_dict() for m in messages]})


@app.route('/messages/<id>')
def get_message(id):
    message = Message.query.get_or_404(id)
    return jsonify(message.to_dict())
