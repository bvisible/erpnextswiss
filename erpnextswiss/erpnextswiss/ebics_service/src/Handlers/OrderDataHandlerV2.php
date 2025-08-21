<?php

namespace EbicsApi\Ebics\Handlers;

use DateTimeInterface;
use DOMDocument;
use DOMElement;
use DOMNode;
use DOMNodeList;
use EbicsApi\Ebics\Contracts\SignatureInterface;
use EbicsApi\Ebics\Models\Crypt\X509;
use EbicsApi\Ebics\Models\XmlData;
use EbicsApi\Ebics\Models\XmlDocument;
use EbicsApi\Ebics\Services\DOMHelper;

/**
 * Ebics 2.x OrderDataHandler.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 *
 * @internal
 */
abstract class OrderDataHandlerV2 extends OrderDataHandler
{
    public function handleSignaturePubKey(
        DOMElement $xmlSignaturePubKeyInfo,
        XmlData $xml,
        SignatureInterface $certificateA,
        DateTimeInterface $dateTime,
        ?string $ns = null
    ): void {
        $this->handlePubKeyValue($xmlSignaturePubKeyInfo, $xml, $certificateA, $dateTime, $ns);
    }

    public function handleAuthenticationPubKey(
        DOMElement $xmlAuthenticationPubKeyInfo,
        XmlData $xml,
        SignatureInterface $certificateX,
        DateTimeInterface $dateTime,
        ?string $ns = null
    ): void {
        $this->handlePubKeyValue($xmlAuthenticationPubKeyInfo, $xml, $certificateX, $dateTime, $ns);
    }

    public function handleEncryptionPubKey(
        DOMElement $xmlEncryptionPubKeyInfo,
        XmlData $xml,
        SignatureInterface $certificateE,
        DateTimeInterface $dateTime,
        ?string $ns = null
    ): void {
        $this->handlePubKeyValue($xmlEncryptionPubKeyInfo, $xml, $certificateE, $dateTime, $ns);
    }

    /**
     * Add PubKeyValue to PublicKeyInfo XML Node.
     */
    private function handlePubKeyValue(
        DOMNode $xmlPublicKeyInfo,
        DOMDocument $xml,
        SignatureInterface $signature,
        ?DateTimeInterface $dateTime,
        ?string $ns = null
    ): void {
        $publicKeyDetails = $this->cryptService->decomposePublicKey($signature->getPublicKey());
        $nsPrefix = null === $ns ? '' : $ns . ':';

        // Add PubKeyValue to Signature.
        $xmlPubKeyValue = $xml->createElement($nsPrefix . 'PubKeyValue');
        $xmlPublicKeyInfo->appendChild($xmlPubKeyValue);

        // Add ds:RSAKeyValue to PubKeyValue.
        $xmlRSAKeyValue = $xml->createElement('ds:RSAKeyValue');
        $xmlPubKeyValue->appendChild($xmlRSAKeyValue);

        // Add ds:Modulus to ds:RSAKeyValue.
        $xmlModulus = $xml->createElement('ds:Modulus');
        $xmlModulus->nodeValue = base64_encode($publicKeyDetails['m']);
        $xmlRSAKeyValue->appendChild($xmlModulus);

        // Add ds:Exponent to ds:RSAKeyValue.
        $xmlExponent = $xml->createElement('ds:Exponent');
        $xmlExponent->nodeValue = base64_encode($publicKeyDetails['e']);
        $xmlRSAKeyValue->appendChild($xmlExponent);

        // Add TimeStamp to PubKeyValue.
        $xmlTimeStamp = $xml->createElement($nsPrefix . 'TimeStamp');
        $xmlTimeStamp->nodeValue = $dateTime->format('Y-m-d\TH:i:s\Z');
        $xmlPubKeyValue->appendChild($xmlTimeStamp);
    }

    public function retrieveAuthenticationSignature(XmlDocument $document): SignatureInterface
    {
        $h00x = $this->getH00XVersion();
        $xpath = $this->prepareH00XXPath($document);

        $x509Certificate = $xpath->query("//$h00x:AuthenticationPubKeyInfo/ds:X509Data/ds:X509Certificate");
        if ($x509Certificate instanceof DOMNodeList && 0 !== $x509Certificate->length) {
            $x509CertificateValue = DOMHelper::safeItemValue($x509Certificate);
            $x509CertificateValueDe = base64_decode($x509CertificateValue);

            $certificateContent
                = "-----BEGIN CERTIFICATE-----\n" .
                chunk_split($x509CertificateValue, 64) .
                "-----END CERTIFICATE-----\n";

            $x509 = new X509();
            $x509->loadX509($x509CertificateValueDe);

            $publicKey = $x509->getPublicKey();

            $signature = $this->signatureFactory->createSignatureXFromDetails(
                $publicKey->getModulus(),
                $publicKey->getExponent()
            );

            $signature->setCertificateContent($certificateContent);
        } else {
            $modulus = $xpath->query("//$h00x:AuthenticationPubKeyInfo/$h00x:PubKeyValue/ds:RSAKeyValue/ds:Modulus");
            $modulusValue = DOMHelper::safeItemValue($modulus);
            $modulusValueDe = base64_decode($modulusValue);
            $exponent = $xpath->query("//$h00x:AuthenticationPubKeyInfo/$h00x:PubKeyValue/ds:RSAKeyValue/ds:Exponent");
            $exponentValue = DOMHelper::safeItemValue($exponent);
            $exponentValueDe = base64_decode($exponentValue);

            $signature = $this->signatureFactory->createSignatureXFromDetails(
                $this->bigIntegerFactory->create($modulusValueDe, 256),
                $this->bigIntegerFactory->create($exponentValueDe, 256)
            );
        }

        return $signature;
    }

    public function retrieveEncryptionSignature(XmlData $document): SignatureInterface
    {
        $h00x = $this->getH00XVersion();
        $xpath = $this->prepareH00XXPath($document);

        $x509Certificate = $xpath->query("//$h00x:EncryptionPubKeyInfo/ds:X509Data/ds:X509Certificate");
        if ($x509Certificate instanceof DOMNodeList && 0 !== $x509Certificate->length) {
            $x509CertificateValue = DOMHelper::safeItemValue($x509Certificate);
            $x509CertificateValueDe = base64_decode($x509CertificateValue);

            $certificateContent
                = "-----BEGIN CERTIFICATE-----\n" .
                chunk_split($x509CertificateValue, 64) .
                "-----END CERTIFICATE-----\n";

            $x509 = new X509();
            $x509->loadX509($x509CertificateValueDe);

            $publicKey = $x509->getPublicKey();

            $signature = $this->signatureFactory->createSignatureEFromDetails(
                $publicKey->getModulus(),
                $publicKey->getExponent()
            );

            $signature->setCertificateContent($certificateContent);
        } else {
            $modulus = $xpath->query("//$h00x:EncryptionPubKeyInfo/$h00x:PubKeyValue/ds:RSAKeyValue/ds:Modulus");
            $modulusValue = DOMHelper::safeItemValue($modulus);
            $modulusValueDe = base64_decode($modulusValue);
            $exponent = $xpath->query("//$h00x:EncryptionPubKeyInfo/$h00x:PubKeyValue/ds:RSAKeyValue/ds:Exponent");
            $exponentValue = DOMHelper::safeItemValue($exponent);
            $exponentValueDe = base64_decode($exponentValue);

            $signature = $this->signatureFactory->createSignatureEFromDetails(
                $this->bigIntegerFactory->create($modulusValueDe, 256),
                $this->bigIntegerFactory->create($exponentValueDe, 256)
            );
        }

        return $signature;
    }
}
