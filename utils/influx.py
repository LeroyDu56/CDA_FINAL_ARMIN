# auth_app/influx.py
from influxdb_client import InfluxDBClient
from django.conf import settings
from datetime import datetime, timezone
from auth_app.models import ServiceTask, HostIpMapping
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
    Récupère l'état de connexion de tous les hôtes en vérifiant explicitement le timestamp
    de la dernière donnée reçue.
    """
    # Import ici pour éviter les imports circulaires
    from auth_app.models import HostIpMapping, ServiceTask, HostContact
    from datetime import datetime, timezone, timedelta
    
    logger.info("Récupération de l'état des hôtes.")
    try:
        with _get_influx_client() as client:
            query_api = client.query_api()
            
            # Utiliser le bucket configuré
            bucket = settings.INFLUXDB_BUCKET
            
            # Récupérer tous les hosts avec leur dernier timestamp
            query = f'''
            from(bucket: "{bucket}")
            |> range(start: -30d)
            |> filter(fn: (r) => r._measurement == "cpu")
            |> group(columns: ["host"])
            |> last()
            '''

            tables = query_api.query(org=settings.INFLUXDB_ORG, query=query)

            host_status = {}
            now_utc = datetime.now(timezone.utc)
            
            # Dictionnaire pour stocker les informations d'IP détectées automatiquement
            auto_hosts_ips = {}
            
            for table in tables:
                for record in table.records:
                    host_name = record.values["host"]
                    last_time = record.values["_time"]
                    
                    # Calculer la différence de temps
                    time_diff = now_utc - last_time
                    
                    # Un hôte est actif s'il a envoyé des données au cours des 30 dernières secondes
                    is_active = time_diff.total_seconds() < 30
                    
                    # Log pour le débogage
                    logger.info(f"Hôte: {host_name}, Dernière connexion: {last_time}, Actif: {is_active}, Différence: {time_diff.total_seconds()} secondes")
                    
                    host_status[host_name] = is_active
                    
                    # Sauvegarder ou mettre à jour l'hôte dans la base de données
                    host_mapping, created = HostIpMapping.objects.get_or_create(
                        host=host_name,
                        defaults={
                            'ip_address': "Non spécifiée",
                            'is_manual': False  # Marquer comme hôte automatique
                        }
                    )
                    
                    # Si l'hôte existait déjà et était manuel, le marquer comme automatique
                    if not created and host_mapping.is_manual:
                        host_mapping.is_manual = False
                        host_mapping.save()
                        
            # Maintenant, récupérons les IP pour tous les hôtes automatiques
            ip_info = get_host_ip_info()
            for host_name, info in ip_info.items():
                if host_name in host_status and info['ip'] != "Non spécifiée":
                    auto_hosts_ips[info['ip']] = host_name
            
            # Vérifions s'il y a des hôtes manuels avec des IPs correspondant à des hôtes automatiques
            manual_hosts = HostIpMapping.objects.filter(is_manual=True)
            for manual_host in manual_hosts:
                if manual_host.ip_address in auto_hosts_ips:
                    auto_host_name = auto_hosts_ips[manual_host.ip_address]
                    
                    # Vérifier que les noms sont différents
                    if manual_host.host != auto_host_name:
                        try:
                            logger.info(f"Tentative de remplacement de l'hôte manuel {manual_host.host} par l'hôte automatique {auto_host_name}")
                            
                            # Transférer les informations client
                            manual_tasks = ServiceTask.objects.filter(host=manual_host.host)
                            for task in manual_tasks:
                                # Créer une tâche équivalente pour l'hôte automatique
                                ServiceTask.objects.get_or_create(
                                    host=auto_host_name,
                                    title=task.title,
                                    defaults={
                                        'description': task.description,
                                        'priority': task.priority,
                                        'status': task.status,
                                        'client': task.client
                                    }
                                )
                            
                            # Transférer les contacts
                            manual_contact = HostContact.objects.filter(host=manual_host.host).first()
                            if manual_contact:
                                HostContact.objects.update_or_create(
                                    host=auto_host_name,
                                    defaults={
                                        'contact_name': manual_contact.contact_name,
                                        'contact_email': manual_contact.contact_email,
                                        'contact_phone': manual_contact.contact_phone
                                    }
                                )
                            
                            # Supprimer l'hôte manuel et ses données associées
                            manual_tasks.delete()
                            if manual_contact:
                                manual_contact.delete()
                            manual_host.delete()
                            
                            logger.info(f"Hôte manuel {manual_host.host} remplacé avec succès par {auto_host_name}")
                            
                        except Exception as e:
                            logger.error(f"Erreur lors du remplacement de l'hôte manuel: {e}")

            # Ajouter les hôtes manuels au dictionnaire de statut
            for manual_host in HostIpMapping.objects.filter(is_manual=True):
                if manual_host.host not in host_status:
                    host_status[manual_host.host] = False  # Les hôtes manuels sont toujours inactifs
                    
            return host_status

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statuts des hôtes: {e}")
        
        # En cas d'erreur avec InfluxDB, utiliser les hôtes de la base de données
        try:
            host_status = {}
            db_hosts = HostIpMapping.objects.all()
            for host_mapping in db_hosts:
                # Tous les hôtes seront marqués comme inactifs
                host_status[host_mapping.host] = False
            return host_status
        except Exception as db_error:
            logger.error(f"Erreur également lors de la récupération des hôtes depuis la base de données: {db_error}")
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
    Récupère les adresses IP des hôtes avec persistance.
    Utilise les adresses IP stockées en base de données et ne les met à jour
    que si une nouvelle adresse IP différente est détectée.
    
    Args:
        host (str, optional): Nom d'hôte spécifique à rechercher. Si None, récupère pour tous les hôtes.
        
    Returns:
        dict: Dictionnaire {host_name: {'ip': ip_address}} avec les adresses IP des hôtes.
    """
    # Import ici pour éviter les imports circulaires
    from auth_app.models import HostIpMapping
    
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

            # 2. Récupérer les adresses IP depuis InfluxDB
            query_host_ip = f'''
            from(bucket: "{settings.INFLUXDB_BUCKET}")
            |> range(start: -1d)
            |> filter(fn: (r) => r._measurement == "host_ip" {host_filter})
            |> last()
            '''

            influx_ip_info = {}
            
            try:
                tables_host_ip = query_api.query(org=settings.INFLUXDB_ORG, query=query_host_ip)
                for table in tables_host_ip:
                    for record in table.records:
                        host_name = record.values.get("host", "")
                        ip_addresses = record.values.get("_value", "")
                        if host_name and ip_addresses:
                            # Prendre la première adresse IP (si plusieurs)
                            first_ip = ip_addresses.split()[0]
                            influx_ip_info[host_name] = first_ip
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des adresses IP depuis InfluxDB: {e}")
            
            # 3. Construire le résultat final en combinant les données de base de données et InfluxDB
            result = {}
            
            for host_name in all_hosts:
                # Étape 1: Récupérer l'enregistrement de la base de données (ou en créer un nouveau)
                host_mapping, created = HostIpMapping.objects.get_or_create(
                    host=host_name,
                    defaults={'ip_address': "Non spécifiée"}
                )
                
                # Étape 2: Vérifier si nous avons une nouvelle IP depuis InfluxDB
                if host_name in influx_ip_info:
                    new_ip = influx_ip_info[host_name]
                    # Mettre à jour l'IP stockée uniquement si elle est différente de l'actuelle
                    if new_ip != host_mapping.ip_address and new_ip:
                        host_mapping.ip_address = new_ip
                        host_mapping.save()
                        logger.info(f"IP mise à jour pour {host_name}: {new_ip}")
                
                # Étape 3: Utiliser l'IP de la base de données (qu'elle soit nouvelle ou existante)
                result[host_name] = {'ip': host_mapping.ip_address if host_mapping.ip_address else "Non spécifiée"}
            
            # Si un hôte spécifique était demandé mais n'a pas été trouvé
            if host and host not in result:
                # Vérifier si nous avons cet hôte en base de données
                host_mapping = HostIpMapping.objects.filter(host=host).first()
                if host_mapping:
                    result[host] = {'ip': host_mapping.ip_address if host_mapping.ip_address else "Non spécifiée"}
                else:
                    result[host] = {'ip': "Non spécifiée"}

            return result

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des adresses IP: {e}")
        
        # En cas d'erreur, essayer de récupérer les données depuis la base de données
        try:
            result = {}
            
            if host:
                # Recherche d'un hôte spécifique
                host_mapping = HostIpMapping.objects.filter(host=host).first()
                if host_mapping:
                    result[host] = {'ip': host_mapping.ip_address if host_mapping.ip_address else "Non spécifiée"}
                else:
                    result[host] = {'ip': "Non spécifiée"}
            else:
                # Récupération de tous les hôtes
                host_mappings = HostIpMapping.objects.all()
                for mapping in host_mappings:
                    result[mapping.host] = {'ip': mapping.ip_address if mapping.ip_address else "Non spécifiée"}
            
            return result
        except Exception as db_error:
            logger.error(f"Erreur également lors de la récupération des adresses IP depuis la base de données: {db_error}")
            if host:
                return {host: {'ip': "Non spécifiée"}}
            return {}