#!/usr/bin/env python3
"""
Outils de débogage pour EBICS
Fonctions utilitaires pour diagnostiquer les problèmes
"""

import frappe
import os
import json
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

def get_ebics_state(connection_name: str = "Raiffeisen") -> Dict:
    """
    Obtenir l'état complet d'une connexion EBICS
    
    Args:
        connection_name: Nom de la connexion EBICS
        
    Returns:
        Dict avec l'état complet
    """
    try:
        conn = frappe.get_doc("ebics Connection", connection_name)
        
        state = {
            "connection": {
                "name": conn.name,
                "url": conn.url,
                "host_id": conn.host_id,
                "partner_id": conn.partner_id,
                "user_id": conn.user_id,
                "iban": getattr(conn, 'iban', None)
            },
            "status": {
                "ini_sent": conn.ini_sent,
                "hia_sent": conn.hia_sent,
                "bank_activated": conn.bank_activated
            },
            "keys": check_keys_status(connection_name),
            "last_errors": get_recent_errors(connection_name),
            "workflow_progress": calculate_workflow_progress(conn)
        }
        
        return state
        
    except Exception as e:
        return {"error": str(e)}


def check_keys_status(connection_name: str) -> Dict:
    """
    Vérifier le statut des clés
    
    Returns:
        Dict avec les infos sur les clés
    """
    site_path = frappe.get_site_path()
    keys_dir = os.path.join(
        site_path, "private", "files", "ebics_keys", connection_name
    )
    keys_file = os.path.join(keys_dir, "keys.json")
    
    status = {
        "directory_exists": os.path.exists(keys_dir),
        "keys_file_exists": os.path.exists(keys_file),
        "keys_file_size": 0,
        "keys_file_modified": None,
        "backup_files": [],
        "passphrase_status": "unknown"
    }
    
    if os.path.exists(keys_file):
        status["keys_file_size"] = os.path.getsize(keys_file)
        status["keys_file_modified"] = datetime.fromtimestamp(
            os.path.getmtime(keys_file)
        ).strftime("%Y-%m-%d %H:%M:%S")
        
        # Vérifier le format
        try:
            with open(keys_file, 'r') as f:
                content = f.read()
                # Essayer de décoder en Base64
                base64.b64decode(content)
                status["keys_format"] = "Base64 (node-ebics-client)"
        except:
            status["keys_format"] = "Format inconnu ou corrompu"
            
    # Lister les backups
    if os.path.exists(keys_dir):
        for file in os.listdir(keys_dir):
            if file.startswith('keys') and file != 'keys.json':
                file_path = os.path.join(keys_dir, file)
                size = os.path.getsize(file_path)
                modified = datetime.fromtimestamp(os.path.getmtime(file_path))
                status["backup_files"].append({
                    "name": file,
                    "size": size,
                    "modified": modified.strftime("%Y-%m-%d %H:%M:%S")
                })
                
    # Vérifier le passphrase
    try:
        from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
        conn = frappe.get_doc("ebics Connection", connection_name)
        client = EbicsNode(conn)
        passphrase = client._get_passphrase()
        
        if passphrase == "*******":
            status["passphrase_status"] = "UI mask (using default)"
        elif passphrase:
            status["passphrase_status"] = f"Set ({len(passphrase)} chars)"
        else:
            status["passphrase_status"] = "Empty"
    except:
        status["passphrase_status"] = "Error checking"
        
    return status


def analyze_error(error_code: str, connection_name: str = None) -> Dict:
    """
    Analyser un code d'erreur EBICS
    
    Args:
        error_code: Code d'erreur EBICS
        connection_name: Nom de la connexion (optionnel)
        
    Returns:
        Dict avec l'analyse
    """
    error_meanings = {
        "000000": {
            "meaning": "Succès",
            "severity": "info",
            "action": "Aucune action requise"
        },
        "061001": {
            "meaning": "Authentification échouée / Non activé",
            "severity": "warning",
            "action": "Attendre l'activation de la banque ou vérifier les clés"
        },
        "061002": {
            "meaning": "Signature invalide",
            "severity": "error",
            "action": "Vérifier les clés et régénérer si nécessaire"
        },
        "090003": {
            "meaning": "Utilisateur inconnu",
            "severity": "error",
            "action": "Vérifier l'User ID avec la banque"
        },
        "090005": {
            "meaning": "Utilisateur verrouillé",
            "severity": "critical",
            "action": "Contacter la banque immédiatement"
        },
        "091001": {
            "meaning": "Type d'ordre inconnu",
            "severity": "error",
            "action": "Vérifier le type d'ordre supporté par la banque"
        },
        "091005": {
            "meaning": "Pas de données disponibles",
            "severity": "info",
            "action": "Normal - aucune transaction pour cette période"
        },
        "091115": {
            "meaning": "Ordre en cours de traitement",
            "severity": "info",
            "action": "Réessayer dans quelques minutes"
        },
        "091116": {
            "meaning": "Ordre déjà existant",
            "severity": "warning",
            "action": "L'ordre a déjà été soumis - vérifier l'historique"
        },
        "091301": {
            "meaning": "Compte bloqué",
            "severity": "critical",
            "action": "Contacter la banque - compte bancaire bloqué"
        }
    }
    
    analysis = error_meanings.get(error_code, {
        "meaning": "Code d'erreur inconnu",
        "severity": "unknown",
        "action": "Consulter la documentation EBICS"
    })
    
    analysis["code"] = error_code
    
    # Si une connexion est fournie, vérifier le contexte
    if connection_name:
        state = get_ebics_state(connection_name)
        
        # Recommandations spécifiques basées sur l'état
        if error_code == "061001":
            if not state["status"]["ini_sent"]:
                analysis["specific_action"] = "Envoyer INI d'abord"
            elif not state["status"]["hia_sent"]:
                analysis["specific_action"] = "Envoyer HIA après INI"
            elif not state["status"]["bank_activated"]:
                analysis["specific_action"] = "Attendre l'activation de la banque"
            else:
                analysis["specific_action"] = "Exécuter HPB pour récupérer les clés de la banque"
                
    return analysis


def dump_keys_info(connection_name: str, show_content: bool = False) -> None:
    """
    Afficher les informations sur les clés (sans exposer les clés)
    
    Args:
        connection_name: Nom de la connexion
        show_content: Si True, affiche un aperçu du contenu (dangereux!)
    """
    print(f"\n🔐 Informations sur les clés - {connection_name}")
    print("=" * 60)
    
    status = check_keys_status(connection_name)
    
    print(f"📁 Dossier existe: {status['directory_exists']}")
    print(f"📄 Fichier keys.json existe: {status['keys_file_exists']}")
    
    if status['keys_file_exists']:
        print(f"📊 Taille: {status['keys_file_size']} bytes")
        print(f"📅 Modifié: {status['keys_file_modified']}")
        print(f"🔧 Format: {status.get('keys_format', 'Inconnu')}")
        
    print(f"🔑 Passphrase: {status['passphrase_status']}")
    
    if status['backup_files']:
        print(f"\n📦 Fichiers de backup: {len(status['backup_files'])}")
        for backup in status['backup_files']:
            print(f"  - {backup['name']} ({backup['size']} bytes, {backup['modified']})")
            
    if show_content and status['keys_file_exists']:
        print("\n⚠️  APERÇU DU CONTENU (SENSIBLE!):")
        site_path = frappe.get_site_path()
        keys_file = os.path.join(
            site_path, "private", "files", "ebics_keys", 
            connection_name, "keys.json"
        )
        
        with open(keys_file, 'r') as f:
            content = f.read()
            # Afficher seulement les 100 premiers caractères
            print(f"  Début: {content[:100]}...")
            print(f"  Fin: ...{content[-100:]}")


def test_command_execution(connection_name: str) -> Dict:
    """
    Tester l'exécution d'une commande node-ebics-client
    
    Returns:
        Dict avec les résultats du test
    """
    from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
    import subprocess
    
    results = {
        "node_version": None,
        "npm_version": None,
        "node_ebics_installed": False,
        "command_test": None
    }
    
    # Vérifier Node.js
    try:
        result = subprocess.run(['node', '--version'], 
                              capture_output=True, text=True)
        results["node_version"] = result.stdout.strip()
    except:
        results["node_version"] = "Not installed"
        
    # Vérifier npm
    try:
        result = subprocess.run(['npm', '--version'], 
                              capture_output=True, text=True)
        results["npm_version"] = result.stdout.strip()
    except:
        results["npm_version"] = "Not installed"
        
    # Vérifier node-ebics-client
    try:
        result = subprocess.run(
            ['npm', 'list', 'node-ebics-client'],
            capture_output=True, text=True,
            cwd='/Users/jeremy/Downloads/node-ebics-client-master'
        )
        if 'node-ebics-client' in result.stdout:
            results["node_ebics_installed"] = True
    except:
        pass
        
    # Tester une commande simple
    try:
        conn = frappe.get_doc("ebics Connection", connection_name)
        client = EbicsNode(conn)
        
        # Essayer d'appeler _run_node_command avec une commande simple
        results["command_test"] = "Client created successfully"
    except Exception as e:
        results["command_test"] = f"Error: {e}"
        
    return results


def get_recent_errors(connection_name: str, days: int = 7) -> List[Dict]:
    """
    Obtenir les erreurs récentes pour une connexion
    
    Args:
        connection_name: Nom de la connexion
        days: Nombre de jours à regarder
        
    Returns:
        Liste des erreurs récentes
    """
    # Dans un vrai système, on lirait les logs
    # Ici on retourne un exemple
    return []


def calculate_workflow_progress(connection: Any) -> Dict:
    """
    Calculer la progression du workflow d'initialisation
    
    Args:
        connection: Document de connexion EBICS
        
    Returns:
        Dict avec la progression
    """
    steps = {
        "keys_generated": False,
        "ini_sent": connection.ini_sent,
        "hia_sent": connection.hia_sent,
        "hpb_done": False,
        "bank_activated": connection.bank_activated,
        "ready": False
    }
    
    # Vérifier si les clés existent
    site_path = frappe.get_site_path()
    keys_file = os.path.join(
        site_path, "private", "files", "ebics_keys",
        connection.name, "keys.json"
    )
    steps["keys_generated"] = os.path.exists(keys_file)
    
    # HPB est fait si la banque est activée (heuristique)
    steps["hpb_done"] = connection.bank_activated
    
    # Prêt si tout est fait
    steps["ready"] = all([
        steps["keys_generated"],
        steps["ini_sent"],
        steps["hia_sent"],
        steps["bank_activated"]
    ])
    
    # Calculer le pourcentage
    completed = sum(1 for v in steps.values() if v)
    total = len(steps)
    percentage = (completed / total) * 100
    
    return {
        "steps": steps,
        "completed": completed,
        "total": total,
        "percentage": percentage,
        "status": "Ready" if steps["ready"] else "In Progress"
    }


def debug_current_state(connection_name: str = "Raiffeisen") -> None:
    """
    Afficher un debug complet de l'état actuel
    
    Args:
        connection_name: Nom de la connexion
    """
    print("\n" + "=" * 60)
    print(f"🔍 ÉTAT DE DÉBOGAGE EBICS - {connection_name}")
    print("=" * 60)
    
    # État général
    state = get_ebics_state(connection_name)
    
    if "error" in state:
        print(f"❌ Erreur: {state['error']}")
        return
        
    # Connexion
    print("\n📡 CONNEXION:")
    for key, value in state["connection"].items():
        print(f"  {key}: {value}")
        
    # Statut
    print("\n📊 STATUT:")
    for key, value in state["status"].items():
        status_icon = "✅" if value else "⏳"
        print(f"  {status_icon} {key}: {value}")
        
    # Clés
    print("\n🔐 CLÉS:")
    keys = state["keys"]
    print(f"  Fichier existe: {keys['keys_file_exists']}")
    if keys['keys_file_exists']:
        print(f"  Taille: {keys['keys_file_size']} bytes")
        print(f"  Format: {keys.get('keys_format', 'Inconnu')}")
        print(f"  Passphrase: {keys['passphrase_status']}")
        
    # Progression
    print("\n📈 PROGRESSION:")
    progress = state["workflow_progress"]
    print(f"  Étapes complétées: {progress['completed']}/{progress['total']}")
    print(f"  Pourcentage: {progress['percentage']:.0f}%")
    print(f"  Statut: {progress['status']}")
    
    for step, done in progress["steps"].items():
        icon = "✅" if done else "⏳"
        print(f"    {icon} {step}")
        
    # Test de commande
    print("\n⚙️  ENVIRONNEMENT:")
    env = test_command_execution(connection_name)
    print(f"  Node.js: {env['node_version']}")
    print(f"  npm: {env['npm_version']}")
    print(f"  node-ebics-client: {'✅ Installé' if env['node_ebics_installed'] else '❌ Non installé'}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    import sys
    
    # Permettre l'exécution directe pour debug
    sys.path.append('/home/neoffice/frappe-bench/sites')
    frappe.init(site='prod.local')
    frappe.connect()
    
    # Debug complet par défaut
    debug_current_state()
    
    # Analyser une erreur spécifique si fournie
    if len(sys.argv) > 1:
        error_code = sys.argv[1]
        print(f"\n🔍 Analyse de l'erreur {error_code}:")
        analysis = analyze_error(error_code, "Raiffeisen")
        for key, value in analysis.items():
            print(f"  {key}: {value}")
    
    frappe.destroy()