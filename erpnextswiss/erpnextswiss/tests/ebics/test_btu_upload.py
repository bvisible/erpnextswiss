#!/usr/bin/env python3
"""
Test BTU upload for EBICS 3.0 (H005)
"""

import frappe
import json
from datetime import datetime

def test_btu_cct_upload():
    """Test BTU upload with CCT (Credit Transfer) for EBICS 3.0"""
    
    # Sample pain.001 XML for testing
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03">
    <CstmrCdtTrfInitn>
        <GrpHdr>
            <MsgId>TEST-BTU-{}</MsgId>
            <CreDtTm>{}</CreDtTm>
            <NbOfTxs>1</NbOfTxs>
            <CtrlSum>1000.00</CtrlSum>
            <InitgPty>
                <Nm>Test Company AG</Nm>
                <Id>
                    <OrgId>
                        <Othr>
                            <Id>CHE123456789</Id>
                        </Othr>
                    </OrgId>
                </Id>
            </InitgPty>
        </GrpHdr>
        <PmtInf>
            <PmtInfId>PAYMENT-BTU-001</PmtInfId>
            <PmtMtd>TRF</PmtMtd>
            <NbOfTxs>1</NbOfTxs>
            <CtrlSum>1000.00</CtrlSum>
            <ReqdExctnDt>{}</ReqdExctnDt>
            <Dbtr>
                <Nm>Test Debtor AG</Nm>
                <PstlAdr>
                    <Ctry>CH</Ctry>
                </PstlAdr>
            </Dbtr>
            <DbtrAcct>
                <Id>
                    <IBAN>CH9300762011623852957</IBAN>
                </Id>
            </DbtrAcct>
            <DbtrAgt>
                <FinInstnId>
                    <BIC>CRESCHZZ80A</BIC>
                </FinInstnId>
            </DbtrAgt>
            <CdtTrfTxInf>
                <PmtId>
                    <InstrId>INSTR-001</InstrId>
                    <EndToEndId>E2E-REF-001</EndToEndId>
                </PmtId>
                <Amt>
                    <InstdAmt Ccy="CHF">1000.00</InstdAmt>
                </Amt>
                <Cdtr>
                    <Nm>Test Creditor GmbH</Nm>
                    <PstlAdr>
                        <Ctry>CH</Ctry>
                    </PstlAdr>
                </Cdtr>
                <CdtrAcct>
                    <Id>
                        <IBAN>CH4431999123000889012</IBAN>
                    </Id>
                </CdtrAcct>
                <RmtInf>
                    <Ustrd>Test BTU Payment via EBICS 3.0</Ustrd>
                </RmtInf>
            </CdtTrfTxInf>
        </PmtInf>
    </CstmrCdtTrfInitn>
</Document>""".format(
        datetime.now().strftime("%Y%m%d%H%M%S"),
        datetime.now().isoformat(),
        datetime.now().strftime("%Y-%m-%d")
    )
    
    return xml_content

def test_btu_upload_with_manager(connection_name='Credit Suisse Test Platform'):
    """Test BTU upload using EbicsManager"""
    
    from erpnextswiss.erpnextswiss.ebics_manager import EbicsManager
    
    # Get test XML
    xml_content = test_btu_cct_upload()
    
    print("=" * 60)
    print("Testing BTU Upload for EBICS 3.0")
    print("=" * 60)
    print(f"Connection: {connection_name}")
    print(f"XML Length: {len(xml_content)} characters")
    print(f"EBICS Version: H005 (3.0)")
    
    try:
        # Create manager
        manager = EbicsManager(connection_name)
        
        # Execute CCT upload using BTU for EBICS 3.0
        result = manager.execute_order('CCT', xml_content=xml_content)
        
        print("\nResult:")
        print(json.dumps(result, indent=2))
        
        if result.get('success'):
            print("\n✅ BTU upload successful!")
            print(f"Transaction ID: {result.get('transaction_id')}")
        else:
            print(f"\n❌ BTU upload failed: {result.get('error')}")
            
        return result
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

def test_direct_php_btu():
    """Test BTU upload directly via PHP service"""
    
    import subprocess
    import tempfile
    import os
    
    xml_content = test_btu_cct_upload()
    
    # Write XML to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
        f.write(xml_content)
        xml_file = f.name
    
    try:
        # Create PHP test script for BTU
        php_script = r"""<?php
require_once '/home/neoffice/frappe-bench/apps/erpnextswiss/erpnextswiss/ebics_php/vendor/autoload.php';

use EbicsApi\Ebics\EbicsClient;
use EbicsApi\Ebics\Models\Bank;
use EbicsApi\Ebics\Models\User;
use EbicsApi\Ebics\Services\ArrayKeyringManager;
use EbicsApi\Ebics\Orders\BTU;
use EbicsApi\Ebics\Contexts\BTUContext;
use EbicsApi\Ebics\Models\XmlDocument;

$keyringPath = '/home/neoffice/frappe-bench/sites/prod.local/private/files/ebics_keys/Credit Suisse Test Platform/keyring.json';
$xmlFile = $argv[1];

try {
    $keyringData = json_decode(file_get_contents($keyringPath), true);
    $xmlContent = file_get_contents($xmlFile);
    
    // Force VERSION_30 for EBICS 3.0
    $keyringData['VERSION'] = 'VERSION_30';
    
    $bank = new Bank('TESTHOST', 'https://example-bank.com/ebics', 'H005');
    $user = new User('CRS08141', 'CRS08141');
    
    $keyringManager = new ArrayKeyringManager();
    $keyring = $keyringManager->loadKeyring($keyringData, 'testtesttest', 'VERSION_30');
    
    $client = new EbicsClient($bank, $user, $keyring);
    
    // Create BTU context for CCT
    $btuContext = new BTUContext();
    $btuContext->setServiceName('CCT');
    $btuContext->setScope('CH');
    $btuContext->setServiceOption('pain.001');
    $btuContext->setMsgName('pain.001.001.03');
    $btuContext->setFileName('payment_' . date('YmdHis') . '.xml');
    
    // Create order data
    $orderData = new XmlDocument();
    $orderData->loadXML($xmlContent);
    
    // Create and execute BTU order
    $btuOrder = new BTU($btuContext, $orderData);
    $result = $client->executeUploadOrder($btuOrder);
    
    echo json_encode(['success' => true, 'transactionId' => $result->getTransactionId()]);
} catch (Exception $e) {
    echo json_encode(['success' => false, 'error' => $e->getMessage()]);
}
"""
        
        # Write PHP script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.php', delete=False) as f:
            f.write(php_script)
            php_file = f.name
        
        # Execute PHP script
        result = subprocess.run(
            ['php', php_file, xml_file],
            capture_output=True,
            text=True
        )
        
        print("PHP Output:", result.stdout)
        if result.stderr:
            print("PHP Errors:", result.stderr)
            
        return json.loads(result.stdout) if result.stdout else {'success': False, 'error': 'No output'}
        
    finally:
        # Cleanup
        if os.path.exists(xml_file):
            os.unlink(xml_file)
        if 'php_file' in locals() and os.path.exists(php_file):
            os.unlink(php_file)

if __name__ == "__main__":
    # Test with manager
    print("\n" + "=" * 60)
    print("Test 1: Using EbicsManager")
    print("=" * 60)
    test_btu_upload_with_manager()
    
    # Test directly with PHP
    print("\n" + "=" * 60)
    print("Test 2: Direct PHP BTU Test")
    print("=" * 60)
    test_direct_php_btu()