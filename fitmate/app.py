from flask import Flask, render_template, request, redirect, url_for, session, flash, get_flashed_messages, jsonify
import mysql.connector
from pymongo import MongoClient
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, date
import random
import json

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
cursor = db_mysql.cursor(buffered=True)


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

@app.route('/generate_meal_plan', methods=['POST'])
def generate_meal_plan():
    # Retrieve the selected mealTimeframe from the form data
    meal_timeframe = request.form.get('mealTimeframe')


    # Fetch the user's goal data to get the target calories
    user_id = session['user']['id']
    goal_query = "SELECT target_calories FROM goals WHERE user_id = %s"
    cursor.execute(goal_query, (user_id,))
    goal_data = cursor.fetchone()
    if goal_data:
        target_calories = goal_data[0]
    else:
        # Set a default value for target_calories if no goal data is found
        target_calories = 2000

    # Fetch the available food data from the MongoDB collection
    food_data = list(food_collection.find())

    # The number of meals to generate (breakfast, lunch, and dinner)
    num_meals = 3

    # Initialize the meal plan
    meal_plan = {
        'breakfast': [],
        'lunch': [],
        'dinner': []
    }

    # Calculate the rough target calorie range for each meal
    target_calories_per_meal = target_calories / num_meals
    min_calories_per_meal = target_calories_per_meal * 0.8
    max_calories_per_meal = target_calories_per_meal * 1.2

    # Function to calculate the remaining calories for a specific meal
    def calculate_remaining_calories(meal):
        return max_calories_per_meal - sum(float(food['Calories']) for food in meal)

    # Function to randomly select a food item from available_food_items based on calories
    def select_food_item(remaining_calories):
        candidates = [food for food in food_data if float(food['Calories']) <= remaining_calories]

        if candidates:
            selected_food = random.choice(candidates)
            food_data.remove(selected_food)  # Remove the selected food item from the list
            return selected_food
        else:
            return None

    # Generate meal plans for the selected mealTimeframe
    remaining_calories = max_calories_per_meal
    while remaining_calories > 0:
        selected_food = select_food_item(remaining_calories)

        if selected_food:
            meal_plan[meal_timeframe.lower()].append(selected_food)
            remaining_calories = calculate_remaining_calories(meal_plan[meal_timeframe.lower()])
        else:
            # If there are no more suitable food items, break the loop
            break

    # Convert the MongoDB document to a Python dictionary
    meal_plan_data_dict = {
        'mealTimeframe': meal_timeframe,
        'mealPlan': meal_plan[meal_timeframe.lower()]
    }


    # Convert the data to JSON format
    meal_plan_json = json.dumps(meal_plan_data_dict, default=str)

    return meal_plan_json

@app.route('/')
@login_required
def home():
    # Get the current date
    today = date.today()
    food_data = list(food_collection.find())
    exercise_data = list(exercise_collection.find())
    user = session.get('user')
    user_id = user['id']

    actual_meal_query = """
        SELECT dp.daily_plan_id, dp.goal_id, dp.date, dp.net_calories,
               m.calories_gained, m.food_name, m.meal_timeframe, m.meal_id, g.goal_name, g.target_calories
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
                'exercises': [],
                'goal_name': row[8],
                'target_calories': row[9]
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

    # Function to round calorie values to 2 decimal places
    def round_calories(value):
        return round(value, 2)

    # Round the calorie values in the daily_plans dictionary
    for plan in daily_plans:
        plan['net_calories'] = round_calories(plan['net_calories'])

        for meal_list in [plan['breakfast_meals'], plan['lunch_meals'], plan['dinner_meals']]:
            for meal in meal_list:
                meal['calories_gained'] = round_calories(meal['calories_gained'])

        for exercise in plan['exercises']:
            exercise['calories_burnt'] = round_calories(exercise['calories_burnt'])

    return render_template('home.html', user=user, daily_plans=daily_plans, food_data=food_data, exercise_data=exercise_data, today=today)




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
    activity = request.form['activity']
    calories_burnt = float(request.form['caloriesBurnt'])
    daily_plan_id = int(request.form.get('dailyPlanId'))
    # NEED TO CHANGE, IDK WHAT IS EXERCISE TYPE FOR
    exercise_type = 'placeholder'
    description = request.form['description']
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
    exercise_type = 'placeholder'
    activity = request.form['editActivity']
    description = request.form['editDescription']
    calories_burnt = float(request.form['editCaloriesBurnt'])
    # daily_plan_id = int(request.form['editDailyPlanId'])

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

@app.route('/add_food_item', methods=['POST'])
@login_required
def add_food_item():
    # Get the form data from the POST request
    food_name = request.form.get('foodName')
    food_measure = request.form.get('foodMeasure')
    food_grams = float(request.form.get('foodGrams'))
    food_calories = float(request.form.get('foodCalories'))
    food_protein = float(request.form.get('foodProtein'))
    food_fat = float(request.form.get('foodFat'))
    food_satfat = float(request.form.get('foodSatfat'))
    food_fiber = float(request.form.get('foodFiber'))
    food_carbs = float(request.form.get('foodCarbs'))
    food_category = request.form.get('foodCategory')
    food_item = {
        'Food': food_name,
        'Measure': food_measure,
        'Grams': food_grams,
        'Calories': food_calories,
        'Protein': food_protein,
        'Fat': food_fat,
        'SatFat': food_satfat,
        'Fiber': food_fiber,
        'Carbs': food_carbs,
        'Category': food_category
    }
    food_collection.insert_one(food_item)
    return redirect('/food')

@app.route('/update_food_item', methods=['POST'])
@login_required
def update_food_item():
    # Get the form data from the POST request
    food_name = request.form.get('foodNameUp')
    food_measure = request.form.get('foodMeasureU')
    food_grams = float(request.form.get('foodGramsU'))
    food_calories = float(request.form.get('foodCaloriesU'))
    food_protein = float(request.form.get('foodProteinU'))
    food_fat = float(request.form.get('foodFatU'))
    food_satfat = float(request.form.get('foodSatfatU'))
    food_fiber = float(request.form.get('foodFiberU'))
    food_carbs = float(request.form.get('foodCarbsU'))
    food_category = request.form.get('foodCategoryU')

    # Find the food item in the database based on the unique identifier
    existing_food_item = food_collection.find_one({'Food': food_name})

    if existing_food_item:
        # Update the food item data
        existing_food_item['Measure'] = food_measure
        existing_food_item['Grams'] = food_grams
        existing_food_item['Calories'] = food_calories
        existing_food_item['Protein'] = food_protein
        existing_food_item['Fat'] = food_fat
        existing_food_item['SatFat'] = food_satfat
        existing_food_item['Fiber'] = food_fiber
        existing_food_item['Carbs'] = food_carbs
        existing_food_item['Category'] = food_category

        # Update the document in the database
        food_collection.update_one({'Food': food_name}, {'$set': existing_food_item})

        return redirect('/food')
    else:
    # Return an error response to the client
        return jsonify({'error': 'Food item not found.'}), 404

@app.route('/delete_food_item', methods=['POST'])
@login_required
def delete_food_item():
    # Get the form data from the POST request
    food_name = request.form.get('foodNameU')
    # Find the food item in the database based on the unique identifier (food_name)
    existing_food_item = food_collection.find_one({'Food': food_name})

    if existing_food_item:
        # Delete the food item from the database
        food_collection.delete_one({'Food': food_name})
        return jsonify({'message': 'Food item deleted successfully.'})
    else:
        # Return an error response to the client
        return jsonify({'error': 'Food item not found.'}), 404
    
@app.route('/exercise')
@login_required
def exercise():
    # Retrieve the data from the 'exercise' collection
    exercise_data = exercise_collection.find()

    user = session.get('user')  # Retrieve the user data from the session

    # Pass the data to the template
    return render_template('exercise.html', exercise_data=exercise_data, user=user)

@app.route('/add_exercise_item', methods=['POST'])
@login_required
def add_exercise_item():
    # Get the form data from the POST request
    exercise_activity = request.form.get('exerciseActivity')
    exercise_calories_130 = float(request.form.get('exerciseCalories130'))
    exercise_calories_155 = float(request.form.get('exerciseCalories155'))
    exercise_calories_180 = float(request.form.get('exerciseCalories180'))
    exercise_calories_205 = float(request.form.get('exerciseCalories205'))
    exercise_calories_per_kg = float(request.form.get('exerciseCaloriesPerKg'))

    exercise_item = {
        'Activity': exercise_activity,
        '130 lb': exercise_calories_130,
        '155 lb': exercise_calories_155,
        '180 lb': exercise_calories_180,
        '205 lb': exercise_calories_205,
        'Calories per kg': exercise_calories_per_kg
    }

    exercise_collection.insert_one(exercise_item)
    return redirect('/exercise')

@app.route('/update_exercise_item', methods=['POST'])
@login_required
def update_exercise_item():
    # Get the form data from the POST request
    exercise_activity = request.form.get('exerciseActivityUp')
    exercise_lb130 = float(request.form.get('exercise130lbU'))
    exercise_lb155 = float(request.form.get('exercise155lbU'))
    exercise_lb180 = float(request.form.get('exercise180lbU'))
    exercise_lb205 = float(request.form.get('exercise205lbU'))
    exercise_calories_per_kg = float(request.form.get('exerciseCaloriesPerKgU'))
    
    # Find the exercise item in the database based on the unique identifier
    existing_exercise_item = exercise_collection.find_one({'Activity': exercise_activity})
    if existing_exercise_item:
        # Update the exercise item data
        existing_exercise_item['Activity'] = exercise_activity
        existing_exercise_item['130 lb'] = exercise_lb130
        existing_exercise_item['155 lb'] = exercise_lb155
        existing_exercise_item['180 lb'] = exercise_lb180
        existing_exercise_item['205 lb'] = exercise_lb205
        existing_exercise_item['Calories per kg'] = exercise_calories_per_kg
        
        # Update the document in the database
        exercise_collection.update_one({'Activity': exercise_activity}, {'$set': existing_exercise_item})
        return redirect('/exercise')

@app.route('/delete_exercise_item', methods=['POST'])
@login_required
def delete_exercise_item():
    # Get the form data from the POST request
    exercise_activity = request.form.get('exerciseActivityU')
    # Find the exercise item in the database based on the unique identifier (exercise_activity)
    existing_exercise_item = exercise_collection.find_one({'Activity': exercise_activity})

    if existing_exercise_item:
        # Delete the exercise item from the database
        exercise_collection.delete_one({'Activity': exercise_activity})
        return jsonify({'message': 'Exercise item deleted successfully.'})
    else:
        # Return an error response to the client
        return jsonify({'error': 'Exercise item not found.'}), 404

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

    # Call the function to update daily plans
    update_daily_plans(goal_id, start_date, end_date, target_calories)

    return redirect('/goal')


def update_daily_plans(goal_id, new_start_date, new_end_date, target_calories):
    # Convert new_start_date and new_end_date to datetime.date objects
    new_start_date = datetime.strptime(new_start_date, '%Y-%m-%d').date()
    new_end_date = datetime.strptime(new_end_date, '%Y-%m-%d').date()

    # Retrieve the associated daily plans from the database
    get_daily_plans_query = "SELECT daily_plan_id, date FROM daily_plan WHERE goal_id = %s"
    cursor.execute(get_daily_plans_query, (goal_id,))
    daily_plans = cursor.fetchall()

    # Create a set of existing plan dates for easier comparison
    existing_dates = set(plan[1] for plan in daily_plans)

    # Delete any daily plans that fall outside the new goal range
    for plan in daily_plans:
        plan_date = plan[1]
        if plan_date < new_start_date or plan_date > new_end_date:
            delete_plan_query = "DELETE FROM daily_plan WHERE daily_plan_id = %s"
            cursor.execute(delete_plan_query, (plan[0],))
            db_mysql.commit()

    # Add new daily plans for the extended range if necessary
    current_date = new_start_date
    while current_date <= new_end_date:
        if current_date not in existing_dates:
            # Create a new daily plan
            create_plan_query = "INSERT INTO daily_plan (goal_id, date, net_calories) VALUES (%s, %s, 0)"
            cursor.execute(create_plan_query, (goal_id, current_date))
            db_mysql.commit()
        current_date += timedelta(days=1)


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
    user = session.get('user')

    user_id = user['id']

    # Retrieve the filter parameters from the URL query parameters
    goal_name_filter = request.args.get('goal_name')
    date_filter = request.args.get('date')
    net_calories_filter = request.args.get('net_calories_filter')

    actual_meal_query = """
        SELECT dp.daily_plan_id, dp.goal_id, dp.date, dp.net_calories,
               m.calories_gained, m.food_name, m.meal_timeframe, m.meal_id,
               g.goal_name, g.target_calories
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

    goal_query = """
        SELECT DISTINCT goal_name
        FROM goals
        WHERE user_id = %s
    """

    values = (user_id,)

    # Modify the actual_meal_query based on the filter parameters
    if goal_name_filter:
        actual_meal_query += " AND g.goal_name = %s"
        exercise_query += " AND g.goal_name = %s"
        values += (goal_name_filter,)

    if date_filter:
        actual_meal_query += " AND dp.date = %s"
        exercise_query += " AND dp.date = %s"
        values += (date_filter,)

    # Add the comparison filters for net calories
    if net_calories_filter == "higher":
        actual_meal_query += " AND dp.net_calories > (SELECT AVG(net_calories) FROM daily_plan)"
        exercise_query += " AND dp.net_calories > (SELECT AVG(net_calories) FROM daily_plan)"
    elif net_calories_filter == "lower":
        actual_meal_query += " AND dp.net_calories < (SELECT AVG(net_calories) FROM daily_plan)"
        exercise_query += " AND dp.net_calories < (SELECT AVG(net_calories) FROM daily_plan)"

    cursor.execute(actual_meal_query, values)
    rows1 = cursor.fetchall()

    cursor.execute(exercise_query, values)
    rows2 = cursor.fetchall()

    cursor.execute(goal_query, (user_id,))
    rows3 = cursor.fetchall()

    daily_plans = {}
    for row in rows1:
        daily_plan_id = row[0]  # Access the column value by index
        if daily_plan_id not in daily_plans:
            daily_plans[daily_plan_id] = {
                'id': daily_plan_id,
                'goal_id': row[1],  # Access the column value by index
                'date': row[2],  # Access the column value by index
                'net_calories': row[3],  # Access the column value by index
                'goal_name': row[8],  # Access the goal_name column value by index
                'target_calories': row[9],  # Access the target_calories column value by index
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

    goal_names = [row[0] for row in rows3]

    daily_plans = list(daily_plans.values())

    return render_template('dailyplan.html', user=user, daily_plans=daily_plans, goal_names=goal_names,
                           selected_goal=goal_name_filter, selected_date=date_filter, net_calories_filter=net_calories_filter)


    
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
    new_password = request.form['new_password']  # New password field

    # Update the user's profile data in the session
    user = session.get('user')
    if user:
        user['name'] = name
        user['email'] = email
        user['height'] = height
        user['weight'] = weight

    # Check if the user provided a new password and update it in the database
    if new_password:
        hashed_password = generate_password_hash(new_password)
        update_password_query = "UPDATE users SET password = %s WHERE user_id = %s"
        values = (hashed_password, user['id'])
        cursor.execute(update_password_query, values)
        db_mysql.commit()
        flash('Password updated successfully', 'success')

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


if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)
