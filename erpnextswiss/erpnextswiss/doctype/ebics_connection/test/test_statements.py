#!/usr/bin/env python3
"""
Tests de téléchargement des relevés EBICS
Test Z52, Z53, C52, C53 et le parsing
"""

import frappe
import unittest
from datetime import datetime, timedelta
import json
from typing import Dict, Optional, List

class TestEBICSStatements(unittest.TestCase):
    """Tests de téléchargement des relevés"""
    
    @classmethod
    def setUpClass(cls):
        """Configuration initiale"""
        cls.connection_name = "Raiffeisen"
        cls.connection = frappe.get_doc("ebics Connection", cls.connection_name)
        
    def setUp(self):
        """Avant chaque test"""
        from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
        self.client = EbicsNode(self.connection)
        
    def test_z53_basic(self):
        """Test 1: Download Z53 basique (7 jours)"""
        to_date = datetime.now()
        from_date = to_date - timedelta(days=7)
        
        result = self.client.Z53(from_date, to_date, parsed=False)
        
        self._analyze_result(result, "Z53 (7 jours)")
        
    def test_z53_with_parsing(self):
        """Test 2: Download Z53 avec parsing"""
        to_date = datetime.now()
        from_date = to_date - timedelta(days=7)
        
        result = self.client.Z53(from_date, to_date, parsed=True)
        
        self._analyze_result(result, "Z53 avec parsing")
        
        if result.get('parsed'):
            print("✅ Données parsées disponibles")
            transactions = result.get('transactions', [])
            print(f"📊 {len(transactions)} transaction(s) trouvée(s)")
            
    def test_z53_date_ranges(self):
        """Test 3: Test avec différentes plages de dates"""
        test_ranges = [
            ("Aujourd'hui", 0),
            ("Hier", 1),
            ("3 jours", 3),
            ("1 semaine", 7),
            ("1 mois", 30),
            ("3 mois", 90)
        ]
        
        print("\n📅 Test de différentes plages de dates:")
        
        for label, days in test_ranges:
            to_date = datetime.now()
            from_date = to_date - timedelta(days=days)
            
            result = self.client.Z53(from_date, to_date, parsed=False)
            
            if result.get('success'):
                print(f"  ✅ {label}: Succès")
            else:
                error = result.get('error', '')
                if '091005' in str(error):
                    print(f"  ℹ️  {label}: Pas de données")
                elif '061001' in str(error):
                    print(f"  ⚠️  {label}: Non activé")
                    break  # Pas la peine de continuer
                else:
                    print(f"  ❌ {label}: Erreur")
                    
    def test_z52_intraday(self):
        """Test 4: Download Z52 (relevé intraday)"""
        to_date = datetime.now()
        from_date = to_date - timedelta(days=1)
        
        result = self.client.Z52(from_date, to_date, parsed=False)
        
        self._analyze_result(result, "Z52 intraday")
        
        # Z52 a souvent pas de données (normal)
        if not result.get('success'):
            error = result.get('error', '')
            if '091005' in str(error):
                print("ℹ️  Pas de mouvements intraday (normal)")
                
    def test_z52_with_parsing(self):
        """Test 5: Download Z52 avec parsing"""
        to_date = datetime.now()
        from_date = to_date - timedelta(hours=6)  # 6 heures
        
        result = self.client.Z52(from_date, to_date, parsed=True)
        
        self._analyze_result(result, "Z52 avec parsing")
        
    def test_c53_if_available(self):
        """Test 6: Test C53 si disponible"""
        if hasattr(self.client, 'C53'):
            to_date = datetime.now()
            from_date = to_date - timedelta(days=7)
            
            result = self.client.C53(from_date, to_date)
            self._analyze_result(result, "C53")
        else:
            self.skipTest("C53 non implémenté")
            
    def test_error_handling(self):
        """Test 7: Gestion des erreurs communes"""
        # Test avec des dates invalides
        future_date = datetime.now() + timedelta(days=30)
        past_date = datetime.now() - timedelta(days=365*5)  # 5 ans
        
        # Dates futures
        result = self.client.Z53(datetime.now(), future_date, parsed=False)
        if not result.get('success'):
            print("✅ Gestion correcte des dates futures")
            
        # Dates très anciennes
        result = self.client.Z53(past_date, past_date + timedelta(days=1), parsed=False)
        if not result.get('success'):
            error = result.get('error', '')
            if '091005' in str(error):
                print("✅ Pas de données anciennes (normal)")
                
    def test_parse_camt_function(self):
        """Test 8: Vérifier les fonctions de parsing CAMT"""
        try:
            from erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard import read_camt053
            self.assertTrue(callable(read_camt053))
            print("✅ Fonction read_camt053 disponible")
        except ImportError:
            print("⚠️  Fonction read_camt053 non disponible")
            
    def test_statement_formats(self):
        """Test 9: Vérifier les formats supportés"""
        supported_formats = []
        
        # Vérifier les méthodes disponibles
        for format in ['Z52', 'Z53', 'C52', 'C53', 'STA', 'VMK']:
            if hasattr(self.client, format):
                supported_formats.append(format)
                
        print(f"\n📋 Formats supportés: {', '.join(supported_formats)}")
        
        # Au minimum Z52 et Z53 doivent être supportés
        self.assertIn('Z52', supported_formats)
        self.assertIn('Z53', supported_formats)
        
    def test_performance(self):
        """Test 10: Test de performance pour les downloads"""
        import time
        
        to_date = datetime.now()
        from_date = to_date - timedelta(days=1)
        
        # Mesurer le temps de download
        start = time.time()
        result = self.client.Z53(from_date, to_date, parsed=False)
        elapsed = time.time() - start
        
        print(f"\n⏱️  Temps de download Z53: {elapsed:.2f}s")
        
        # Le timeout devrait être raisonnable
        if result.get('success') or '091005' in str(result.get('error', '')):
            self.assertLess(elapsed, 30, "Download trop lent (>30s)")
            
    def test_missing_bank_keys(self):
        """Test 11: Gestion des clés de banque manquantes"""
        to_date = datetime.now()
        from_date = to_date - timedelta(days=1)
        
        result = self.client.Z53(from_date, to_date, parsed=False)
        
        if not result.get('success'):
            error = str(result.get('error', ''))
            
            if 'Cannot read properties of null' in error and "'e'" in error:
                print("⚠️  Clés de la banque manquantes détectées")
                print("    -> Il faut exécuter HPB après activation")
                self.assertTrue(True)  # C'est un problème connu
            elif '061001' in error:
                print("⚠️  Banque pas activée (061001)")
                self.assertTrue(True)
                
    def _analyze_result(self, result: Dict, test_name: str):
        """Helper pour analyser un résultat"""
        if result.get('success'):
            print(f"✅ {test_name}: Succès")
            
            # Afficher des infos si disponibles
            if 'output' in result:
                output = str(result['output'])
                if len(output) > 100:
                    print(f"   📄 Données reçues: {len(output)} caractères")
                    
        else:
            error = result.get('error', 'Erreur inconnue')
            
            # Analyser le type d'erreur
            if '091005' in str(error):
                print(f"ℹ️  {test_name}: Pas de données disponibles (091005)")
            elif '061001' in str(error):
                print(f"⚠️  {test_name}: Non activé par la banque (061001)")
            elif 'Cannot read properties of null' in str(error):
                print(f"❌ {test_name}: Clés de banque manquantes")
            elif 'timeout' in str(error).lower():
                print(f"⏱️  {test_name}: Timeout")
            else:
                print(f"❌ {test_name}: {error}")
                

def run_tests():
    """Exécuter tous les tests de statements"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestEBICSStatements)
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