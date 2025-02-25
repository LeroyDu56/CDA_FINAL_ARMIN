# auth_app/influx.py
from influxdb_client import InfluxDBClient
from django.conf import settings
from datetime import datetime, timedelta, timezone

def get_hosts_status():
    # Récupérer les valeurs depuis settings.py
    url = settings.INFLUXDB_URL
    token = settings.INFLUXDB_TOKEN
    org = settings.INFLUXDB_ORG
    bucket = settings.INFLUXDB_BUCKET
    
    client = InfluxDBClient(url=url, token=token, org=org)
    query_api = client.query_api()
    
    # Requête unique pour grouper par host et prendre le dernier point
    # (exemple avec la mesure "cpu" ; adaptez si besoin)
    query = f'''
     from(bucket: "{bucket}")
     |> range(start: -7d)
     |> filter(fn: (r) => r._measurement == "cpu")
     |> group(columns: ["host"])
     |> last()
     '''
    
    tables = query_api.query(org=org, query=query)
    
    # On veut récupérer _time et host
    host_status = {}
    now_utc = datetime.now(timezone.utc)
    
    for table in tables:
        for record in table.records:
            host_name = record.values["host"]
            last_time = record.values["_time"]  # C'est un datetime en UTC
            # Vérifier si la différence est < 30s
            delta = now_utc - last_time
            is_fresh = (delta.total_seconds() < 30)
            # Stocker l'info
            host_status[host_name] = is_fresh
    
    client.close()
    return host_status

def get_last_connection_time(host):
    """
    Récupère la date/heure de la dernière connexion d'un hôte depuis InfluxDB
    
    Args:
        host (str): Le nom de l'hôte
        
    Returns:
        datetime ou None: Le timestamp de la dernière connexion ou None si aucune donnée
    """
    # Récupérer les valeurs depuis settings.py
    url = settings.INFLUXDB_URL
    token = settings.INFLUXDB_TOKEN
    org = settings.INFLUXDB_ORG
    bucket = settings.INFLUXDB_BUCKET
    
    try:
        client = InfluxDBClient(url=url, token=token, org=org)
        query_api = client.query_api()
        
        # Requête pour obtenir le dernier point de données pour cet hôte
        query = f'''
        from(bucket: "{bucket}")
          |> range(start: -30d)
          |> filter(fn: (r) => r._measurement == "cpu" and r.host == "{host}")
          |> group(columns: ["host"])
          |> last()
        '''
        
        tables = query_api.query(org=org, query=query)
        
        # Extraire le timestamp du résultat
        for table in tables:
            for record in table.records:
                client.close()
                return record.values["_time"]  # Retourne le datetime de la dernière connexion
        
        client.close()
        return None  # Aucune donnée trouvée
    except Exception as e:
        print(f"Erreur lors de la récupération de la dernière connexion: {e}")
        return None