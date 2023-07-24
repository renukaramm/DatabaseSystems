from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from pymongo import MongoClient
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

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
                # 3 is for password
                'height': user[4],
                'weight': user[5],
                'date_of_birth': user[6]
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
    food_data = food_collection.find()

    user = session.get('user')  # Retrieve the user data from the session

    user_id = user['id']
    # Fetch the daily plans with associated meals and calories gained from the database
    actual_meal_query = """
        SELECT dp.daily_plan_id, dp.goal_id, dp.date, dp.net_calories,
               m.calories_gained, m.food_name, m.meal_timeframe, m.meal_id
        FROM daily_plan dp
        JOIN goals g ON dp.goal_id = g.goal_id
        LEFT JOIN meal m ON dp.daily_plan_id = m.daily_plan_id AND m.meal_type = 'actual'
        WHERE g.user_id = %s
    """

    exercise_query = """
        SELECT dp.daily_plan_id, e.exercise_id, e.exercise_type, e.activity, e.description, e.calories_burnt
        FROM daily_plan dp
        JOIN goals g ON dp.goal_id = g.goal_id
        LEFT JOIN exercise e ON dp.daily_plan_id = e.daily_plan_id
        WHERE g.user_id = %s
    """

    values = (user_id,)  # Pass user_id as a tuple

    cursor.execute(actual_meal_query, values)
    rows1 = cursor.fetchall()

    cursor.execute(exercise_query, values)
    rows2 = cursor.fetchall()

    daily_plans = {}
    for row in rows1:
        daily_plan_id = row[0]  # Access the column value by index
        if daily_plan_id not in daily_plans:
            daily_plans[daily_plan_id] = {
                'id': daily_plan_id,
                'goal_id': row[1],  # Access the column value by index
                'date': row[2],  # Access the column value by index
                'net_calories': row[3],  # Access the column value by index
                'breakfast_meals': [],
                'lunch_meals': [],
                'dinner_meals': [],
                'exercises': []
            }

        meal_timeframe = row[6]  # Access the column value by index
        food_name = row[5]  # Access the column value by index
        calories_gained = row[4]  # Access the column value by index
        meal_id = row[7]

        meal = {'id': meal_id, 'food_name': food_name, 'calories_gained': calories_gained}
        if meal_timeframe == 'Breakfast':
            daily_plans[daily_plan_id]['breakfast_meals'].append(meal)
        elif meal_timeframe == 'Lunch':
            daily_plans[daily_plan_id]['lunch_meals'].append(meal)
        elif meal_timeframe == 'Dinner':
            daily_plans[daily_plan_id]['dinner_meals'].append(meal)

    # Now, let's loop through the exercises and append them to the correct daily plan
    for row in rows2:
        daily_plan_id = row[0]  # Access the daily_plan_id from the exercise query
        exercise_id = row[1]
        exercise_type = row[2]
        activity = row[3]
        description = row[4]
        calories_burnt = row[5]

        if exercise_id or exercise_type or activity or description or calories_burnt:
            exercise = {
                'id': exercise_id,
                'exercise_type': exercise_type,
                'activity': activity,
                'description': description,
                'calories_burnt': calories_burnt
            }

            # Append the exercise to the correct daily plan using daily_plan_id as the key
            daily_plans[daily_plan_id]['exercises'].append(exercise)

    daily_plans = list(daily_plans.values())

    return render_template('home.html', user=user, daily_plans=daily_plans, food_data=food_data)


@app.route('/add_actual_meal', methods=['POST'])
@login_required
def add_actual_meal():
    meal_timeframe = request.form['mealTimeframe']
    food_name = request.form['foodName']
    calories_gained = float(request.form['caloriesGained'])
    daily_plan_id = int(request.form.get('dailyPlanId'))

    # Insert the actual meal into the database
    insert_query = "INSERT INTO meal (daily_plan_id, meal_type, food_name, calories_gained, meal_timeframe) " \
                   "VALUES (%s, %s, %s, %s, %s)"
    values = (daily_plan_id, 'actual', food_name, calories_gained, meal_timeframe)
    cursor.execute(insert_query, values)

    # Update the net_calories in the daily_plan table
    update_query = "UPDATE daily_plan SET net_calories = net_calories + %s WHERE daily_plan_id = %s"
    values = (calories_gained, daily_plan_id)
    cursor.execute(update_query, values)

    db_mysql.commit()

    return redirect('/')


@app.route('/update_actual_meal', methods=['POST'])
@login_required
def update_actual_meal():
    meal_id = int(request.form['mealId'])
    food_name = request.form['foodName']
    calories_gained = float(request.form['caloriesGained'])
    daily_plan_id = int(request.form['editDailyPlanId'])

    # Get the old calories gained value for the meal
    get_old_calories_query = "SELECT calories_gained FROM meal WHERE meal_id = %s"
    cursor.execute(get_old_calories_query, (meal_id,))
    old_calories_gained = cursor.fetchone()[0]

    # Calculate the difference between old and new calories
    calories_difference = calories_gained - old_calories_gained

    # Update the actual meal in the database
    update_meal_query = "UPDATE meal SET food_name = %s, calories_gained = %s WHERE meal_id = %s"
    update_meal_values = (food_name, calories_gained, meal_id)
    cursor.execute(update_meal_query, update_meal_values)

    # Update the net_calories in the daily_plan table
    update_dp_query = "UPDATE daily_plan SET net_calories = net_calories + %s WHERE daily_plan_id = %s"
    update_dp_values = (calories_difference, daily_plan_id)
    cursor.execute(update_dp_query, update_dp_values)

    db_mysql.commit()

    return redirect('/')


@app.route('/delete_actual_meal', methods=['POST'])
@login_required
def delete_actual_meal():
    meal_id = request.form['mealId']
    daily_plan_id = int(request.form['deleteDailyPlanId'])
    calories_gained = float(request.form['caloriesGained'])

    if meal_id:
        meal_id = int(meal_id)

        # Delete the actual meal from the database
        delete_query = "DELETE FROM meal WHERE meal_id = %s"
        values = (meal_id,)
        cursor.execute(delete_query, values)

        # Update the net_calories in the daily_plan table
        update_dp = "UPDATE daily_plan SET net_calories = net_calories - %s WHERE daily_plan_id = %s"
        values = (calories_gained, daily_plan_id)
        cursor.execute(update_dp, values)

        db_mysql.commit()

    return redirect('/')


@app.route('/add_exercise', methods=['POST'])
@login_required
def add_exercise():
    exercise_type = request.form['exerciseType']
    activity = request.form['activity']
    description = request.form['description']
    calories_burnt = float(request.form['caloriesBurnt'])
    daily_plan_id = int(request.form.get('dailyPlanId'))

    # Insert the exercise into the database
    insert_query = "INSERT INTO exercise (daily_plan_id, exercise_type, activity, description, calories_burnt) " \
                   "VALUES (%s, %s, %s, %s, %s)"
    values = (daily_plan_id, exercise_type, activity, description, calories_burnt)
    cursor.execute(insert_query, values)

    # Update the net_calories in the daily_plan table
    update_query = "UPDATE daily_plan SET net_calories = net_calories - %s WHERE daily_plan_id = %s"
    values = (calories_burnt, daily_plan_id)
    cursor.execute(update_query, values)

    db_mysql.commit()

    return redirect('/')


@app.route('/update_exercise', methods=['POST'])
@login_required
def update_exercise():
    exercise_id = int(request.form['exerciseId'])
    exercise_type = request.form['exerciseType']
    activity = request.form['activity']
    description = request.form['description']
    calories_burnt = float(request.form['caloriesBurnt'])
    daily_plan_id = int(request.form['editDailyPlanId'])

    # Update the exercise in the database
    update_exercise_query = "UPDATE exercise SET exercise_type = %s, activity = %s, description = %s, " \
                            "calories_burnt = %s WHERE exercise_id = %s"
    update_exercise_values = (exercise_type, activity, description, calories_burnt, exercise_id)
    cursor.execute(update_exercise_query, update_exercise_values)

    db_mysql.commit()

    return redirect('/')


@app.route('/delete_exercise', methods=['POST'])
@login_required
def delete_exercise():
    exercise_id = request.form['exerciseId']
    daily_plan_id = int(request.form['deleteDailyPlanId'])
    calories_burnt = float(request.form['caloriesBurnt'])

    if exercise_id:
        exercise_id = int(exercise_id)

        # Delete the exercise from the database
        delete_query = "DELETE FROM exercise WHERE exercise_id = %s"
        values = (exercise_id,)
        cursor.execute(delete_query, values)

        db_mysql.commit()

    return redirect('/')


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
        target_weight = request.form['target-weight']
        target_calories = request.form['target-calories']
        start_date = request.form['start-date']
        end_date = request.form['end-date']


        # Insert the goal into the database
        user = session.get('user')
        user_id = user['id']
        insert_query = "INSERT INTO goals (user_id, goal_type, target_weight, target_calories, start_date, end_date, goal_name) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        values = (user_id, goal_type, target_weight, target_calories, start_date, end_date, goal_name)
        cursor.execute(insert_query, values)
        db_mysql.commit()

        return redirect('/goal')

    user = session.get('user')  # Retrieve the user data from the session

    return render_template('add_goal.html', user=user)


@app.route('/update_goal', methods=['POST'])
@login_required
def update_goal():
    goal_id = request.form.get('goalId')
    goal_name = request.form['goalName']
    goal_type = request.form['goalType']
    target_weight = request.form['targetWeight']
    target_calories = request.form['targetCalories']
    start_date = request.form['startDate']
    end_date = request.form['endDate']


    # Update the goal in the database
    update_query = "UPDATE goals SET goal_name = %s, goal_type = %s, target_weight = %s, target_calories = %s, start_date = %s, end_date = %s WHERE goal_id = %s"
    values = (goal_name, goal_type, target_weight, target_calories, start_date, end_date, goal_id)
    cursor.execute(update_query, values)
    db_mysql.commit()

    return redirect('/goal')


@app.route('/delete_goal', methods=['POST'])
@login_required
def delete_goal():
    goal_id = request.form['goalId']

    if goal_id:
        goal_id = int(goal_id)

        # Delete the goal from the database
        delete_query = "DELETE FROM goals WHERE goal_id = %s"
        values = (goal_id,)
        cursor.execute(delete_query, values)
        db_mysql.commit()

    return redirect('/goal')


@app.route('/records')
@login_required
def records():
    user = session.get('user')  # Retrieve the user data from the session
    return render_template('records.html', user=user)


@app.route('/records_goals')
@login_required
def records_goals():
    user = session.get('user')  # Retrieve the user data from the session

    # Retrieve the user's goals from the database
    user_id = user['id']
    # user_id = 1
    select_query = "SELECT * FROM goals WHERE user_id = %s"
    values = (user_id,)
    cursor.execute(select_query, values)
    goals = cursor.fetchall()
    # Prepare data for the graph
    graph_data = {}  # A dictionary to hold the graph data for each goal

    for goal in goals:
        goal_id = goal[0]  # Access the goal_id from the goal tuple
        goal_name = goal[2]  # Access the goal_name from the goal tuple

        # Fetch the daily plan data for the current goal from the database
        daily_plan_query = "SELECT date, net_calories FROM daily_plan WHERE goal_id = %s ORDER BY date ASC"
        cursor.execute(daily_plan_query, (goal_id,))
        daily_plan_data = cursor.fetchall()

        # Extract dates and net calories for the graph
        dates = []
        net_calories = []

        for daily_plan in daily_plan_data:
            dates.append(daily_plan[0].strftime('%Y-%m-%d'))  # Convert date object to string
            net_calories.append(daily_plan[1])

        # Add the graph data for the current goal to the graph_data dictionary
        graph_data[goal_name] = {
            'dates': dates,
            'net_calories': net_calories,
        }

    return render_template('records_goals.html', user=user, goals=goals, graph_data=graph_data)


@app.route('/dailyplan')
@login_required
def daily_plan():
    user = session.get('user')  # Retrieve the user data from the session

    user_id = user['id']
    # Fetch the daily plans with associated meals and calories gained from the database
    actual_meal_query = """
            SELECT dp.daily_plan_id, dp.goal_id, dp.date, dp.net_calories,
                   m.calories_gained, m.food_name, m.meal_timeframe, m.meal_id
            FROM daily_plan dp
            JOIN goals g ON dp.goal_id = g.goal_id
            LEFT JOIN meal m ON dp.daily_plan_id = m.daily_plan_id AND m.meal_type = 'actual'
            WHERE g.user_id = %s
        """

    exercise_query = """
            SELECT dp.daily_plan_id, e.exercise_id, e.exercise_type, e.activity, e.description, e.calories_burnt
            FROM daily_plan dp
            JOIN goals g ON dp.goal_id = g.goal_id
            LEFT JOIN exercise e ON dp.daily_plan_id = e.daily_plan_id
            WHERE g.user_id = %s
        """

    values = (user_id,)  # Pass user_id as a tuple

    cursor.execute(actual_meal_query, values)
    rows1 = cursor.fetchall()

    cursor.execute(exercise_query, values)
    rows2 = cursor.fetchall()

    daily_plans = {}
    for row in rows1:
        daily_plan_id = row[0]  # Access the column value by index
        if daily_plan_id not in daily_plans:
            daily_plans[daily_plan_id] = {
                'id': daily_plan_id,
                'goal_id': row[1],  # Access the column value by index
                'date': row[2],  # Access the column value by index
                'net_calories': row[3],  # Access the column value by index
                'breakfast_meals': [],
                'lunch_meals': [],
                'dinner_meals': [],
                'exercises': []
            }

        meal_timeframe = row[6]  # Access the column value by index
        food_name = row[5]  # Access the column value by index
        calories_gained = row[4]  # Access the column value by index
        meal_id = row[7]

        meal = {'id': meal_id, 'food_name': food_name, 'calories_gained': calories_gained}
        if meal_timeframe == 'Breakfast':
            daily_plans[daily_plan_id]['breakfast_meals'].append(meal)
        elif meal_timeframe == 'Lunch':
            daily_plans[daily_plan_id]['lunch_meals'].append(meal)
        elif meal_timeframe == 'Dinner':
            daily_plans[daily_plan_id]['dinner_meals'].append(meal)

    # Now, let's loop through the exercises and append them to the correct daily plan
    for row in rows2:
        daily_plan_id = row[0]  # Access the daily_plan_id from the exercise query
        exercise_id = row[1]
        exercise_type = row[2]
        activity = row[3]
        description = row[4]
        calories_burnt = row[5]

        if exercise_id or exercise_type or activity or description or calories_burnt:
            exercise = {
                'id': exercise_id,
                'exercise_type': exercise_type,
                'activity': activity,
                'description': description,
                'calories_burnt': calories_burnt
            }

            # Append the exercise to the correct daily plan using daily_plan_id as the key
            daily_plans[daily_plan_id]['exercises'].append(exercise)

    daily_plans = list(daily_plans.values())

    return render_template('dailyplan.html', user=user, daily_plans=daily_plans)


# Inside the profile route, pass the user data to the profile.html template.
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

    # Save the updated user data in the session
    session['user'] = user

    return redirect('/profile')


@app.route('/change-password', methods=['POST'])
@login_required
def change_password():
    user = session.get('user')

    # Get the submitted password data from the form
    current_password = request.form['current_password']
    new_password = request.form['new_password']

    # Check if the current password matches the stored password
    if check_password_hash(user['password'], current_password):
        # Hash the new password before storing it in the database
        hashed_password = generate_password_hash(new_password)

        # Update the password in the database
        update_query = "UPDATE users SET password = %s WHERE user_id = %s"
        values = (hashed_password, user['user_id'])
        cursor.execute(update_query, values)
        db_mysql.commit()

        # Update the password in the session
        user['password'] = hashed_password
        session['user'] = user

        # Redirect to the profile page with a success message
        return redirect('/profile')

    else:
        # Password verification failed, show an error message
        return 'Incorrect current password'



if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)
