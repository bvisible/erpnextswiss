#!/bin/bash

echo "Testing BTU Upload for EBICS 3.0 (H005)"
echo "========================================"

cd /home/neoffice/frappe-bench

# Test 1: Test BTU upload via Python
echo ""
echo "Test 1: BTU Upload via Python"
echo "------------------------------"
bench --site prod.local execute erpnextswiss.erpnextswiss.tests.ebics.test_btu_upload.test_btu_upload_with_manager

# Test 2: Direct test with minimal params
echo ""
echo "Test 2: Simple CCT Test"
echo "------------------------"
bench --site prod.local execute erpnextswiss.erpnextswiss.ebics_manager.execute_ebics_order \
    --kwargs "{'connection': 'Credit Suisse Test Platform', 'action': 'CCT', 'params': '{\"xml_content\": \"<?xml version=\\\"1.0\\\" encoding=\\\"UTF-8\\\"?><Document xmlns=\\\"urn:iso:std:iso:20022:tech:xsd:pain.001.001.03\\\"><CstmrCdtTrfInitn><GrpHdr><MsgId>TEST-BTU-001</MsgId></GrpHdr></CstmrCdtTrfInitn></Document>\"}'}"

echo ""
echo "Tests completed!"