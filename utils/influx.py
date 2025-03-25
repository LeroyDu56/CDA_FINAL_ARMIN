# auth_app/influx.py
from influxdb_client import InfluxDBClient
from django.conf import settings
from datetime import datetime, timezone
import logging

# Configuration du logger
logger = logging.getLogger(__name__)

def _get_influx_client():
    """
    Crée et retourne un client InfluxDB avec les paramètres de configuration.
    """
    return InfluxDBClient(
        url=settings.INFLUXDB_URL,
        token=settings.INFLUXDB_TOKEN,
        org=settings.INFLUXDB_ORG
    )

def get_hosts_status():
    logger.info("Récupération de l'état des hôtes.")
    """
    Récupère l'état de connexion de tous les hôtes.

    Returns:
        dict: Dictionnaire {host_name: is_active} où is_active est un booléen
              indiquant si l'hôte a envoyé des données dans les 5 dernières secondes.
    """
    try:
        with _get_influx_client() as client:
            query_api = client.query_api()

            query = f'''
            from(bucket: "{settings.INFLUXDB_BUCKET}")
            |> range(start: -7d)
            |> filter(fn: (r) => r._measurement == "cpu")
            |> group(columns: ["host"])
            |> last()
            '''

            tables = query_api.query(org=settings.INFLUXDB_ORG, query=query)

            host_status = {}
            now_utc = datetime.now(timezone.utc)

            for table in tables:
                for record in table.records:
                    host_name = record.values["host"]
                    last_time = record.values["_time"]
                    is_fresh = (now_utc - last_time).total_seconds() < 30
                    host_status[host_name] = is_fresh

            return host_status

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statuts des hôtes: {e}")
        logger.error(f"Erreur lors de la récupération des statuts des hôtes: {e}")
        return {}

def get_last_connection_time(host):
    """
    Récupère la date/heure de la dernière connexion d'un hôte depuis InfluxDB.

    Args:
        host (str): Le nom de l'hôte

    Returns:
        datetime ou None: Le timestamp de la dernière connexion ou None si aucune donnée
    """
    try:
        with _get_influx_client() as client:
            query_api = client.query_api()

            query = f'''
            from(bucket: "{settings.INFLUXDB_BUCKET}")
            |> range(start: -30d)
            |> filter(fn: (r) => r._measurement == "cpu" and r.host == "{host}")
            |> group(columns: ["host"])
            |> last()
            '''

            tables = query_api.query(org=settings.INFLUXDB_ORG, query=query)

            for table in tables:
                for record in table.records:
                    return record.values["_time"]

            return None  # Aucune donnée trouvée

    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la dernière connexion pour {host}: {e}")
        return None
