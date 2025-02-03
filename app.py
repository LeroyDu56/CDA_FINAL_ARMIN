from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_bcrypt import Bcrypt
from db import get_connection

app = Flask(__name__, static_folder='static', template_folder='templates')
bcrypt = Bcrypt(app)

# ============================
# ROUTES DES PAGES HTML
# ============================
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

# ============================
# ROUTE POUR L'INSCRIPTION
# ============================
@app.route('/api/register', methods=['POST'])
def register_user():
    try:
        data = request.form
        email = data.get('email')
        password = data.get('password')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        confirm_password = data.get('confirm_password')

        print(f"📩 Requête reçue avec email: {email}")

        if not email or not password or not first_name or not last_name:
            return jsonify({"message": "Tous les champs sont requis."}), 400

        if password != confirm_password:
            return jsonify({"message": "Les mots de passe ne correspondent pas."}), 400

        conn = get_connection()
        cur = conn.cursor()

        # Vérifier si l'email existe déjà
        cur.execute("SELECT email FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            print("⚠️ Email déjà utilisé")
            return jsonify({"message": "Cet email est déjà enregistré."}), 400

        # Hasher le mot de passe
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        print(f"🔑 Mot de passe haché : {hashed_password}")

        # Insérer l'utilisateur et récupérer l'ID
        cur.execute("INSERT INTO users (email, password_hash, first_name, last_name) VALUES (%s, %s, %s, %s) RETURNING user_id", (email, hashed_password, first_name, last_name))
        new_user = cur.fetchone()
        conn.commit()

        print(f"🛠️ Résultat de l'insertion : {new_user}")

        if new_user is None:
            print("⚠️ RETURNING user_id n'a rien retourné. On va récupérer l'ID manuellement.")
            cur.execute("SELECT user_id FROM users WHERE email = %s", (email,))
            new_user = cur.fetchone()
            print(f"🛠️ ID récupéré via SELECT : {new_user}")

        cur.close()
        conn.close()

        if new_user is None:
            print("🚨 ERREUR: Impossible de récupérer l'ID utilisateur après insertion.")
            return jsonify({"message": "Erreur lors de l'inscription. Impossible de récupérer l'ID."}), 500

        print(f"✅ Utilisateur créé avec succès. ID: {new_user['user_id']}")

        return redirect(url_for('home'))

    except Exception as e:
        print(f"❌ Erreur lors de l'inscription : {e}")
        import traceback
        traceback.print_exc()  # Affiche toute la stack d'erreur
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500

# ============================
# ROUTE POUR LA CONNEXION
# ============================
@app.route('/api/login', methods=['POST'])
def login_user():
    try:
        data = request.form
        email = data.get('email')
        password = data.get('password')

        print(f"📩 Tentative de connexion pour : {email}")

        if not email or not password:
            return jsonify({"message": "Email et mot de passe requis."}), 400

        conn = get_connection()
        cur = conn.cursor()

        # Récupérer l'utilisateur
        cur.execute("SELECT user_id, email, password_hash FROM users WHERE email = %s", (email,))
        user = cur.fetchone()

        if not user:
            print("❌ Identifiants invalides (utilisateur non trouvé)")
            return jsonify({"message": "Identifiants invalides."}), 401

        # Vérifier le mot de passe
        if not bcrypt.check_password_hash(user['password_hash'], password):
            print("❌ Identifiants invalides (mot de passe incorrect)")
            return jsonify({"message": "Identifiants invalides."}), 401

        # Mettre à jour la dernière connexion
        cur.execute("UPDATE users SET last_login = NOW() WHERE user_id = %s", (user['user_id'],))
        conn.commit()

        print(f"✅ Connexion réussie pour {email}")

        cur.close()
        conn.close()

        return redirect(url_for('home'))

    except Exception as e:
        print(f"❌ Erreur lors de la connexion : {e}")
        return jsonify({"message": "Erreur serveur"}), 500

# ============================
# DÉMARRER LE SERVEUR
# ============================
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)
