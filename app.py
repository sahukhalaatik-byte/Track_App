import sqlite3
from datetime import date
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user



app = Flask(__name__)
app.secret_key = 'Donttellthistoanyone'
DATABASE = 'database.db'


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


class User(UserMixin):
    def __init__(self, id, username, email, password):
        self.id = id
        self.username = username
        self.email = email
        self.password = password


@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user:
        return User(user['id'], user['username'], user['email'], user['password'])
    return None


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute('''
                 CREATE TABLE IF NOT EXISTS users (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       username TEXT NOT NULL UNIQUE,
                       email TEXT NOT NULL,
                       password TEXT NOT NULL
                 )
                 ''')


    conn.execute('''
                 CREATE TABLE IF NOT EXISTS transactions (
                         id INTEGER PRIMARY KEY AUTOINCREMENT,
                         title TEXT NOT NULL,
                         amount REAL NOT NULL,
                         type TEXT NOT NULL,
                         category TEXT NOT NULL DEFAULT 'Other',
                         date TEXT NOT NULL,
                         notes TEXT DEFAULT ''
                 )
                 ''')
    conn.commit()
    conn.close()



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        hashed = generate_password_hash(password)

        try:
            conn = get_db()
            conn.execute(
                'INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                (username, email, hashed)
            )
            conn.commit()
            conn.close()
            flash('Account created! Please log in.')
            return redirect(url_for('login'))
        except:
            flash('Username already exists.')
            conn.close()

    return render_template('register.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            login_user(User(user['id'], user['username'], user['email'], user['password']))
            return redirect(url_for('index'))
        else:
            flash('Wrong username or password.')

    return render_template('login.html')



@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))



@app.route('/')

@app.route('/index')
@login_required
def index():
    conn = get_db()

    today = date.today()

    month = int(request.args.get('month', today.month))
    year  = int(request.args.get('year',  today.year))
    no_month_filter = (month == 0)

    filter_type = request.args.get('type', 'all')
    filter_category = request.args.get('category', 'all')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    if no_month_filter:
        query = 'SELECT * FROM transactions WHERE 1=1'
        params = []
    else:
        query = 'SELECT * FROM transactions WHERE strftime("%m", date) = ? AND strftime("%Y", date) = ?'
        params = [str(month).zfill(2), str(year)]

    if filter_type != 'all':
        query += ' AND type = ?'
        params.append(filter_type)

    if filter_category != 'all':
        query += ' AND category = ?'
        params.append(filter_category)

    if date_from:
        query += ' AND date >= ?'
        params.append(date_from)

    if date_to:
        query += ' AND date <= ?'
        params.append(date_to)

    query += ' ORDER BY date DESC'
    transactions = conn.execute(query, params).fetchall()

    total_income = sum(t['amount'] for t in transactions if t['type'] == 'income')
    total_expenses = sum(t['amount'] for t in transactions if t['type'] == 'expense')
    balance = total_income - total_expenses

    conn.close()
    return render_template('index.html',
                           transactions=transactions,
                           total_income=total_income,
                           total_expenses=total_expenses,
                           balance=balance,
                           month=month,
                           year=year,
                           no_month_filter=no_month_filter,
                           filter_type=filter_type,
                           filter_category=filter_category,
                           date_from=date_from,
                           date_to=date_to,
                           )



@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        title = request.form['title']
        amount = float(request.form['amount'])
        type_ = request.form['type']
        category = request.form['category']
        txn_date = request.form['date']
        notes = request.form.get('notes', '')

        conn = get_db()
        conn.execute(
            'INSERT INTO transactions (title, amount, type, category, date, notes) VALUES (?, ?, ?, ?, ?, ?)',
            (title, amount, type_, category, txn_date, notes)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    return render_template('add.html')



@app.route('/delete/<int:id>')
@login_required
def delete(id):
    conn = get_db()
    conn.execute('DELETE FROM transactions WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))



@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    conn = get_db()
    transaction = conn.execute(
        'SELECT * FROM transactions WHERE id = ?', (id,)
    ).fetchone()

    if request.method == 'POST':
        title = request.form['title']
        amount = float(request.form['amount'])
        type_ = request.form['type']
        category = request.form['category']
        txn_date = request.form['date']
        notes = request.form.get('notes', '')

        conn.execute(
            'UPDATE transactions SET title=?, amount=?, type=?, category=?, date=?, notes=? WHERE id=?',
            (title, amount, type_, category, txn_date, notes, id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    conn.close()
    return render_template('edit.html', trn=transaction)



if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5001)