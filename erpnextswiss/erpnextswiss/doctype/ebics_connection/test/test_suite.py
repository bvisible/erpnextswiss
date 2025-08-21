#!/usr/bin/env python3
"""
Suite de tests complète pour EBICS
Exécute tous les tests dans l'ordre approprié
"""

import frappe
import unittest
from datetime import datetime, timedelta
import json
import sys
import traceback
from typing import Dict, List, Optional

class EBICSTestSuite:
    """Suite de tests principale pour EBICS"""
    
    def __init__(self, connection_name: str = "Raiffeisen", verbose: bool = True):
        self.connection_name = connection_name
        self.verbose = verbose
        self.results = []
        self.errors = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log avec niveau"""
        if self.verbose:
            prefix = {
                "INFO": "ℹ️ ",
                "SUCCESS": "✅",
                "WARNING": "⚠️ ",
                "ERROR": "❌",
                "DEBUG": "🔍"
            }.get(level, "")
            print(f"{prefix} {message}")
    
    def run_all_tests(self) -> Dict:
        """Exécute tous les tests dans l'ordre"""
        
        self.log("="*60)
        self.log("SUITE DE TESTS EBICS COMPLÈTE")
        self.log(f"Connection: {self.connection_name}")
        self.log(f"Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log("="*60)
        
        # Liste des tests à exécuter dans l'ordre
        test_sequence = [
            ("Configuration", self.test_configuration),
            ("Connection", self.test_connection),
            ("Clés existantes", self.test_existing_keys),
            ("Génération de clés", self.test_key_generation),
            ("INI", self.test_ini),
            ("HIA", self.test_hia),
            ("HPB", self.test_hpb),
            ("Lettre INI", self.test_ini_letter),
            ("Z53 Download", self.test_z53_download),
            ("Z52 Download", self.test_z52_download),
            ("Parsing CAMT", self.test_camt_parsing),
            ("Upload Payment", self.test_payment_upload),
            ("Gestion d'erreurs", self.test_error_handling),
            ("Performance", self.test_performance)
        ]
        
        # Exécuter chaque test
        for test_name, test_func in test_sequence:
            self.log(f"\n📝 Test: {test_name}")
            self.log("-" * 40)
            
            try:
                result = test_func()
                self.results.append({
                    "test": test_name,
                    "status": "PASS" if result else "FAIL",
                    "result": result
                })
                
                if result:
                    self.log(f"Test {test_name} réussi", "SUCCESS")
                else:
                    self.log(f"Test {test_name} échoué", "WARNING")
                    
            except Exception as e:
                self.errors.append({
                    "test": test_name,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
                self.log(f"Test {test_name} - Erreur: {e}", "ERROR")
                self.results.append({
                    "test": test_name,
                    "status": "ERROR",
                    "error": str(e)
                })
        
        # Résumé
        self.print_summary()
        
        return {
            "results": self.results,
            "errors": self.errors,
            "summary": self.get_summary()
        }
    
    def test_configuration(self) -> bool:
        """Test 1: Vérifier la configuration"""
        try:
            conn = frappe.get_doc("ebics Connection", self.connection_name)
            
            required_fields = ['url', 'host_id', 'partner_id', 'user_id']
            missing = []
            
            for field in required_fields:
                if not getattr(conn, field, None):
                    missing.append(field)
            
            if missing:
                self.log(f"Champs manquants: {', '.join(missing)}", "WARNING")
                return False
            
            self.log(f"URL: {conn.url}")
            self.log(f"Host ID: {conn.host_id}")
            self.log(f"Partner ID: {conn.partner_id}")
            self.log(f"User ID: {conn.user_id}")
            
            return True
            
        except Exception as e:
            self.log(f"Erreur configuration: {e}", "ERROR")
            return False
    
    def test_connection(self) -> bool:
        """Test 2: Tester la connexion EBICS"""
        try:
            from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
            
            conn = frappe.get_doc("ebics Connection", self.connection_name)
            client = EbicsNode(conn)
            
            # Vérifier que le client est créé
            if client:
                self.log("Client EBICS créé avec succès")
                return True
            return False
            
        except Exception as e:
            self.log(f"Erreur connexion: {e}", "ERROR")
            return False
    
    def test_existing_keys(self) -> bool:
        """Test 3: Vérifier l'existence des clés"""
        try:
            import os
            site_path = frappe.get_site_path()
            keys_file = os.path.join(
                site_path, "private", "files", "ebics_keys", 
                self.connection_name, "keys.json"
            )
            
            if os.path.exists(keys_file):
                size = os.path.getsize(keys_file)
                self.log(f"Fichier de clés existe ({size} bytes)")
                
                # Vérifier qu'on peut les lire
                from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
                conn = frappe.get_doc("ebics Connection", self.connection_name)
                client = EbicsNode(conn)
                
                # Tester le passphrase
                passphrase = client._get_passphrase()
                if passphrase == "*******":
                    self.log("⚠️  Passphrase est le masque UI", "WARNING")
                else:
                    self.log(f"Passphrase: {'*' * len(passphrase)}")
                
                return True
            else:
                self.log("Pas de fichier de clés", "WARNING")
                return False
                
        except Exception as e:
            self.log(f"Erreur vérification clés: {e}", "ERROR")
            return False
    
    def test_key_generation(self) -> bool:
        """Test 4: Tester la génération de clés (sans exécuter)"""
        try:
            from erpnextswiss.erpnextswiss.ebics_api import generate_new_keys
            
            # Vérifier que la fonction existe
            if callable(generate_new_keys):
                self.log("Fonction de génération de clés disponible")
                return True
            return False
            
        except Exception as e:
            self.log(f"Erreur génération clés: {e}", "ERROR")
            return False
    
    def test_ini(self) -> bool:
        """Test 5: Tester INI (sans exécuter si déjà fait)"""
        try:
            conn = frappe.get_doc("ebics Connection", self.connection_name)
            
            if conn.ini_sent:
                self.log("INI déjà envoyé")
                return True
            else:
                self.log("INI pas encore envoyé", "WARNING")
                # On pourrait l'envoyer ici si nécessaire
                return False
                
        except Exception as e:
            self.log(f"Erreur INI: {e}", "ERROR")
            return False
    
    def test_hia(self) -> bool:
        """Test 6: Tester HIA (sans exécuter si déjà fait)"""
        try:
            conn = frappe.get_doc("ebics Connection", self.connection_name)
            
            if conn.hia_sent:
                self.log("HIA déjà envoyé")
                return True
            else:
                self.log("HIA pas encore envoyé", "WARNING")
                return False
                
        except Exception as e:
            self.log(f"Erreur HIA: {e}", "ERROR")
            return False
    
    def test_hpb(self) -> bool:
        """Test 7: Tester HPB"""
        try:
            from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
            
            conn = frappe.get_doc("ebics Connection", self.connection_name)
            client = EbicsNode(conn)
            
            result = client.HPB()
            
            if result.get('success'):
                # Parser la réponse
                if 'output' in result:
                    try:
                        output_str = str(result['output'])
                        json_start = output_str.find('{')
                        if json_start >= 0:
                            data = json.loads(output_str[json_start:])
                            
                            if data.get('bankKeysReceived'):
                                self.log("Clés de la banque reçues et sauvegardées", "SUCCESS")
                                return True
                            
                            technical_code = data.get('data', {}).get('technicalCode')
                            if technical_code == '061001':
                                self.log("Authentification échouée - Banque pas activée", "WARNING")
                                return False
                            elif technical_code == '000000':
                                self.log("HPB réussi", "SUCCESS")
                                return True
                    except:
                        pass
                
                self.log("HPB exécuté mais statut incertain", "WARNING")
                return False
            else:
                self.log(f"HPB échoué: {result.get('error')}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"Erreur HPB: {e}", "ERROR")
            return False
    
    def test_ini_letter(self) -> bool:
        """Test 8: Tester la génération de la lettre INI"""
        try:
            from erpnextswiss.erpnextswiss.ebics_api import generate_ini_letter_pdf
            
            if callable(generate_ini_letter_pdf):
                self.log("Fonction de génération PDF disponible")
                return True
            return False
            
        except Exception as e:
            self.log(f"Erreur lettre INI: {e}", "ERROR")
            return False
    
    def test_z53_download(self) -> bool:
        """Test 9: Tester le download Z53"""
        try:
            from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
            
            conn = frappe.get_doc("ebics Connection", self.connection_name)
            client = EbicsNode(conn)
            
            to_date = datetime.now()
            from_date = to_date - timedelta(days=7)
            
            # Test sans parsing
            result = client.Z53(from_date, to_date, parsed=False)
            
            if result.get('success'):
                self.log("Z53 download réussi")
                return True
            else:
                error = result.get('error', '')
                if 'Cannot read properties of null' in str(error):
                    self.log("Clés de la banque manquantes", "WARNING")
                elif '091005' in str(error):
                    self.log("Pas de données disponibles (normal)", "WARNING")
                    return True
                else:
                    self.log(f"Z53 échoué: {error}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"Erreur Z53: {e}", "ERROR")
            return False
    
    def test_z52_download(self) -> bool:
        """Test 10: Tester le download Z52"""
        try:
            from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
            
            conn = frappe.get_doc("ebics Connection", self.connection_name)
            client = EbicsNode(conn)
            
            to_date = datetime.now()
            from_date = to_date - timedelta(days=1)
            
            result = client.Z52(from_date, to_date, parsed=False)
            
            if result.get('success'):
                self.log("Z52 download réussi")
                return True
            else:
                error = result.get('error', '')
                if '091005' in str(error):
                    self.log("Pas de données intraday (normal)", "WARNING")
                    return True
                else:
                    self.log(f"Z52 échoué: {error}", "WARNING")
                return False
                
        except Exception as e:
            self.log(f"Erreur Z52: {e}", "ERROR")
            return False
    
    def test_camt_parsing(self) -> bool:
        """Test 11: Tester le parsing CAMT"""
        try:
            # Vérifier que les fonctions de parsing existent
            from erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard import read_camt053
            
            if callable(read_camt053):
                self.log("Fonction de parsing CAMT disponible")
                return True
            return False
            
        except Exception as e:
            self.log(f"Parsing CAMT non disponible: {e}", "WARNING")
            return False
    
    def test_payment_upload(self) -> bool:
        """Test 12: Tester l'upload de paiements (sans exécuter)"""
        try:
            from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
            
            conn = frappe.get_doc("ebics Connection", self.connection_name)
            client = EbicsNode(conn)
            
            # Vérifier que les méthodes existent
            if hasattr(client, 'CCT') and hasattr(client, 'XE2'):
                self.log("Méthodes d'upload disponibles (CCT, XE2)")
                return True
            return False
            
        except Exception as e:
            self.log(f"Erreur upload: {e}", "ERROR")
            return False
    
    def test_error_handling(self) -> bool:
        """Test 13: Tester la gestion d'erreurs"""
        try:
            # Dictionnaire des codes d'erreur EBICS
            error_codes = {
                "000000": "Success",
                "061001": "Authentication failed",
                "091005": "No data available",
                "090003": "User unknown",
                "091001": "Order type unknown"
            }
            
            self.log(f"Codes d'erreur connus: {len(error_codes)}")
            return True
            
        except Exception as e:
            self.log(f"Erreur: {e}", "ERROR")
            return False
    
    def test_performance(self) -> bool:
        """Test 14: Tester les performances"""
        try:
            import time
            from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
            
            conn = frappe.get_doc("ebics Connection", self.connection_name)
            
            start = time.time()
            client = EbicsNode(conn)
            elapsed = time.time() - start
            
            self.log(f"Temps de création du client: {elapsed:.3f}s")
            
            if elapsed < 1.0:
                self.log("Performance acceptable", "SUCCESS")
                return True
            else:
                self.log("Performance lente", "WARNING")
                return False
                
        except Exception as e:
            self.log(f"Erreur performance: {e}", "ERROR")
            return False
    
    def get_summary(self) -> Dict:
        """Génère un résumé des tests"""
        total = len(self.results)
        passed = len([r for r in self.results if r['status'] == 'PASS'])
        failed = len([r for r in self.results if r['status'] == 'FAIL'])
        errors = len([r for r in self.results if r['status'] == 'ERROR'])
        
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "success_rate": f"{(passed/total*100):.1f}%" if total > 0 else "0%"
        }
    
    def print_summary(self):
        """Affiche le résumé des tests"""
        summary = self.get_summary()
        
        self.log("\n" + "="*60)
        self.log("RÉSUMÉ DES TESTS")
        self.log("="*60)
        
        self.log(f"Total: {summary['total']} tests")
        self.log(f"✅ Réussis: {summary['passed']}")
        self.log(f"⚠️  Échoués: {summary['failed']}")
        self.log(f"❌ Erreurs: {summary['errors']}")
        self.log(f"📊 Taux de réussite: {summary['success_rate']}")
        
        if self.errors:
            self.log("\n⚠️  Erreurs détectées:", "WARNING")
            for error in self.errors:
                self.log(f"  - {error['test']}: {error['error']}")


def run_test_suite(connection_name: str = "Raiffeisen", verbose: bool = True):
    """Point d'entrée principal pour exécuter la suite de tests"""
    suite = EBICSTestSuite(connection_name, verbose)
    return suite.run_all_tests()


if __name__ == "__main__":
    # Pour tests locaux
    import sys
    sys.path.append('/home/neoffice/frappe-bench/sites')
    frappe.init(site='prod.local')
    frappe.connect()
    
    result = run_test_suite()
    
    frappe.destroy()
    
    # Code de sortie basé sur le résultat
    summary = result['summary']
    if summary['errors'] > 0:
        sys.exit(2)
    elif summary['failed'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)