# EBICS Test Suite

## Overview

This directory contains the test suite for the EBICS integration using ebics-client-php.

## Test Files

### 1. `test_ebics_workflow.py`
Complete workflow test that validates the entire EBICS initialization process:
- Key generation
- INI/HIA sending
- Letter generation
- HPB download (with proper failure before activation)

### 2. `test_hpb_authentication.py`
Specific test for HPB authentication that verifies:
- HPB correctly fails with error 091002 when not activated
- Proper error messages are returned
- Security is enforced

### 3. `test_direct_php.py`
Direct PHP service test that bypasses the Python manager:
- Tests the PHP service directly
- Useful for debugging PHP-specific issues
- Validates HMAC authentication

## Running Tests

### From Bench (Recommended)

```bash
# Run complete workflow test
bench --site prod.local execute erpnextswiss.erpnextswiss.tests.ebics.test_ebics_workflow.run_ebics_workflow_tests

# Run HPB authentication test
bench --site prod.local execute erpnextswiss.erpnextswiss.tests.ebics.test_hpb_authentication.run_hpb_test

# Run direct PHP test
bench --site prod.local execute erpnextswiss.erpnextswiss.tests.ebics.test_direct_php.run_php_tests
```

### Direct Python Execution

```bash
cd /home/neoffice/frappe-bench
python3 -m erpnextswiss.erpnextswiss.tests.ebics.test_hpb_authentication
```

## Expected Results

### HPB Test (Before Activation)
```
✓ SUCCESS: HPB correctly returns authentication error!
   - Error: EBICS_AUTHENTICATION_FAILED
   - Code: 091002
   - Message: The bank has not yet activated your EBICS access
```

### Workflow Test
```
[TEST 1] Generate EBICS Keys          ✓
[TEST 2] Send INI Order               ✓
[TEST 3] Send HIA Order               ✓
[TEST 4] Generate INI Letter          ✓
[TEST 5] Download HPB (Before)        ✓ (fails as expected)
```

## Test Environment

Tests are configured to use the **Credit Suisse Test** connection by default:
- Host: CSCHZZ12
- URL: https://cs-ebics-service-test.credit-suisse.com/ebics/ebics
- Version: H005

## Security Notes

- Tests use HMAC-SHA256 for secure communication
- Secret keys are generated per request
- No credentials are hardcoded
- HPB correctly enforces bank activation requirement

## Troubleshooting

### PHP Execution Errors
Check PHP service logs:
```bash
tail -f /var/log/php/error.log
```

### Key Storage Issues
Verify key directory exists:
```bash
ls -la sites/prod.local/private/files/ebics_keys/
```

### Permission Issues
Ensure correct ownership:
```bash
chown -R neoffice:neoffice sites/prod.local/private/files/ebics_keys/
```

## Contributing

When adding new tests:
1. Follow the existing naming convention
2. Include clear documentation
3. Test both success and failure scenarios
4. Ensure tests are idempotent
5. Add test to this README