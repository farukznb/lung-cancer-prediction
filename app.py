from flask import Flask, flash, redirect, render_template, request, session, url_for
import os
import sqlite3
import secrets
import datetime
import smtplib
from email.mime.text import MIMEText
from werkzeug.security import generate_password_hash, check_password_hash
import numpy as np
import pickle

# === Configuration de l'application ===
app = Flask(__name__)
app.secret_key = 'votre_clé_secrète_stable_et_complexe'  # À changer en production !

# Configuration SMTP (exemple pour Gmail)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'votre_email@gmail.com'
app.config['MAIL_PASSWORD'] = 'votre_mot_de_passe_app'

# === Chargement du modèle ===
with open("lcmodel.pickle", "rb") as f:
    model = pickle.load(f)

# === Initialisation de la base de données ===
def init_db():
    try:
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
            password TEXT NOT NULL,
            email TEXT
        )
        """)

        # Table pour réinitialisation de mot de passe
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL UNIQUE,
            expires_at DATETIME NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """)

        conn.commit()
    except sqlite3.Error as e:
        print(f"Erreur DB à l'initialisation: {e}")
    finally:
        conn.close()

# === Routes principales ===
@app.route('/')
def home():
    if not session.get('logged_in'):
        return redirect(url_for('do_admin_login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def do_admin_login():
    if request.method == 'POST':
        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, password FROM users WHERE username = ?",
                (request.form['username'],)
            )
            user = cursor.fetchone()
            
            if user and check_password_hash(user[2], request.form['password']):
                session['logged_in'] = True
                session['user_id'] = user[0]
                session['username'] = user[1]
                flash('Connexion réussie!', 'success')
                return redirect(url_for('home'))
            else:
                flash('Identifiants incorrects', 'danger')
        except sqlite3.Error as e:
            flash('Erreur de base de données', 'danger')
            print(f"Erreur DB: {e}")
        finally:
            conn.close()
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            username = request.form['username'].strip()
            password = generate_password_hash(request.form['password'])
            email = request.form.get('email')  # Optionnel

            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            
            # Vérification de l'existence de l'utilisateur
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                flash('Ce nom d\'utilisateur existe déjà', 'warning')
            else:
                # Création du compte
                cursor.execute(
                    "INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
                    (username, password, email)
                )
                conn.commit()
                flash('Compte créé avec succès!', 'success')
                return redirect(url_for('do_admin_login'))
        except sqlite3.Error as e:
            flash('Erreur lors de la création du compte', 'danger')
            print(f"Erreur DB: {e}")
        finally:
            conn.close()
    
    return render_template('signup.html')

# === Fonctionnalité Mot de passe oublié ===
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email_or_username = request.form['email_or_username']
        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, email FROM users WHERE username = ? OR email = ?",
                (email_or_username, email_or_username)
            )
            user = cursor.fetchone()
            
            if user and user[1]:  # Vérifie que l'email existe
                token = secrets.token_urlsafe(32)
                expires_at = datetime.datetime.now() + datetime.timedelta(hours=1)
                
                cursor.execute(
                    "INSERT INTO password_resets (user_id, token, expires_at) VALUES (?, ?, ?)",
                    (user[0], token, expires_at)
                )
                conn.commit()
                
                send_reset_email(user[1], token)
                flash('Un lien de réinitialisation a été envoyé à votre email.', 'info')
            else:
                flash('Aucun compte trouvé avec ces identifiants ou email non enregistré', 'warning')
        except Exception as e:
            flash('Une erreur est survenue', 'danger')
            print(f"Erreur: {e}")
        finally:
            conn.close()
    
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id FROM password_resets 
            WHERE token = ? AND expires_at > datetime('now')
        """, (token,))
        reset_request = cursor.fetchone()
        
        if not reset_request:
            flash('Lien invalide ou expiré', 'danger')
            return redirect(url_for('forgot_password'))
        
        if request.method == 'POST':
            new_password = generate_password_hash(request.form['new_password'])
            cursor.execute(
                "UPDATE users SET password = ? WHERE id = ?",
                (new_password, reset_request[0])
            )
            cursor.execute(
                "DELETE FROM password_resets WHERE token = ?",
                (token,)
            )
            conn.commit()
            flash('Votre mot de passe a été mis à jour', 'success')
            return redirect(url_for('do_admin_login'))
            
    except Exception as e:
        flash('Une erreur est survenue', 'danger')
        print(f"Erreur: {e}")
    finally:
        conn.close()
    
    return render_template('reset_password.html', token=token)

def send_reset_email(to_email, token):
    reset_url = url_for('reset_password', token=token, _external=True)
    msg = MIMEText(f"""
        <h3>Réinitialisation de mot de passe</h3>
        <p>Cliquez sur ce lien pour réinitialiser votre mot de passe :</p>
        <a href="{reset_url}">{reset_url}</a>
        <p>Ce lien expirera dans 1 heure.</p>
    """, 'html')
    msg['Subject'] = 'Réinitialisation de mot de passe'
    msg['From'] = app.config['MAIL_USERNAME']
    msg['To'] = to_email
    
    try:
        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
    except Exception as e:
        print(f"Erreur d'envoi d'email: {e}")

# === Routes supplémentaires ===
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('do_admin_login'))

@app.route('/form')
def form():
    if not session.get('logged_in'):
        return redirect(url_for('do_admin_login'))
    return render_template('main.html')

@app.route('/predict', methods=['POST'])
def predict():
    if not session.get('logged_in'):
        return redirect(url_for('do_admin_login'))
    
    try:
        gender = 1 if request.form['gender'].lower() == 'male' else 0
        fields = ['age', 'smoking', 'yellow_fingers', 'anxiety', 'peer_pressure',
                 'chronic_disease', 'fatigue', 'allergy', 'wheezing',
                 'alcohol_consuming', 'coughing', 'shortness_of_breath',
                 'swallowing_difficulty', 'chest_pain']
        data = [int(request.form[field]) for field in fields]
        all_features = [gender] + data

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

        features = np.array([all_features])
        prediction = model.predict(features)
        result = "🟥 High risk of lung cancer" if prediction[0] == 1 else "🟩 Low risk of lung cancer"
        
        return render_template('prediction.html', result=result)

    except Exception as e:
        flash(f"Erreur: {str(e)}", 'danger')
        return redirect(url_for('form'))
    finally:
        conn.close()

# === Point d'entrée ===
if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=4000)
