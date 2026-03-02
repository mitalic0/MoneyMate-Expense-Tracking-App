
from app import app, db, User, Expense
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random

with app.app_context():
    db.create_all()

    if not User.query.filter_by(email="demo@demo.com").first():
        demo_user = User(
            username="DemoUser",
            email="demo@demo.com",
            password_hash=generate_password_hash("demo123")
        )
        db.session.add(demo_user)
        db.session.commit()

    user = User.query.filter_by(email="demo@demo.com").first()

    categories = ["Food", "Travel", "Shopping", "Bills", "Health", "Entertainment", "Rent"]
    descriptions = ["Zomato", "Swiggy", "Uber Ride", "Metro Card", "Amazon Order",
                    "Electricity Bill", "Pharmacy", "Movie Ticket", "Grocery Store",
                    "Netflix Subscription", "Gym Membership", "Petrol Pump"]

    payments = ["UPI", "Card", "Cash"]

    for _ in range(50):
        expense = Expense(
            amount=random.randint(150, 8000),
            category=random.choice(categories),
            description=random.choice(descriptions),
            date=datetime.today() - timedelta(days=random.randint(0, 120)),
            payment_method=random.choice(payments),
            user_id=user.id
        )
        db.session.add(expense)

    db.session.commit()
    print("50 demo expenses inserted successfully!")
