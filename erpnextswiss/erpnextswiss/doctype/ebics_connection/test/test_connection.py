#!/usr/bin/env python3
"""
Tests de connexion EBICS
Test l'établissement et la gestion des connexions
"""

import frappe
import unittest
from datetime import datetime
import time
from typing import Optional

class TestEBICSConnection(unittest.TestCase):
    """Tests de connexion EBICS"""
    
    @classmethod
    def setUpClass(cls):
        """Configuration initiale pour tous les tests"""
        cls.connection_name = "Raiffeisen"
        cls.connection = None
        cls.client = None
        
    def setUp(self):
        """Configuration avant chaque test"""
        from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
        
        self.connection = frappe.get_doc("ebics Connection", self.connection_name)
        self.client = EbicsNode(self.connection)
        
    def test_basic_connection(self):
        """Test 1: Connexion basique"""
        self.assertIsNotNone(self.client)
        self.assertIsNotNone(self.client.connection)
        self.assertEqual(self.client.connection.name, self.connection_name)
        
    def test_connection_parameters(self):
        """Test 2: Vérifier les paramètres de connexion"""
        required_fields = ['url', 'host_id', 'partner_id', 'user_id']
        
        for field in required_fields:
            value = getattr(self.connection, field, None)
            self.assertIsNotNone(value, f"Le champ {field} est manquant")
            self.assertTrue(len(str(value)) > 0, f"Le champ {field} est vide")
            
    def test_url_validation(self):
        """Test 3: Validation de l'URL EBICS"""
        url = self.connection.url
        
        # Vérifier que c'est une URL HTTPS
        self.assertTrue(url.startswith('https://'), "L'URL doit être HTTPS")
        
        # Vérifier qu'elle contient ebics
        self.assertIn('ebics', url.lower(), "L'URL doit contenir 'ebics'")
        
    def test_passphrase_handling(self):
        """Test 4: Gestion du passphrase"""
        passphrase = self.client._get_passphrase()
        
        self.assertIsNotNone(passphrase)
        
        # Vérifier que ce n'est pas le masque UI
        if passphrase == "*******":
            print("⚠️  ATTENTION: Le passphrase est le masque UI littéral")
            
    def test_client_initialization_time(self):
        """Test 5: Performance de l'initialisation"""
        from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
        
        start = time.time()
        client = EbicsNode(self.connection)
        elapsed = time.time() - start
        
        self.assertLess(elapsed, 1.0, f"Initialisation trop lente: {elapsed:.3f}s")
        
    def test_multiple_connections(self):
        """Test 6: Créer plusieurs clients simultanément"""
        from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
        
        clients = []
        for i in range(3):
            client = EbicsNode(self.connection)
            self.assertIsNotNone(client)
            clients.append(client)
            
        self.assertEqual(len(clients), 3)
        
    def test_connection_with_invalid_doc(self):
        """Test 7: Gestion d'une connexion invalide"""
        from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
        
        with self.assertRaises(Exception):
            # Essayer avec un nom de connexion inexistant
            fake_conn = frappe.get_doc("ebics Connection", "NonExistentConnection")
            client = EbicsNode(fake_conn)
            
    def test_bank_parameters(self):
        """Test 8: Vérifier les paramètres bancaires"""
        # Vérifier que les IBANs sont configurés si nécessaire
        if hasattr(self.connection, 'iban'):
            iban = self.connection.iban
            if iban:
                # IBAN suisse commence par CH
                self.assertTrue(iban.startswith('CH') or iban.startswith('LI'))
                
    def test_connection_status_fields(self):
        """Test 9: Vérifier les champs de statut"""
        status_fields = ['ini_sent', 'hia_sent', 'bank_activated']
        
        for field in status_fields:
            self.assertTrue(hasattr(self.connection, field), 
                          f"Le champ de statut {field} n'existe pas")
                          
    def test_node_command_availability(self):
        """Test 10: Vérifier que node-ebics-client est disponible"""
        import subprocess
        
        try:
            # Vérifier que npm et node sont installés
            result = subprocess.run(['node', '--version'], 
                                  capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            
            # Vérifier que node-ebics-client est installé
            result = subprocess.run(['npm', 'list', 'node-ebics-client'], 
                                  capture_output=True, text=True, 
                                  cwd='/Users/jeremy/Downloads/node-ebics-client-master')
            self.assertIn('node-ebics-client', result.stdout)
            
        except FileNotFoundError:
            self.fail("Node.js n'est pas installé")
            

def run_tests():
    """Exécuter tous les tests de connexion"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestEBICSConnection)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    import sys
    sys.path.append('/home/neoffice/frappe-bench/sites')
    frappe.init(site='prod.local')
    frappe.connect()
    
    success = run_tests()
    
    frappe.destroy()
    sys.exit(0 if success else 1)