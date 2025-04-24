from flask import Flask, flash, redirect, render_template, request, session, url_for
import os
import numpy as np
import sqlite3
import pickle
import logging
from logging.handlers import RotatingFileHandler
from werkzeug.security import generate_password_hash, check_password_hash

# === Configuration de l'application ===
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(12))

# === Configuration du logging ===
def setup_logging():
    logging.basicConfig(level=logging.INFO)
    handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=3)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)

setup_logging()

# === Initialisation de la base de données ===
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Table des données de santé
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

    # Table des utilisateurs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()

# === Chargement du modèle ===
try:
    with open("lcmodel.pickle", "rb") as f:
        model = pickle.load(f)
    app.logger.info("Modèle chargé avec succès")
except Exception as e:
    app.logger.error(f"Erreur lors du chargement du modèle : {str(e)}")
    raise

# Initialisation de la base de données
init_db()

# === Routes ===
@app.route('/')
def home():
    if not session.get('logged_in'):
        return redirect('/login')
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def do_admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Veuillez remplir tous les champs.')
            return redirect('/login')

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[0], password):
            session['logged_in'] = True
            app.logger.info(f"Utilisateur {username} connecté")
            return redirect('/')
        else:
            flash('Identifiants invalides.')
            app.logger.warning(f"Tentative de connexion échouée pour {username}")
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Veuillez remplir tous les champs.')
            return redirect('/signup')

        hashed_pw = generate_password_hash(password)
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
            conn.commit()
            flash('Compte créé. Vous pouvez maintenant vous connecter.')
            app.logger.info(f"Nouvel utilisateur enregistré : {username}")
        except sqlite3.IntegrityError:
            flash("Ce nom d'utilisateur existe déjà.")
            app.logger.warning(f"Tentative de création d'un compte existant : {username}")
        finally:
            conn.close()
        
        return redirect('/login')

    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    app.logger.info("Utilisateur déconnecté")
    return redirect('/login')

@app.route('/form')
def form():
    if not session.get('logged_in'):
        return redirect('/login')
    return render_template('main.html')

@app.route('/predict', methods=['POST'])
def predict():
    if not session.get('logged_in'):
        return redirect('/login')

    try:
        app.logger.info("Traitement d'une nouvelle prédiction")
        
        # Validation des champs
        required_fields = ['gender', 'age', 'smoking', 'yellow_fingers', 'anxiety',
                         'peer_pressure', 'chronic_disease', 'fatigue', 'allergy',
                         'wheezing', 'alcohol_consuming', 'coughing',
                         'shortness_of_breath', 'swallowing_difficulty', 'chest_pain']
        
        for field in required_fields:
            if field not in request.form:
                raise ValueError(f"Champ manquant : {field}")

        # Préparation des données
        gender = 1 if request.form['gender'].lower() == 'male' else 0
        data = [int(request.form[field]) for field in required_fields[1:]]
        all_features = [gender] + data

        # Enregistrement en base de données
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

        # Prédiction
        features = np.array([all_features])
        prediction = model.predict(features)
        result = "🟥 Risque élevé de cancer du poumon" if prediction[0] == 1 else "🟩 Risque faible de cancer du poumon"

        app.logger.info(f"Prédiction réussie. Résultat : {result}")
        return render_template('prediction.html', result=result)

    except ValueError as e:
        app.logger.warning(f"Erreur de validation : {str(e)}")
        flash(str(e))
        return redirect('/form')
    except Exception as e:
        app.logger.error(f"Erreur de prédiction : {str(e)}", exc_info=True)
        flash("Une erreur s'est produite lors de la prédiction.")
        return redirect('/form')

if __name__ == '__main__':
    app.run(debug=True)
