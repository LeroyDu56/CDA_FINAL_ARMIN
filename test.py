import requests
import time
import math

# Configuration : modifiez ces valeurs selon votre environnement
INFLUX_URL = "http://localhost:8086"
ORG = "armin"            # Nom de l'organisation défini dans InfluxDB 2
BUCKET = "armin_supervision"      # Nom du bucket défini dans InfluxDB 2
TOKEN = "9k4bMDtTBr22EvjBPv4UP3cIsKaz_qTSMhaJpeInxF7HeT6TmSQMXd1YJmdXnG-D1FzaBYREm5aEMerivjbkdA=="  # Remplacez par votre token API InfluxDB 2

# Construction de l'URL d'écriture
write_url = f"{INFLUX_URL}/api/v2/write?org={ORG}&bucket={BUCKET}&precision=s"

# Headers HTTP
headers = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "text/plain; charset=utf-8"
}

print("Début de l'envoi de données sinusoïdales...")

# Paramètres pour la sinusoïde
period = 60  # période en secondes
base_value = 50  # valeur de base
amplitude = 20   # amplitude de la variation

while True:
    # Obtenir le timestamp actuel (en secondes)
    timestamp = int(time.time())
    # Calculer l'angle en fonction du temps (modulo période)
    angle = 2 * math.pi * (timestamp % period) / period
    # Calculer la valeur sinusoïdale
    value = base_value + amplitude * math.sin(angle)
    
    # Créer la donnée en line protocol
    # Exemple : mesure "sinus", tag "location=room1", champ "value"
    data = f"sinus,location=room1 value={value} {timestamp}"
    
    # Envoyer la donnée via une requête POST
    try:
        response = requests.post(write_url, headers=headers, data=data)
        if response.status_code == 204:
            print(f"[{timestamp}] Valeur envoyée: {value:.2f}")
        else:
            print(f"[{timestamp}] Erreur HTTP: {response.status_code}, réponse: {response.text}")
    except Exception as e:
        print(f"[{timestamp}] Exception: {e}")
    
    # Pause d'une seconde avant d'envoyer la prochaine donnée
    time.sleep(5)
