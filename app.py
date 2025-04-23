from flask import Flask, flash, redirect, render_template, request, session, url_for
import os
import numpy as np
from keras.models import load_model
import sqlite3
import pickle

# === Load the trained model ===
with open("lcmodel.pickle", "rb") as f:
    model = pickle.load(f)

# === Initialize the database (creates table if not exists) ===
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Health data table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS health_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        gender INTEGER,
        age INTEGER,
        smoking INTEGER,
        yellow_fingers INTEGER,
        anxiety INTEGER,
        peer_pressure INTEGER,
        chronic_disease INTEGER,
        fatigue INTEGER,
        allergy INTEGER,
        wheezing INTEGER,
        alcohol_consuming INTEGER,
        coughing INTEGER,
        shortness_of_breath INTEGER,
        swallowing_difficulty INTEGER,
        chest_pain INTEGER
    )
    """)

    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()

# === Flask app setup ===
app = Flask(__name__)
app.secret_key = os.urandom(12)
init_db()  # Run database initialization

@app.route('/')
def home():
    if not session.get('logged_in'):
        return redirect('/login')
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def do_admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['logged_in'] = True
            return redirect('/')
        else:
            flash('Invalid credentials.')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            flash('User already exists.')
        else:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            flash('Account created. You can now log in.')

        conn.close()
        return redirect('/login')

    return render_template('signup.html')

@app.route('/logout')
def logout():
    session['logged_in'] = False
    return redirect('/login')

@app.route('/form')
def form():
    return render_template('main.html')

@app.route('/predict', methods=['POST'])
def predict():
    try:
        form = request.form
        gender = 1 if form['gender'].lower() == 'male' else 0

        # Extract and convert remaining fields
        fields = ['age', 'smoking', 'yellow_fingers', 'anxiety', 'peer_pressure',
                  'chronic_disease', 'fatigue', 'allergy', 'wheezing',
                  'alcohol_consuming', 'coughing', 'shortness_of_breath',
                  'swallowing_difficulty', 'chest_pain']
        data = [int(form[field]) for field in fields]
        all_features = [gender] + data

        # Save input to the database
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO health_data (
                gender, age, smoking, yellow_fingers, anxiety,
                peer_pressure, chronic_disease, fatigue, allergy,
                wheezing, alcohol_consuming, coughing,
                shortness_of_breath, swallowing_difficulty, chest_pain
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, all_features)
        conn.commit()
        conn.close()

        # Make prediction with the model
        features = np.array([all_features])
        prediction = model.predict(features)
        result = "🟥 High risk of lung cancer" if prediction[0] == 1 else "🟩 Low risk of lung cancer"

        return render_template('prediction.html', result=result)

    except Exception as e:
        return f"Prediction error: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=4000)
