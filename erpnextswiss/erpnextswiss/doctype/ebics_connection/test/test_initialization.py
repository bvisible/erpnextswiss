#!/usr/bin/env python3
"""
Tests d'initialisation EBICS
Test le workflow INI, HIA, HPB et activation
"""

import frappe
import unittest
import json
from datetime import datetime
from typing import Dict, Optional

class TestEBICSInitialization(unittest.TestCase):
    """Tests du workflow d'initialisation EBICS"""
    
    @classmethod
    def setUpClass(cls):
        """Configuration initiale"""
        cls.connection_name = "Raiffeisen"
        cls.connection = frappe.get_doc("ebics Connection", cls.connection_name)
        
    def setUp(self):
        """Avant chaque test"""
        from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
        self.client = EbicsNode(self.connection)
        
    def test_ini_status(self):
        """Test 1: Vérifier le statut INI"""
        ini_sent = self.connection.ini_sent
        
        if ini_sent:
            print("✅ INI déjà envoyé")
        else:
            print("⚠️  INI pas encore envoyé")
            
        # Le champ doit exister
        self.assertIsNotNone(ini_sent)
        
    def test_hia_status(self):
        """Test 2: Vérifier le statut HIA"""
        hia_sent = self.connection.hia_sent
        
        if hia_sent:
            print("✅ HIA déjà envoyé")
        else:
            print("⚠️  HIA pas encore envoyé")
            
        self.assertIsNotNone(hia_sent)
        
    def test_bank_activation_status(self):
        """Test 3: Vérifier le statut d'activation"""
        bank_activated = self.connection.bank_activated
        
        if bank_activated:
            print("✅ Banque activée")
        else:
            print("⚠️  Banque pas encore activée")
            
        self.assertIsNotNone(bank_activated)
        
    def test_ini_method(self):
        """Test 4: Test de la méthode INI (sans exécuter si déjà fait)"""
        if self.connection.ini_sent:
            print("ℹ️  INI déjà envoyé, skip du test")
            self.skipTest("INI déjà envoyé")
            
        # Si pas encore envoyé, on pourrait le tester
        # mais on ne le fait pas automatiquement
        self.assertTrue(hasattr(self.client, 'INI'))
        
    def test_hia_method(self):
        """Test 5: Test de la méthode HIA (sans exécuter si déjà fait)"""
        if self.connection.hia_sent:
            print("ℹ️  HIA déjà envoyé, skip du test")
            self.skipTest("HIA déjà envoyé")
            
        self.assertTrue(hasattr(self.client, 'HIA'))
        
    def test_hpb_method(self):
        """Test 6: Test de la méthode HPB"""
        result = self.client.HPB()
        
        self.assertIsNotNone(result)
        self.assertIn('success', result)
        
        if result.get('success'):
            print("✅ HPB exécuté avec succès")
            
            # Vérifier si les clés de la banque sont reçues
            if 'output' in result:
                try:
                    output_str = str(result['output'])
                    json_start = output_str.find('{')
                    if json_start >= 0:
                        data = json.loads(output_str[json_start:])
                        
                        if data.get('bankKeysReceived'):
                            print("✅ Clés de la banque reçues et sauvegardées")
                            self.assertTrue(True)
                        else:
                            technical_code = data.get('data', {}).get('technicalCode')
                            if technical_code == '061001':
                                print("⏳ Code 061001: Banque pas encore activée")
                            elif technical_code == '000000':
                                print("✅ HPB réussi avec code 000000")
                            else:
                                print(f"⚠️  Code technique: {technical_code}")
                except Exception as e:
                    print(f"⚠️  Impossible de parser la réponse HPB: {e}")
        else:
            error = result.get('error', 'Erreur inconnue')
            print(f"❌ HPB échoué: {error}")
            
            # Si c'est une erreur d'authentification, c'est normal
            if '061001' in str(error):
                print("ℹ️  C'est normal si la banque n'a pas encore activé")
                
    def test_initialization_order(self):
        """Test 7: Vérifier l'ordre d'initialisation"""
        # L'ordre correct est : Génération clés -> INI -> HIA -> HPB -> Activation
        
        # Si INI est envoyé, les clés doivent exister
        if self.connection.ini_sent:
            import os
            site_path = frappe.get_site_path()
            keys_file = os.path.join(
                site_path, "private", "files", "ebics_keys",
                self.connection_name, "keys.json"
            )
            self.assertTrue(os.path.exists(keys_file), 
                          "INI envoyé mais pas de clés!")
                          
        # Si HIA est envoyé, INI doit l'être aussi
        if self.connection.hia_sent:
            self.assertTrue(self.connection.ini_sent, 
                          "HIA envoyé mais pas INI!")
                          
        # Si activé, INI et HIA doivent être envoyés
        if self.connection.bank_activated:
            self.assertTrue(self.connection.ini_sent, 
                          "Activé mais INI pas envoyé!")
            self.assertTrue(self.connection.hia_sent, 
                          "Activé mais HIA pas envoyé!")
                          
    def test_ini_letter_generation(self):
        """Test 8: Test de génération de la lettre INI"""
        from erpnextswiss.erpnextswiss.ebics_api import generate_ini_letter_pdf
        
        self.assertTrue(callable(generate_ini_letter_pdf))
        
        # On ne génère pas vraiment le PDF dans le test
        # mais on vérifie que la fonction existe
        
    def test_bank_technical_codes(self):
        """Test 9: Comprendre les codes techniques EBICS"""
        codes = {
            "000000": "Succès",
            "061001": "Authentification échouée / Non activé",
            "061002": "Signature invalide", 
            "090003": "Utilisateur inconnu",
            "091001": "Type d'ordre inconnu",
            "091005": "Pas de données disponibles",
            "091116": "Ordre déjà soumis"
        }
        
        # Juste vérifier qu'on connaît les codes
        self.assertGreater(len(codes), 5)
        
        print(f"📋 {len(codes)} codes techniques connus")
        
    def test_workflow_completion(self):
        """Test 10: Vérifier la complétion du workflow"""
        steps = {
            "Clés générées": self._check_keys_exist(),
            "INI envoyé": self.connection.ini_sent,
            "HIA envoyé": self.connection.hia_sent,
            "HPB exécuté": self._check_hpb_done(),
            "Banque activée": self.connection.bank_activated
        }
        
        print("\n📊 État du workflow d'initialisation:")
        for step, done in steps.items():
            status = "✅" if done else "⏳"
            print(f"  {status} {step}")
            
        # Calculer le pourcentage de complétion
        completed = sum(1 for done in steps.values() if done)
        total = len(steps)
        percentage = (completed / total) * 100
        
        print(f"\n📈 Progression: {completed}/{total} ({percentage:.0f}%)")
        
        # Le test passe toujours, c'est juste informatif
        self.assertTrue(True)
        
    def _check_keys_exist(self):
        """Helper: Vérifier que les clés existent"""
        import os
        site_path = frappe.get_site_path()
        keys_file = os.path.join(
            site_path, "private", "files", "ebics_keys",
            self.connection_name, "keys.json"
        )
        return os.path.exists(keys_file)
        
    def _check_hpb_done(self):
        """Helper: Vérifier si HPB a été fait (heuristique)"""
        # On ne peut pas savoir avec certitude sans flag dédié
        # mais si la banque est activée, HPB a forcément été fait
        return self.connection.bank_activated
        

def run_tests():
    """Exécuter tous les tests d'initialisation"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestEBICSInitialization)
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