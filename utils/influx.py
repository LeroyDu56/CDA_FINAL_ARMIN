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
