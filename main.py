import os

from flask import Flask, render_template, request, redirect, url_for
import google.oauth2.id_token
from google.auth.transport import requests as google_requests

from models import Todo, get_engine, get_session_factory, init_db

app = Flask(__name__)

# ── Database setup ────────────────────────────────────────────────────────────
engine         = get_engine()
SessionFactory = get_session_factory(engine)
init_db(engine)          # Creates tables on first boot if they don't exist

# ── Firebase auth ─────────────────────────────────────────────────────────────
firebase_request_adapter = google_requests.Request()


def verify_token(id_token):
    """Verify Firebase ID token and return claims dict, or None."""
    if not id_token:
        return None
    try:
        return google.oauth2.id_token.verify_firebase_token(
            id_token, firebase_request_adapter
        )
    except ValueError as e:
        print(f"Token verification failed: {e}")
        return None


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Main todo page – only accessible when authenticated."""
    id_token   = request.cookies.get('token')
    user_claims = verify_token(id_token)
    if not user_claims:
        return redirect(url_for('login'))

    user_id = user_claims['user_id']
    with SessionFactory() as session:
        todos = (
            session.query(Todo)
            .filter(Todo.user_id == user_id)
            .order_by(Todo.created.asc())
            .all()
        )
        # Detach objects from session so they're usable in the template
        session.expunge_all()

    return render_template('index.html', todos=todos, user=user_claims)


@app.route('/login')
def login():
    """Login page – redirects to index if already logged in."""
    id_token = request.cookies.get('token')
    if verify_token(id_token):
        return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/add', methods=['POST'])
def add():
    """Add a new todo."""
    id_token    = request.cookies.get('token')
    user_claims = verify_token(id_token)
    if not user_claims:
        return redirect(url_for('login'))

    title = request.form.get('title', '').strip()
    if title:
        with SessionFactory() as session:
            todo = Todo(
                user_id=user_claims['user_id'],
                email=user_claims.get('email', ''),
                title=title,
            )
            session.add(todo)
            session.commit()

    return redirect(url_for('index'))


@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    """Delete a todo."""
    id_token    = request.cookies.get('token')
    user_claims = verify_token(id_token)
    if not user_claims:
        return redirect(url_for('login'))

    with SessionFactory() as session:
        todo = session.query(Todo).filter(Todo.id == id).first()
        if todo and todo.user_id == user_claims['user_id']:
            session.delete(todo)
            session.commit()

    return redirect(url_for('index'))


@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    """Edit a todo (show edit form and process update)."""
    id_token    = request.cookies.get('token')
    user_claims = verify_token(id_token)
    if not user_claims:
        return redirect(url_for('login'))

    with SessionFactory() as session:
        todo = session.query(Todo).filter(Todo.id == id).first()

        if not todo or todo.user_id != user_claims['user_id']:
            return "Forbidden", 403

        if request.method == 'POST':
            new_title = request.form.get('title', '').strip()
            if new_title:
                todo.title = new_title
                session.commit()
                return redirect(url_for('index'))

        session.expunge(todo)   # detach before leaving the with-block

    return render_template('edit.html', todo=todo)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)