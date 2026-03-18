import os
from flask import Flask, render_template, request, redirect, url_for
from google.cloud import datastore
import datetime
import google.oauth2.id_token
from google.auth.transport import requests as google_requests

app = Flask(__name__)

firebase_request_adapter = google_requests.Request()
datastore_client = datastore.Client()

def verify_token(id_token):
    """Verify Firebase token and return user claims."""
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

@app.route('/')
def index():
    """Main todo page – only accessible when authenticated."""
    id_token = request.cookies.get('token')
    user_claims = verify_token(id_token)
    if user_claims:
        user_id = user_claims['user_id']
        query = datastore_client.query(kind='Todo')
        query.add_filter('user_id', '=', user_id)
        query.order = ['created']
        todos = list(query.fetch())
        return render_template('index.html', todos=todos, user=user_claims)
    else:
        return redirect(url_for('login'))

@app.route('/login')
def login():
    """Login page – redirects to index if already logged in."""
    id_token = request.cookies.get('token')
    user_claims = verify_token(id_token)
    if user_claims:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/add', methods=['POST'])
def add():
    """Add a new todo."""
    id_token = request.cookies.get('token')
    user_claims = verify_token(id_token)
    if not user_claims:
        return redirect(url_for('login'))

    title = request.form['title']
    if title:
        key = datastore_client.key('Todo')
        todo = datastore.Entity(key=key)
        todo.update({
            'title': title,
            'created': datetime.datetime.utcnow(),
            'user_id': user_claims['user_id']
        })
        datastore_client.put(todo)
    return redirect(url_for('index'))

@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    """Delete a todo."""
    id_token = request.cookies.get('token')
    user_claims = verify_token(id_token)
    if not user_claims:
        return redirect(url_for('login'))

    key = datastore_client.key('Todo', id)
    todo = datastore_client.get(key)
    if todo and todo.get('user_id') == user_claims['user_id']:
        datastore_client.delete(key)
    return redirect(url_for('index'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    """Edit a todo (show edit form and process update)."""
    id_token = request.cookies.get('token')
    user_claims = verify_token(id_token)
    if not user_claims:
        return redirect(url_for('login'))

    key = datastore_client.key('Todo', id)
    todo = datastore_client.get(key)
    if not todo or todo.get('user_id') != user_claims['user_id']:
        return "Forbidden", 403

    if request.method == 'POST':
        new_title = request.form['title']
        if new_title:
            todo['title'] = new_title
            datastore_client.put(todo)
            return redirect(url_for('index'))

    return render_template('edit.html', todo=todo)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)