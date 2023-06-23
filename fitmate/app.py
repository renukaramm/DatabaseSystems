from flask import Flask, render_template, request, redirect

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
 
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # FOR TESING USE "ADMIN" GUYS
        if username == 'admin' and password == 'admin':
            return 'Login successful!'
        else:
            return 'Invalid username or password'
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        dob = request.form['dob']
        height = request.form['height']
        weight = request.form['weight']
                
        return 'Registration successful!'
    
    return render_template('register.html')

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/food')
def food():
    return render_template('food.html')

@app.route('/exercise')
def exercise():
    return render_template('exercise.html')

@app.route('/goal')
def goal():
    return render_template('goal.html')

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
    user = users['user1']  # Retrieve the user data, hange later guys
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
    app.run()
