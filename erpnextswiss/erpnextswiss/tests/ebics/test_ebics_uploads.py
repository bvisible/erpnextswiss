#!/usr/bin/env python3
"""
Test EBICS upload operations (CCT, CDD, FUL)
"""

import json
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def generate_test_pain001():
    """Generate a test pain.001 XML for credit transfer"""
    timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    msg_id = f"TEST-CCT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03">
    <CstmrCdtTrfInitn>
        <GrpHdr>
            <MsgId>{msg_id}</MsgId>
            <CreDtTm>{timestamp}</CreDtTm>
            <NbOfTxs>1</NbOfTxs>
            <CtrlSum>100.00</CtrlSum>
            <InitgPty>
                <Nm>Test Company AG</Nm>
            </InitgPty>
        </GrpHdr>
        <PmtInf>
            <PmtInfId>PMT-001</PmtInfId>
            <PmtMtd>TRF</PmtMtd>
            <BtchBookg>true</BtchBookg>
            <NbOfTxs>1</NbOfTxs>
            <CtrlSum>100.00</CtrlSum>
            <PmtTpInf>
                <SvcLvl>
                    <Cd>SEPA</Cd>
                </SvcLvl>
            </PmtTpInf>
            <ReqdExctnDt>{datetime.now().strftime('%Y-%m-%d')}</ReqdExctnDt>
            <Dbtr>
                <Nm>Test Company AG</Nm>
            </Dbtr>
            <DbtrAcct>
                <Id>
                    <IBAN>CH5604835012345678009</IBAN>
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
                    <EndToEndId>E2E-001</EndToEndId>
                </PmtId>
                <Amt>
                    <InstdAmt Ccy="CHF">100.00</InstdAmt>
                </Amt>
                <Cdtr>
                    <Nm>Recipient Company</Nm>
                </Cdtr>
                <CdtrAcct>
                    <Id>
                        <IBAN>CH5609000000100123456</IBAN>
                    </Id>
                </CdtrAcct>
                <RmtInf>
                    <Ustrd>Test payment from EBICS test suite</Ustrd>
                </RmtInf>
            </CdtTrfTxInf>
        </PmtInf>
    </CstmrCdtTrfInitn>
</Document>"""

def generate_test_pain008():
    """Generate a test pain.008 XML for direct debit"""
    timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    msg_id = f"TEST-CDD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.008.001.02">
    <CstmrDrctDbtInitn>
        <GrpHdr>
            <MsgId>{msg_id}</MsgId>
            <CreDtTm>{timestamp}</CreDtTm>
            <NbOfTxs>1</NbOfTxs>
            <CtrlSum>50.00</CtrlSum>
            <InitgPty>
                <Nm>Test Company AG</Nm>
            </InitgPty>
        </GrpHdr>
        <PmtInf>
            <PmtInfId>DD-001</PmtInfId>
            <PmtMtd>DD</PmtMtd>
            <BtchBookg>true</BtchBookg>
            <NbOfTxs>1</NbOfTxs>
            <CtrlSum>50.00</CtrlSum>
            <PmtTpInf>
                <SvcLvl>
                    <Cd>SEPA</Cd>
                </SvcLvl>
                <LclInstrm>
                    <Cd>CORE</Cd>
                </LclInstrm>
                <SeqTp>FRST</SeqTp>
            </PmtTpInf>
            <ReqdColltnDt>{datetime.now().strftime('%Y-%m-%d')}</ReqdColltnDt>
            <Cdtr>
                <Nm>Test Company AG</Nm>
            </Cdtr>
            <CdtrAcct>
                <Id>
                    <IBAN>CH5604835012345678009</IBAN>
                </Id>
            </CdtrAcct>
            <CdtrAgt>
                <FinInstnId>
                    <BIC>CRESCHZZ80A</BIC>
                </FinInstnId>
            </CdtrAgt>
            <CdtrSchmeId>
                <Id>
                    <PrvtId>
                        <Othr>
                            <Id>CH12ZZZ12345678</Id>
                            <SchmeNm>
                                <Prtry>SEPA</Prtry>
                            </SchmeNm>
                        </Othr>
                    </PrvtId>
                </Id>
            </CdtrSchmeId>
            <DrctDbtTxInf>
                <PmtId>
                    <InstrId>DD-INSTR-001</InstrId>
                    <EndToEndId>DD-E2E-001</EndToEndId>
                </PmtId>
                <InstdAmt Ccy="CHF">50.00</InstdAmt>
                <DrctDbtTx>
                    <MndtRltdInf>
                        <MndtId>MANDATE-001</MndtId>
                        <DtOfSgntr>2024-01-01</DtOfSgntr>
                    </MndtRltdInf>
                </DrctDbtTx>
                <Dbtr>
                    <Nm>Debtor Company</Nm>
                </Dbtr>
                <DbtrAcct>
                    <Id>
                        <IBAN>CH5609000000100987654</IBAN>
                    </Id>
                </DbtrAcct>
                <RmtInf>
                    <Ustrd>Test direct debit from EBICS test suite</Ustrd>
                </RmtInf>
            </DrctDbtTxInf>
        </PmtInf>
    </CstmrDrctDbtInitn>
</Document>"""

def test_upload_order(connection_name, order_type, xml_content=None):
    """Test a specific upload order"""
    try:
        from ebics_manager import EbicsManager
        
        print(f"\n{'='*60}")
        print(f"Testing {order_type} upload")
        print(f"Connection: {connection_name}")
        print(f"{'='*60}")
        
        manager = EbicsManager(connection_name)
        
        # Generate appropriate test XML if not provided
        if not xml_content:
            if order_type == 'CCT':
                xml_content = generate_test_pain001()
                print("Generated test pain.001 XML")
            elif order_type == 'CDD':
                xml_content = generate_test_pain008()
                print("Generated test pain.008 XML")
            elif order_type == 'FUL':
                xml_content = "<test>Generic test file content</test>"
                print("Generated generic test XML")
        
        params = {
            'xml_content': xml_content
        }
        
        print(f"XML length: {len(xml_content)} characters")
        
        result = manager.execute_order(order_type, **params)
        
        print(f"\nResult:")
        print(json.dumps(result, indent=2))
        
        if result.get('success'):
            print(f"✅ {order_type} upload successful")
            if result.get('transaction_id'):
                print(f"   Transaction ID: {result['transaction_id']}")
        else:
            print(f"❌ {order_type} upload failed: {result.get('error')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error testing {order_type}: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

def test_all_uploads(connection_name):
    """Test all upload order types"""
    
    # Order types to test
    order_types = ['CCT', 'CDD', 'FUL']
    
    results = {}
    success_count = 0
    
    print(f"\n{'='*60}")
    print(f"EBICS Upload Tests - Starting")
    print(f"{'='*60}")
    
    for order_type in order_types:
        result = test_upload_order(connection_name, order_type)
        results[order_type] = result
        if result.get('success'):
            success_count += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Test Summary")
    print(f"{'='*60}")
    print(f"Total tests: {len(order_types)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {len(order_types) - success_count}")
    
    for order_type, result in results.items():
        status = "✅" if result.get('success') else "❌"
        error_msg = result.get('error', 'Unknown')
        if 'debug' in result:
            error_msg += f" (Debug: {result['debug']})"
        print(f"{status} {order_type}: {result.get('message', error_msg)}")
    
    return results

if __name__ == "__main__":
    # Get connection name from command line or use default
    connection_name = sys.argv[1] if len(sys.argv) > 1 else "Entwicklung CS"
    
    # Test all uploads
    test_all_uploads(connection_name)