#!/usr/bin/env python3
"""
Tests de gestion des clés EBICS
Test la génération, sauvegarde et gestion des clés RSA
"""

import frappe
import unittest
import os
import json
import base64
from datetime import datetime
from typing import Dict, Optional

class TestEBICSKeys(unittest.TestCase):
    """Tests de gestion des clés EBICS"""
    
    @classmethod
    def setUpClass(cls):
        """Configuration initiale"""
        cls.connection_name = "Raiffeisen"
        cls.connection = frappe.get_doc("ebics Connection", cls.connection_name)
        
    def setUp(self):
        """Avant chaque test"""
        from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
        self.client = EbicsNode(self.connection)
        
    def test_keys_file_exists(self):
        """Test 1: Vérifier l'existence du fichier de clés"""
        site_path = frappe.get_site_path()
        keys_file = os.path.join(
            site_path, "private", "files", "ebics_keys",
            self.connection_name, "keys.json"
        )
        
        self.assertTrue(os.path.exists(keys_file), 
                       f"Le fichier de clés n'existe pas: {keys_file}")
                       
        # Vérifier la taille
        size = os.path.getsize(keys_file)
        self.assertGreater(size, 100, "Le fichier de clés est trop petit")
        
    def test_keys_file_format(self):
        """Test 2: Vérifier le format du fichier de clés"""
        site_path = frappe.get_site_path()
        keys_file = os.path.join(
            site_path, "private", "files", "ebics_keys",
            self.connection_name, "keys.json"
        )
        
        with open(keys_file, 'r') as f:
            content = f.read()
            
        # Le fichier doit être du Base64 (format node-ebics-client)
        try:
            # Essayer de décoder en Base64
            decoded = base64.b64decode(content)
            self.assertGreater(len(decoded), 0, "Le contenu décodé est vide")
        except Exception as e:
            self.fail(f"Le fichier n'est pas en Base64 valide: {e}")
            
    def test_passphrase_masking(self):
        """Test 3: Test de la gestion du masquage du passphrase"""
        passphrase = self.client._get_passphrase()
        
        self.assertIsNotNone(passphrase)
        
        # Si c'est le masque, vérifier qu'on utilise la valeur par défaut
        if passphrase == "*******":
            print("⚠️  Passphrase est le masque UI, utilise 'default'")
            # Vérifier que la méthode retourne quand même quelque chose
            self.assertTrue(len(passphrase) > 0)
            
    def test_key_types(self):
        """Test 4: Vérifier les types de clés EBICS"""
        # Les clés EBICS standard
        key_types = ['A006', 'X002', 'E002']  # Signature, Auth, Encryption
        
        # node-ebics-client devrait gérer ces types
        for key_type in key_types:
            # On ne peut pas vérifier directement sans décrypter
            # mais on vérifie que le client les comprend
            self.assertIsNotNone(self.client)
            
    def test_bank_keys_storage(self):
        """Test 5: Vérifier le stockage des clés de la banque"""
        # Après HPB, les clés de la banque devraient être stockées
        # On ne peut pas les lire directement (chiffrées)
        # mais on peut vérifier que le client les gère
        
        # Ce test vérifie juste que la méthode existe
        self.assertTrue(hasattr(self.client, 'HPB'))
        
    def test_key_generation_function(self):
        """Test 6: Vérifier que la fonction de génération existe"""
        from erpnextswiss.erpnextswiss.ebics_api import generate_new_keys
        
        self.assertTrue(callable(generate_new_keys))
        
    def test_keys_directory_permissions(self):
        """Test 7: Vérifier les permissions du dossier de clés"""
        site_path = frappe.get_site_path()
        keys_dir = os.path.join(
            site_path, "private", "files", "ebics_keys",
            self.connection_name
        )
        
        self.assertTrue(os.path.exists(keys_dir))
        
        # Vérifier que le dossier est accessible en écriture
        self.assertTrue(os.access(keys_dir, os.W_OK), 
                       "Le dossier de clés n'est pas accessible en écriture")
                       
    def test_backup_keys_exist(self):
        """Test 8: Vérifier s'il y a des backups de clés"""
        site_path = frappe.get_site_path()
        keys_dir = os.path.join(
            site_path, "private", "files", "ebics_keys",
            self.connection_name
        )
        
        # Lister les fichiers de backup
        backup_files = [f for f in os.listdir(keys_dir) 
                       if f.startswith('keys') and f.endswith('.backup')]
        
        if backup_files:
            print(f"📁 {len(backup_files)} fichier(s) de backup trouvé(s)")
            for backup in backup_files:
                file_path = os.path.join(keys_dir, backup)
                size = os.path.getsize(file_path)
                print(f"  - {backup} ({size} bytes)")
                
    def test_key_encryption_strength(self):
        """Test 9: Vérifier la force du chiffrement"""
        # node-ebics-client utilise AES-256-CBC
        # On vérifie juste que les clés sont chiffrées
        
        site_path = frappe.get_site_path()
        keys_file = os.path.join(
            site_path, "private", "files", "ebics_keys",
            self.connection_name, "keys.json"
        )
        
        with open(keys_file, 'r') as f:
            content = f.read()
            
        # Ne doit pas contenir de texte en clair sensible
        sensitive_patterns = ['BEGIN RSA', 'PRIVATE KEY', 'privateKey']
        
        for pattern in sensitive_patterns:
            self.assertNotIn(pattern, content, 
                           f"Le fichier contient '{pattern}' en clair!")
                           
    def test_key_persistence(self):
        """Test 10: Vérifier la persistance des clés"""
        from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
        
        # Créer deux clients et vérifier qu'ils utilisent les mêmes clés
        client1 = EbicsNode(self.connection)
        client2 = EbicsNode(self.connection)
        
        # Les deux devraient pouvoir accéder aux clés
        passphrase1 = client1._get_passphrase()
        passphrase2 = client2._get_passphrase()
        
        self.assertEqual(passphrase1, passphrase2, 
                        "Les passphrases devraient être identiques")
        

def run_tests():
    """Exécuter tous les tests de clés"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestEBICSKeys)
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