from flask import Flask, render_template, request, redirect
import mysql.connector
from pymongo import MongoClient

app = Flask(__name__)

users = {
    'user1': {
        'name': 'Renuka',
        'email': 'renuka@example.com',
        'height': 180,
        'weight': 4,
        'bmi': 23.15,
        'age': 300
    }
}

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
            # User credentials are correct, redirect to the homepage
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


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/food')
def food():
    # Retrieve the data from the 'food' collection
    food_data = food_collection.find()

    # Pass the data to the template
    return render_template('food.html', food_data=food_data)


@app.route('/exercise')
def exercise():
    # Retrieve the data from the 'exercise' collection
    exercise_data = exercise_collection.find()

    # Pass the data to the template
    return render_template('exercise.html', exercise_data=exercise_data)


@app.route('/goal')
def goal():
    # Dummy goals data for testing, replace with your logic to retrieve goals
    goals = [
        {
            'name': 'Goal 1',
            'type': 'Bulk',
            'start_date': '2023-06-21',
            'end_date': '2023-06-30',
            'target_weight': 70,
            'target_calories': 2000
        },
        {
            'name': 'Goal 2',
            'type': 'Weight gain',
            'start_date': '2023-07-01',
            'end_date': '2023-07-10',
            'target_weight': 75,
            'target_calories': 2500
        }
    ]

    return render_template('goal.html', goals=goals)


@app.route('/add_goal', methods=['GET', 'POST'])
def add_goal():
    if request.method == 'POST':
        goal_name = request.form['goal-name']
        goal_type = request.form['goal-type']
        start_date = request.form['start-date']
        end_date = request.form['end-date']
        target_weight = request.form['target-weight']
        target_calories = request.form['target-calories']

        # Perform the necessary actions with the submitted goal data
        # (e.g., store it in a database, update the user's goals, etc.)

        return redirect('/goal')  # Redirect to the goal page after submission

    return render_template('add_goal.html')


@app.route('/records')
def records():
    return render_template('records.html')


@app.route('/records_goals')
def goals():
    return render_template('records_goals.html')


@app.route('/dailyplan')
def daily_plan():
    return render_template('dailyplan.html')


@app.route('/profile')
def profile():
    user = users['user1']  # Retrieve the user data, change later guys
    return render_template('profile.html', user=user)


@app.route('/update-profile', methods=['POST'])
def update_profile():
    # Get the updated profile information from the form
    name = request.form['name']
    email = request.form['email']
    height = request.form['height']
    weight = request.form['weight']

    # Update the user's profile data, change later guys
    users['user1']['name'] = name
    users['user1']['email'] = email
    users['user1']['height'] = height
    users['user1']['weight'] = weight

    return redirect('/profile')


if __name__ == '__main__':
    app.run(debug=True)
