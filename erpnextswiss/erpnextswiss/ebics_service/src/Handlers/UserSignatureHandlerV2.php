<?php

namespace EbicsApi\Ebics\Handlers;

use EbicsApi\Ebics\Models\UserSignature;

/**
 * Ebics 2.5 Class AuthSignatureHandler manage body DOM elements.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 *
 * @internal
 */
final class UserSignatureHandlerV2 extends UserSignatureHandler
{
    public function handleXml(UserSignature $xml, string $digest): void
    {
        $ns = 'http://www.ebics.org/S001';

        // Add UserSignatureData to root.
        $xmlUserSignatureData = $xml->createElementNS(
            $ns,
            'UserSignatureData'
        );
        $xmlUserSignatureData->setAttributeNS(
            'http://www.w3.org/2000/xmlns/',
            'xmlns:xsi',
            'http://www.w3.org/2001/XMLSchema-instance'
        );
        $xmlUserSignatureData->setAttributeNS(
            'http://www.w3.org/2001/XMLSchema-instance',
            'xsi:schemaLocation',
            'http://www.ebics.org/S001 http://www.ebics.org/S001/ebics_signature.xsd'
        );
        $xml->appendChild($xmlUserSignatureData);

        // Add OrderSignatureData to UserSignatureData.
        $xmlOrderSignatureData = $xml->createElementNS($ns, 'OrderSignatureData');
        $xmlUserSignatureData->appendChild($xmlOrderSignatureData);

        // Add SignatureVersion to OrderSignatureData.
        $xmlSignatureVersion = $xml->createElementNS($ns, 'SignatureVersion');
        $xmlSignatureVersion->nodeValue = $this->keyring->getUserSignatureAVersion();
        $xmlOrderSignatureData->appendChild($xmlSignatureVersion);

        $canonicalizedUserSignatureDataHashSigned = $this->cryptService->encrypt(
            $this->keyring->getUserSignatureA()->getPrivateKey(),
            $this->keyring->getPassword(),
            $this->keyring->getUserSignatureAVersion(),
            $digest
        );
        $signatureValueNodeValue = base64_encode($canonicalizedUserSignatureDataHashSigned);

        // Add SignatureValue to OrderSignatureData.
        $xmlSignatureValue = $xml->createElementNS($ns, 'SignatureValue');
        $xmlSignatureValue->nodeValue = $signatureValueNodeValue;
        $xmlOrderSignatureData->appendChild($xmlSignatureValue);

        $this->insertAfter($xmlSignatureValue, $xmlSignatureVersion);

        // Add PartnerID to OrderSignatureData.
        $xmlPartnerID = $xml->createElementNS($ns, 'PartnerID');
        $xmlPartnerID->nodeValue = $this->user->getPartnerId();
        $xmlOrderSignatureData->appendChild($xmlPartnerID);

        // Add UserID to OrderSignatureData.
        $xmlUserID = $xml->createElementNS($ns, 'UserID');
        $xmlUserID->nodeValue = $this->user->getUserId();
        $xmlOrderSignatureData->appendChild($xmlUserID);
    }
}
