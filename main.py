import os
import datetime
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import google.oauth2.id_token
from google.auth.transport import requests as google_requests

app = Flask(__name__)

# PostgreSQL connection from Railway
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ---------- Database Models ----------
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    firebase_uid = db.Column(db.String(128), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)

class Todo(db.Model):
    __tablename__ = 'todos'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    created = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user_id = db.Column(db.String(128), db.ForeignKey('users.firebase_uid'), nullable=False)

# Create tables automatically (only once, when app starts)
with app.app_context():
    db.create_all()

# ---------- Firebase Setup ----------
firebase_request_adapter = google_requests.Request()

def verify_token(id_token):
    if not id_token:
        return None
    try:
        claims = google.oauth2.id_token.verify_firebase_token(
            id_token, firebase_request_adapter
        )
        return claims
    except ValueError as e:
        print(f"Token verification failed: {e}")
        return None

# ---------- Routes ----------
@app.route('/')
def index():
    id_token = request.cookies.get('token')
    user_claims = verify_token(id_token)
    if not user_claims:
        return redirect(url_for('login'))

    user_id = user_claims['user_id']
    # Auto-create user record if not exists
    user = User.query.filter_by(firebase_uid=user_id).first()
    if not user:
        user = User(firebase_uid=user_id, email=user_claims.get('email', ''))
        db.session.add(user)
        db.session.commit()

    todos = Todo.query.filter_by(user_id=user_id).order_by(Todo.created).all()
    return render_template('index.html', todos=todos, user=user_claims)

@app.route('/login')
def login():
    id_token = request.cookies.get('token')
    user_claims = verify_token(id_token)
    if user_claims:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/add', methods=['POST'])
def add():
    id_token = request.cookies.get('token')
    user_claims = verify_token(id_token)
    if not user_claims:
        return redirect(url_for('login'))

    title = request.form['title']
    if title:
        todo = Todo(title=title, user_id=user_claims['user_id'])
        db.session.add(todo)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    id_token = request.cookies.get('token')
    user_claims = verify_token(id_token)
    if not user_claims:
        return redirect(url_for('login'))

    todo = Todo.query.get_or_404(id)
    if todo.user_id == user_claims['user_id']:
        db.session.delete(todo)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    id_token = request.cookies.get('token')
    user_claims = verify_token(id_token)
    if not user_claims:
        return redirect(url_for('login'))

    todo = Todo.query.get_or_404(id)
    if todo.user_id != user_claims['user_id']:
        return "Forbidden", 403

    if request.method == 'POST':
        new_title = request.form['title']
        if new_title:
            todo.title = new_title
            db.session.commit()
            return redirect(url_for('index'))

    return render_template('edit.html', todo=todo)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)