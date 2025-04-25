from django.test import TestCase
from auth_app.models import HostIpMapping

class HostIpMappingTest(TestCase):
    def test_create_and_update_host(self):
        # Création d'un mapping host-IP
        host = HostIpMapping.objects.create(
            host="test-robot",
            ip_address="192.168.1.100",
            is_manual=True
        )
        
        # Vérification des attributs
        self.assertEqual(host.host, "test-robot")
        self.assertEqual(host.ip_address, "192.168.1.100")
        self.assertTrue(host.is_manual)
        
        # Test de mise à jour
        host.ip_address = "192.168.1.101"
        host.save()
        self.assertEqual(host.ip_address, "192.168.1.101")