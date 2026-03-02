from flask import Flask, render_template, redirect, url_for, request, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import extract
import csv
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# ---------------- MODELS ----------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100))
    description = db.Column(db.String(200))
    date = db.Column(db.Date, nullable=False)
    payment_method = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------- ROUTES ----------------

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        if User.query.filter_by(email=request.form['email']).first():
            flash("Email already exists.", "danger")
            return redirect(url_for('register'))

        user = User(
            username=request.form['username'],
            email=request.form['email'],
            password_hash=generate_password_hash(request.form['password'])
        )
        db.session.add(user)
        db.session.commit()
        flash("Registration successful! Please login.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and check_password_hash(user.password_hash, request.form['password']):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash("Invalid credentials", "danger")

    return render_template('login.html')

# ---------------- DASHBOARD ----------------

@app.route('/dashboard')
@login_required
def dashboard():
    month = request.args.get('month')
    query = Expense.query.filter_by(user_id=current_user.id)

    if month:
        year, month_num = month.split("-")
        query = query.filter(
            extract('year', Expense.date) == int(year),
            extract('month', Expense.date) == int(month_num)
        )

    all_expenses = query.order_by(Expense.date.desc()).all()
    expenses = all_expenses[:5]  # 👈 Only 5 recent
    total = sum(e.amount for e in expenses)

    # Category aggregation
    category_data = {}
    for e in all_expenses:
        category_data[e.category] = category_data.get(e.category, 0) + e.amount

    # Payment aggregation
    payment_data = {}
    for e in all_expenses:
        payment_data[e.payment_method] = payment_data.get(e.payment_method, 0) + e.amount

    # Monthly trend
    trend_data = {}
    all_expenses = Expense.query.filter_by(user_id=current_user.id).all()
    for e in all_expenses:
        key = e.date.strftime("%Y-%m")
        trend_data[key] = trend_data.get(key, 0) + e.amount

    trend_data = dict(sorted(trend_data.items()))

    return render_template(
        "dashboard.html",
        expenses=expenses,  # 👈 IMPORTANT (for recent table)
        total=total,
        category_labels=list(category_data.keys()),
        category_values=list(category_data.values()),
        payment_labels=list(payment_data.keys()),
        payment_values=list(payment_data.values()),
        trend_labels=list(trend_data.keys()),
        trend_values=list(trend_data.values()),
        selected_month=month
    )

# ---------------- EXPENSES PAGE ----------------

@app.route('/expenses')
@login_required
def expenses():
    month = request.args.get('month')
    query = Expense.query.filter_by(user_id=current_user.id)

    if month:
        year, month_num = month.split("-")
        query = query.filter(
            extract('year', Expense.date) == int(year),
            extract('month', Expense.date) == int(month_num)
        )

    expenses = query.order_by(Expense.date.desc()).all()
    total = sum(e.amount for e in expenses)

    return render_template(
        "expenses.html",
        expenses=expenses,
        total=total,
        selected_month=month
    )

# ---------------- ADD EXPENSE ----------------

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_expense():
    if request.method == 'POST':
        expense = Expense(
            amount=float(request.form['amount']),
            category=request.form['category'],
            description=request.form['description'],
            date=datetime.strptime(request.form['date'], "%Y-%m-%d"),
            payment_method=request.form['payment_method'],
            user_id=current_user.id
        )
        db.session.add(expense)
        db.session.commit()
        return redirect(url_for('expenses'))

    return render_template('add_expense.html')

# ---------------- EDIT EXPENSE ----------------

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_expense(id):
    expense = Expense.query.get_or_404(id)

    if expense.user_id != current_user.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('expenses'))

    if request.method == 'POST':
        expense.amount = float(request.form['amount'])
        expense.category = request.form['category']
        expense.description = request.form['description']
        expense.date = datetime.strptime(request.form['date'], "%Y-%m-%d")
        expense.payment_method = request.form['payment_method']
        db.session.commit()
        return redirect(url_for('expenses'))

    return render_template('edit_expense.html', expense=expense)

# ---------------- DELETE EXPENSE ----------------

@app.route('/delete/<int:id>')
@login_required
def delete_expense(id):
    expense = Expense.query.get_or_404(id)

    if expense.user_id != current_user.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('expenses'))

    db.session.delete(expense)
    db.session.commit()
    return redirect(url_for('expenses'))

# ---------------- EXPORT CSV ----------------

@app.route('/export')
@login_required
def export_csv():
    expenses = Expense.query.filter_by(user_id=current_user.id).all()
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(['Amount', 'Category', 'Description', 'Date', 'Payment Method'])

    for e in expenses:
        writer.writerow([e.amount, e.category, e.description, e.date, e.payment_method])

    output.seek(0)

    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        download_name='expenses.csv',
        as_attachment=True
    )

# ---------------- LOGOUT ----------------

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ---------------- RUN ----------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)