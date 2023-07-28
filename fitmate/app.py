from flask import Flask, render_template, request, redirect, url_for, session, flash, get_flashed_messages
import mysql.connector
from pymongo import MongoClient
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, date
import random

app = Flask(__name__)
app.secret_key = 'G\x11\xd9\x9aC\xafi\xe8^.hf\x81PDb}4M\xea\x8e\x7f\xa9\x90'

# Create a MongoClient and connect to your MongoDB server
client = MongoClient()

# Connect to the 'fitmATE' database YESSSSSSSSSSSSIR
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
        select_query = "SELECT * FROM users WHERE name = %s"
        cursor.execute(select_query, (name,))
        user = cursor.fetchone()

        if user and check_password_hash(user[3], password):
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
            flash('Invalid username or password', 'error')

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

        hashed_password = generate_password_hash(password)

        # Insert the user registration data into the database
        insert_query = "INSERT INTO users (name, email, password, height, weight, date_of_birth) VALUES (%s, %s, %s, %s, %s, %s)"
        values = (name, email, hashed_password, height, weight, date_of_birth)
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

def generate_meal_plan(daily_calorie_intake, available_food_items):
    # The number of meals to generate (breakfast, lunch, and dinner)
    num_meals = 3

    # Initialize the meal plan
    meal_plan = {
        'breakfast': [],
        'lunch': [],
        'dinner': []
    }

    # Calculate the rough target calorie range for each meal
    target_calories_per_meal = daily_calorie_intake / num_meals
    min_calories_per_meal = target_calories_per_meal * 0.8
    max_calories_per_meal = target_calories_per_meal * 1.2

    # Check if there are available food items
    if not available_food_items:
        print("No available food items.")
        return meal_plan

    # Function to calculate the remaining calories for a specific meal
    def calculate_remaining_calories(meal):
        return max_calories_per_meal - sum(float(food['calories']) for food in meal)

    # Function to randomly select a food item from available_food_items based on calories
    def select_food_item(remaining_calories):
        candidates = [food for food in available_food_items if float(food['calories']) <= remaining_calories]

        if candidates:
            selected_food = random.choice(candidates)
            available_food_items.remove(selected_food)  # Remove the selected food item from the list
            return selected_food
        else:
            return None

    # Generate meal plans for each meal
    for meal_time in meal_plan.keys():
        remaining_calories = calculate_remaining_calories(meal_plan[meal_time])

        while remaining_calories > 0:
            selected_food = select_food_item(remaining_calories)

            if selected_food:
                meal_plan[meal_time].append(selected_food)
                remaining_calories = calculate_remaining_calories(meal_plan[meal_time])
            else:
                # If there are no more suitable food items, break the loop
                break

    return meal_plan


@app.route('/')
@login_required
def home():
    # Get the current date
    today = date.today()
    food_data = list(food_collection.find())
    print("Keys in a sample document:", food_data[0].keys())
    user = session.get('user')

    user_id = user['id']

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

    values = (user_id,)

    cursor.execute(actual_meal_query, values)
    rows1 = cursor.fetchall()

    cursor.execute(exercise_query, values)
    rows2 = cursor.fetchall()

    daily_plans = {}
    for row in rows1:
        daily_plan_id = row[0]
        if daily_plan_id not in daily_plans:
            daily_plans[daily_plan_id] = {
                'id': daily_plan_id,
                'goal_id': row[1],
                'date': row[2],
                'net_calories': row[3],
                'breakfast_meals': [],
                'lunch_meals': [],
                'dinner_meals': [],
                'exercises': []
            }

        meal_timeframe = row[6]
        food_name = row[5]
        calories_gained = row[4]
        meal_id = row[7]

        meal = {'id': meal_id, 'food_name': food_name, 'calories_gained': calories_gained}
        if meal_timeframe == 'Breakfast':
            daily_plans[daily_plan_id]['breakfast_meals'].append(meal)
        elif meal_timeframe == 'Lunch':
            daily_plans[daily_plan_id]['lunch_meals'].append(meal)
        elif meal_timeframe == 'Dinner':
            daily_plans[daily_plan_id]['dinner_meals'].append(meal)

    for row in rows2:
        daily_plan_id = row[0]
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

            daily_plans[daily_plan_id]['exercises'].append(exercise)

    daily_plans = list(daily_plans.values())

    # Generate meal plans for each daily plan
    for dp in daily_plans:
        goal_id = dp['goal_id']

        # Fetch the goal data to get the target calories
        goal_query = "SELECT target_calories FROM goals WHERE goal_id = %s"
        cursor.execute(goal_query, (goal_id,))
        goal_data = cursor.fetchone()
        target_calories = goal_data[0] if goal_data else 2000  # Default to 2000 calories if goal data is not available
        print("Target Calories:", target_calories)

        # Generate meal plan based on available food data
        available_food_items = [{'food_name': item['Food'], 'calories': item['Calories']} for item in food_data]

        generated_meal_plan = generate_meal_plan(target_calories, available_food_items)

        # Assign generated meal plan to the corresponding mealtime
        dp['generated_breakfast'] = generated_meal_plan['breakfast']
        dp['generated_lunch'] = generated_meal_plan['lunch']
        dp['generated_dinner'] = generated_meal_plan['dinner']

    return render_template('home.html', user=user, daily_plans=daily_plans, food_data=food_data, today=today, target_calories=target_calories)



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

def generate_daily_plans(goal_id, start_date, end_date, target_calories):
    current_date = start_date
    delta = timedelta(days=1)

    while current_date <= end_date:
        # Calculate net_calories for each daily plan (initially set to 0)
        net_calories = 0

        # Insert the daily plan into the database
        insert_query = "INSERT INTO daily_plan (goal_id, date, net_calories) VALUES (%s, %s, %s)"
        values = (goal_id, current_date, net_calories)
        cursor.execute(insert_query, values)
        db_mysql.commit()

        # Move to the next date
        current_date += delta

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
        # Convert start_date and end_date to datetime.date objects
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        # Insert the goal into the database
        user = session.get('user')
        user_id = user['id']
        insert_query = "INSERT INTO goals (user_id, goal_type, target_weight, target_calories, start_date, end_date, goal_name) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        values = (user_id, goal_type, target_weight, target_calories, start_date, end_date, goal_name)
        cursor.execute(insert_query, values)
        db_mysql.commit()
        goal_id = cursor.lastrowid
        generate_daily_plans(goal_id, start_date, end_date, target_calories)
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
        # Delete the dailyplans from the database
        delete_query = "DELETE FROM daily_plan WHERE goal_id = %s"
        values = (goal_id,)
        cursor.execute(delete_query, values)
        db_mysql.commit()
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

    # Query the database to calculate BMI and age
    query = "SELECT name, email, height, weight, date_of_birth, " \
            "FLOOR(weight / ((height / 100) * (height / 100))) AS bmi, " \
            "TIMESTAMPDIFF(YEAR, date_of_birth, CURDATE()) AS age " \
            "FROM users WHERE user_id = %s"

    cursor.execute(query, (user['id'],))
    user_data = cursor.fetchone()

    # Extract BMI and age from the query result
    bmi = user_data[5] if user_data[5] else None
    age = user_data[6] if user_data[6] else None

    return render_template('profile.html', user=user, bmi=bmi, age=age)

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

    # Update the user's information in the database
    update_query = "UPDATE users SET name = %s, email = %s, height = %s, weight = %s WHERE user_id = %s"
    values = (name, email, height, weight, user['id'])
    cursor.execute(update_query, values)
    db_mysql.commit()

    # Redirect to the profile page with a success message
    flash('User updated successfully', 'success')
    return redirect('/profile')



@app.route('/change-password', methods=['POST'])
@login_required
def change_password():
    user = session.get('user')

    # Get the submitted password data from the form
    current_password = request.form['current_password']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']

    # Check if the new password and confirm password match
    if new_password != confirm_password:
        flash('New password and confirm password must match', 'error')
        return redirect('/profile')

    # Retrieve the user's current hashed password from the database
    select_query = "SELECT password FROM users WHERE user_id = %s"
    cursor.execute(select_query, (user['id'],))
    stored_password = cursor.fetchone()[0]

    # Check if the current password matches the stored password
    if check_password_hash(stored_password, current_password):
        # Hash the new password before storing it in the database
        hashed_password = generate_password_hash(new_password)

        # Update the password in the database
        update_query = "UPDATE users SET password = %s WHERE user_id = %s"
        values = (hashed_password, user['id'])
        cursor.execute(update_query, values)
        db_mysql.commit()
        print(f"Password updated: {new_password}")
        # Redirect to the profile page with a success message
        flash('Password updated successfully', 'success')
        return redirect('/profile')

    else:
        # Password verification failed, show an error message
        flash('Incorrect current password', 'error')
        print("Flash messages:", get_flashed_messages())
        return redirect('/profile')



if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)
