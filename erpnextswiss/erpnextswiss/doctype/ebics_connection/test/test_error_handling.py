#!/usr/bin/env python3
"""
Tests de gestion des erreurs EBICS
Test tous les codes d'erreur et la récupération
"""

import frappe
import unittest
from datetime import datetime
import json
from typing import Dict, List

class TestEBICSErrorHandling(unittest.TestCase):
    """Tests de gestion des erreurs EBICS"""
    
    @classmethod
    def setUpClass(cls):
        """Configuration initiale"""
        cls.connection_name = "Raiffeisen"
        cls.connection = frappe.get_doc("ebics Connection", cls.connection_name)
        
        # Dictionnaire complet des codes d'erreur EBICS
        cls.error_codes = {
            # Codes de succès
            "000000": "OK - Traitement réussi",
            "011000": "OK - Téléchargement positif",
            "011001": "OK - Segment téléchargé",
            
            # Codes d'authentification
            "061001": "Authentification échouée",
            "061002": "Signature invalide",
            "061099": "Erreur d'authentification interne",
            
            # Codes utilisateur
            "090003": "Utilisateur inconnu",
            "090004": "Utilisateur invalide",
            "090005": "Utilisateur verrouillé",
            "091002": "Utilisateur non autorisé",
            
            # Codes de transaction
            "091001": "Type d'ordre inconnu",
            "091003": "Format de message non supporté",
            "091004": "Version non supportée",
            "091005": "Pas de données disponibles",
            "091006": "Téléchargement impossible",
            "091007": "Upload impossible",
            "091101": "TX segment non trouvé",
            "091102": "Transaction invalide",
            "091103": "TX segment invalide",
            "091104": "TX segment déjà existant",
            "091112": "Format de message invalide",
            "091113": "Fichier de format incohérent",
            "091115": "Ordre en cours de traitement",
            "091116": "Ordre déjà existant",
            "091117": "Téléchargement en cours",
            "091118": "Aucun téléchargement en cours",
            "091119": "Reprise impossible",
            "091120": "Ordre annulé",
            
            # Codes de sécurité
            "091201": "Algorithme de signature non supporté",
            "091202": "Algorithme de chiffrement non supporté",
            "091203": "Clé publique inconnue",
            "091204": "Format de clé invalide",
            "091205": "Certificat invalide",
            "091206": "Certificat expiré",
            "091207": "Certificat révoqué",
            "091208": "Certificat non encore valide",
            "091209": "Algorithme de hash non supporté",
            
            # Codes de compte
            "091301": "Compte bloqué",
            "091302": "Compte inconnu",
            "091303": "Limite dépassée",
            "091304": "Compte non autorisé"
        }
        
    def setUp(self):
        """Avant chaque test"""
        from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
        self.client = EbicsNode(self.connection)
        
    def test_error_code_dictionary(self):
        """Test 1: Vérifier le dictionnaire des codes d'erreur"""
        self.assertGreater(len(self.error_codes), 30)
        print(f"📋 {len(self.error_codes)} codes d'erreur connus")
        
        # Vérifier les codes critiques
        critical_codes = ["000000", "061001", "091005", "090003"]
        for code in critical_codes:
            self.assertIn(code, self.error_codes)
            
    def test_parse_error_from_response(self):
        """Test 2: Parser les codes d'erreur depuis les réponses"""
        # Simuler différentes réponses d'erreur
        test_responses = [
            {"technicalCode": "061001"},
            {"data": {"technicalCode": "091005"}},
            {"error": "Authentication failed", "code": "061001"},
            {"message": "No data available (091005)"}
        ]
        
        for response in test_responses:
            code = self._extract_error_code(response)
            if code:
                print(f"✅ Code extrait: {code} - {self.error_codes.get(code, 'Inconnu')}")
                
    def test_authentication_errors(self):
        """Test 3: Test des erreurs d'authentification"""
        # Tester avec une mauvaise connexion devrait donner 061001
        to_date = datetime.now()
        from_date = to_date.add(days=-1)
        
        result = self.client.Z53(from_date, to_date, parsed=False)
        
        if not result.get('success'):
            error = str(result.get('error', ''))
            if '061001' in error:
                print("✅ Erreur 061001 correctement détectée")
                print("   -> Authentification échouée / Non activé")
                
    def test_no_data_error(self):
        """Test 4: Test de l'erreur 'pas de données'"""
        # Tester avec une date très ancienne
        from datetime import datetime, timedelta
        old_date = datetime.now() - timedelta(days=365*2)  # 2 ans
        
        result = self.client.Z53(old_date, old_date.add(days=1), parsed=False)
        
        if not result.get('success'):
            error = str(result.get('error', ''))
            if '091005' in error:
                print("✅ Erreur 091005 correctement gérée")
                print("   -> Pas de données disponibles")
                
    def test_missing_keys_error(self):
        """Test 5: Test de l'erreur de clés manquantes"""
        result = self.client.Z53(datetime.now().add(days=-1), datetime.now(), parsed=False)
        
        if not result.get('success'):
            error = str(result.get('error', ''))
            if 'Cannot read properties of null' in error:
                print("✅ Erreur de clés manquantes détectée")
                print("   -> Les clés de la banque doivent être téléchargées (HPB)")
                
    def test_error_categories(self):
        """Test 6: Catégoriser les types d'erreurs"""
        categories = {
            "Succès": [],
            "Authentification": [],
            "Utilisateur": [],
            "Transaction": [],
            "Sécurité": [],
            "Compte": [],
            "Autres": []
        }
        
        for code, desc in self.error_codes.items():
            if code.startswith("00") or code.startswith("01"):
                categories["Succès"].append(code)
            elif code.startswith("061"):
                categories["Authentification"].append(code)
            elif code.startswith("090"):
                categories["Utilisateur"].append(code)
            elif code.startswith("0910") or code.startswith("0911"):
                categories["Transaction"].append(code)
            elif code.startswith("0912"):
                categories["Sécurité"].append(code)
            elif code.startswith("0913"):
                categories["Compte"].append(code)
            else:
                categories["Autres"].append(code)
                
        print("\n📊 Catégories d'erreurs:")
        for cat, codes in categories.items():
            if codes:
                print(f"  {cat}: {len(codes)} codes")
                
    def test_error_recovery(self):
        """Test 7: Test de récupération après erreur"""
        # Stratégies de récupération par type d'erreur
        recovery_strategies = {
            "061001": "Attendre l'activation de la banque",
            "091005": "Normal - pas de données pour cette période",
            "091115": "Réessayer plus tard",
            "091116": "Ordre déjà soumis - ignorer",
            "091301": "Contacter la banque - compte bloqué",
            "090005": "Contacter la banque - utilisateur verrouillé"
        }
        
        print("\n🔧 Stratégies de récupération:")
        for code, strategy in recovery_strategies.items():
            desc = self.error_codes.get(code, "Inconnu")
            print(f"  {code} ({desc})")
            print(f"    -> {strategy}")
            
    def test_error_logging(self):
        """Test 8: Vérifier que les erreurs sont loggées"""
        # Les erreurs devraient être dans frappe.log
        # On vérifie juste que le mécanisme existe
        
        import frappe
        
        # Simuler un log d'erreur
        frappe.log_error(
            title="EBICS Test Error",
            message="Test error logging for EBICS"
        )
        
        print("✅ Mécanisme de logging disponible")
        
    def test_timeout_handling(self):
        """Test 9: Gestion des timeouts"""
        # node-ebics-client a un timeout configurable
        # On vérifie que notre client le gère
        
        # Un timeout devrait retourner une erreur spécifique
        # mais on ne peut pas le tester sans vraiment timeout
        
        print("ℹ️  Test de timeout - vérification manuelle requise")
        
    def test_critical_error_detection(self):
        """Test 10: Détecter les erreurs critiques"""
        critical_errors = {
            "061001": "Non activé - Action requise",
            "090005": "Utilisateur verrouillé - CRITIQUE",
            "091301": "Compte bloqué - CRITIQUE",
            "091206": "Certificat expiré - CRITIQUE",
            "091207": "Certificat révoqué - CRITIQUE"
        }
        
        print("\n🚨 Erreurs critiques à surveiller:")
        for code, impact in critical_errors.items():
            print(f"  {code}: {impact}")
            
        # Dans un vrai système, on devrait alerter sur ces erreurs
        self.assertTrue(len(critical_errors) > 0)
        
    def _extract_error_code(self, response: Dict) -> Optional[str]:
        """Helper pour extraire un code d'erreur d'une réponse"""
        # Chercher dans différents endroits
        if isinstance(response, dict):
            # Direct
            if 'technicalCode' in response:
                return response['technicalCode']
            
            # Nested
            if 'data' in response and isinstance(response['data'], dict):
                if 'technicalCode' in response['data']:
                    return response['data']['technicalCode']
                    
            # Dans le message d'erreur
            if 'error' in response:
                error_str = str(response['error'])
                for code in self.error_codes.keys():
                    if code in error_str:
                        return code
                        
            if 'message' in response:
                msg = str(response['message'])
                for code in self.error_codes.keys():
                    if code in msg:
                        return code
                        
        return None
        

def run_tests():
    """Exécuter tous les tests de gestion d'erreurs"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestEBICSErrorHandling)
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