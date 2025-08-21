# Tests ebics Connection

## Structure des Tests

```
erpnextswiss/erpnextswiss/doctype/ebics_connection/test/
├── README.md                    # Ce fichier
├── __init__.py                  # Module Python
├── test_suite.py               # Suite de tests principale
├── test_connection.py           # Tests de connexion et authentification
├── test_keys.py                 # Tests de gestion des clés
├── test_initialization.py      # Tests INI, HIA, HPB
├── test_statements.py           # Tests Z52, Z53, C52, C53
├── test_error_handling.py      # Tests de gestion d'erreurs
└── debug_tools.py              # Outils de debug

```

## Utilisation

### Exécuter tous les tests
```bash
cd /home/neoffice/frappe-bench
bench --site prod.local run-tests --app erpnextswiss --module erpnextswiss.erpnextswiss.doctype.ebics_connection.test
```

### Exécuter la suite complète
```bash
bench --site prod.local execute erpnextswiss.erpnextswiss.doctype.ebics_connection.test.test_suite.run_test_suite
```

### Exécuter un test spécifique
```bash
bench --site prod.local execute erpnextswiss.erpnextswiss.doctype.ebics_connection.test.test_connection.run_tests
```

### Mode debug
```bash
bench --site prod.local execute erpnextswiss.erpnextswiss.doctype.ebics_connection.test.debug_tools.debug_current_state
```

## Tests Disponibles

### 1. Connection Tests (`test_connection.py`)
- Test de connexion basique
- Test avec mauvais credentials
- Test de timeout
- Test de reconnexion

### 2. Keys Tests (`test_keys.py`)
- Génération de clés
- Sauvegarde et restauration
- Chiffrement/déchiffrement
- Gestion du passphrase
- Migration de format

### 3. Initialization Tests (`test_initialization.py`)
- Workflow complet d'activation
- INI, HIA, HPB individuels
- Génération lettre INI
- Vérification activation

### 4. Statements Tests (`test_statements.py`)
- Download Z53 avec différentes dates
- Download Z52 intraday
- Gestion des erreurs "no data"
- Test de performances

### 5. ~~Payments Tests~~ (non créé - à implémenter)
- Upload pain.001
- Vérification statut
- Gestion des rejets
- Test avec différents formats

### 6. Error Handling Tests (`test_error_handling.py`)
- Tous les codes d'erreur EBICS
- Retry logic
- Logging des erreurs
- Recovery procedures

### 7. ~~Parsing Tests~~ (non créé - à implémenter)
- Parse CAMT.053
- Parse CAMT.052
- Extract transactions
- Match avec factures

## Outils de Debug

### État actuel
```python
from erpnextswiss.erpnextswiss.doctype.ebics_connection.test.debug_tools import get_ebics_state
state = get_ebics_state("Raiffeisen")
print(state)
```

### Analyser une erreur
```python
from erpnextswiss.erpnextswiss.doctype.ebics_connection.test.debug_tools import analyze_error
analyze_error("061001", "Raiffeisen")
```

### Dumper les clés (sans les exposer)
```python
from erpnextswiss.erpnextswiss.doctype.ebics_connection.test.debug_tools import dump_keys_info
dump_keys_info("Raiffeisen")
```