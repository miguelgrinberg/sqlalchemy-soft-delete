from flask import Flask, request, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))

    def to_dict(self):
        return {'id': self.id, 'name': self.name,
                'url': url_for('get_user', id=self.id)}


class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(256))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('User')

    def to_dict(self):
        return {'id': self.id, 'message': self.message,
                'url': url_for('get_message', id=self.id),
                'user_url': url_for('get_user', id=self.user_id)}


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
