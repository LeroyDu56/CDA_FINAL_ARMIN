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
    """
    Récupère l'état de connexion de tous les hôtes.

    Returns:
        dict: Dictionnaire {host_name: is_active} où is_active est un booléen
              indiquant si l'hôte a envoyé des données dans les 5 dernières secondes.
    """
    logger.info("Récupération de l'état des hôtes.")
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

def get_host_ip_info(host=None):
    """
    Récupère les adresses IP des hôtes à partir de la mesure host_ip.
    
    Args:
        host (str, optional): Nom d'hôte spécifique à rechercher. Si None, récupère pour tous les hôtes.
        
    Returns:
        dict: Dictionnaire {host_name: {'ip': ip_address}} avec les adresses IP des hôtes.
    """
    try:
        with _get_influx_client() as client:
            query_api = client.query_api()

            # Construire la requête en fonction de si un hôte spécifique est demandé
            host_filter = f'and r.host == "{host}"' if host else ''

            # 1. Récupérer tous les hôtes connus
            query_all_hosts = f'''
            from(bucket: "{settings.INFLUXDB_BUCKET}")
            |> range(start: -1d)
            |> filter(fn: (r) => r._measurement == "cpu" {host_filter})
            |> group(columns: ["host"])
            |> distinct(column: "host")
            '''

            all_hosts = set()
            try:
                tables_all_hosts = query_api.query(org=settings.INFLUXDB_ORG, query=query_all_hosts)
                for table in tables_all_hosts:
                    for record in table.records:
                        host_name = record.values.get("host", "")
                        if host_name:
                            all_hosts.add(host_name)
            except Exception as e:
                logger.error(f"Erreur lors de la récupération de tous les hôtes: {e}")
                # Utiliser une liste prédéfinie si la requête échoue
                all_hosts = {"VM1telegraf", "VM2telegraf"}

            # 2. Récupérer les adresses IP à partir de la mesure host_ip
            query_host_ip = f'''
            from(bucket: "{settings.INFLUXDB_BUCKET}")
            |> range(start: -1d)
            |> filter(fn: (r) => r._measurement == "host_ip" {host_filter})
            |> last()
            '''

            ip_info = {}
            hosts_with_ip = set()

            try:
                tables_host_ip = query_api.query(org=settings.INFLUXDB_ORG, query=query_host_ip)
                for table in tables_host_ip:
                    for record in table.records:
                        host_name = record.values.get("host", "")
                        ip_addresses = record.values.get("_value", "")
                        if host_name and ip_addresses:
                            hosts_with_ip.add(host_name)
                            # Prendre la première adresse IP (si plusieurs)
                            first_ip = ip_addresses.split()[0]
                            ip_info[host_name] = {'ip': first_ip}
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des adresses IP: {e}")

            # 3. Pour les hôtes sans adresse IP, utiliser "Non spécifiée"
            for host_name in all_hosts:
                if host_name not in ip_info:
                    ip_info[host_name] = {'ip': "Non spécifiée"}

            # Si un hôte spécifique était demandé mais n'a pas été trouvé
            if host and host not in ip_info:
                ip_info[host] = {'ip': "Non spécifiée"}

            return ip_info

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des adresses IP: {e}")
        if host:
            return {host: {'ip': "Non spécifiée"}}
        return {}