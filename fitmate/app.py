from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from pymongo import MongoClient
from functools import wraps

app = Flask(__name__)
app.secret_key = 'G\x11\xd9\x9aC\xafi\xe8^.hf\x81PDb}4M\xea\x8e\x7f\xa9\x90'

# Create a MongoClient and connect to your MongoDB server
client = MongoClient()

# Connect to the 'fitmATE' database
db_mongo = client.fitmATE

# Get a reference to the collections
exercise_collection = db_mongo.exercise
food_collection = db_mongo.food

# MySQL database connection details
db_host = 'localhost'
db_user = 'root'
db_password = '1234'
db_name = 'fitmATE'

# Create a MySQL connection and cursor
db_mysql = mysql.connector.connect(
    host=db_host,
    user=db_user,
    password=db_password,
    database=db_name
)
cursor = db_mysql.cursor()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']

        # Check the user's credentials in the MySQL database
        select_query = "SELECT * FROM users WHERE name = %s AND password = %s"
        values = (name, password)
        cursor.execute(select_query, values)
        user = cursor.fetchone()

        if user:
            # User credentials are correct, store the user data in the session
            session['user'] = {
                'id': user[0],
                'name': user[1],
                'email': user[2],
                'height': user[3],
                'weight': user[4],
                'bmi': user[5],
                'age': user[6]
            }

            # Redirect to the homepage
            return redirect('/')
        else:
            # Invalid username or password, show an error message
            return 'Invalid username or password'

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        height = request.form['height']
        weight = request.form['weight']
        date_of_birth = request.form['date_of_birth']

        # Insert the user registration data into the database
        insert_query = "INSERT INTO users (name, email, password, height, weight, date_of_birth) VALUES (%s, %s, %s, %s, %s, %s)"
        values = (name, email, password, height, weight, date_of_birth)
        cursor.execute(insert_query, values)
        db_mysql.commit()

        return redirect('/')

    return render_template('register.html')


@app.route('/logout')
def logout():
    # Clear the session data
    session.clear()
    # Redirect to the login page
    return redirect(url_for('login'))


@app.route('/')
@login_required
def home():
    user = session.get('user')  # Retrieve the user data from the session
    return render_template('home.html', user=user)


@app.route('/food')
@login_required
def food():
    # Retrieve the data from the 'foodcollection
    food_data = food_collection.find()

    user = session.get('user')  # Retrieve the user data from the session

    # Pass the data to the template
    return render_template('food.html', food_data=food_data, user=user)


@app.route('/exercise')
@login_required
def exercise():
    # Retrieve the data from the 'exercise' collection
    exercise_data = exercise_collection.find()

    user = session.get('user')  # Retrieve the user data from the session

    # Pass the data to the template
    return render_template('exercise.html', exercise_data=exercise_data, user=user)


@app.route('/goal')
@login_required
def goal():
    user = session.get('user')  # Retrieve the user data from the session

    # Retrieve the user's goals from the database
    user_id = user['id']
    select_query = "SELECT * FROM goals WHERE user_id = %s"
    values = (user_id,)
    cursor.execute(select_query, values)
    goals = cursor.fetchall()

    return render_template('goal.html', goals=goals, user=user)


@app.route('/add_goal', methods=['GET', 'POST'])
@login_required
def add_goal():
    if request.method == 'POST':
        goal_name = request.form['goal-name']
        goal_type = request.form['goal-type']
        start_date = request.form['start-date']
        end_date = request.form['end-date']
        target_weight = request.form['target-weight']
        target_calories = request.form['target-calories']

        # Insert the goal into the database
        user = session.get('user')
        user_id = user['id']
        insert_query = "INSERT INTO goals (user_id, goal_type, target_weight, target_calories, start_date, end_date) VALUES (%s, %s, %s, %s, %s, %s)"
        values = (user_id, goal_type, target_weight, target_calories, start_date, end_date)
        cursor.execute(insert_query, values)
        db_mysql.commit()

        return redirect('/goal')

    user = session.get('user')  # Retrieve the user data from the session

    return render_template('add_goal.html', user=user)


@app.route('/records')
@login_required
def records():
    user = session.get('user')  # Retrieve the user data from the session
    return render_template('records.html', user=user)


@app.route('/records_goals')
@login_required
def goals():
    user = session.get('user')  # Retrieve the user data from the session
    return render_template('records_goals.html', user=user)


@app.route('/dailyplan')
@login_required
def daily_plan():
    user = session.get('user')  # Retrieve the user data from the session
    return render_template('dailyplan.html', user=user)


@app.route('/profile')
@login_required
def profile():
    user = session.get('user')  # Retrieve the user data from the session
    return render_template('profile.html', user=user)


@app.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    # Get the updated profile information from the form
    name = request.form['name']
    email = request.form['email']
    height = request.form['height']
    weight = request.form['weight']

    # Update the user's profile data in the session
    user = session.get('user')
    if user:
        user['name'] = name
        user['email'] = email
        user['height'] = height
        user['weight'] = weight

    return redirect('/profile')


if __name__ == '__main__':
    app.run(debug=True)
