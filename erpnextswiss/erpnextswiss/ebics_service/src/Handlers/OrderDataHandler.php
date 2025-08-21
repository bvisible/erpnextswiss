<?php

namespace EbicsApi\Ebics\Handlers;

use DateTimeInterface;
use DOMDocument;
use DOMElement;
use DOMNode;
use EbicsApi\Ebics\Contracts\SignatureInterface;
use EbicsApi\Ebics\Exceptions\CertificateEbicsException;
use EbicsApi\Ebics\Factories\CertificateX509Factory;
use EbicsApi\Ebics\Factories\Crypt\BigIntegerFactory;
use EbicsApi\Ebics\Factories\SignatureFactory;
use EbicsApi\Ebics\Handlers\Traits\H00XTrait;
use EbicsApi\Ebics\Models\User;
use EbicsApi\Ebics\Models\XmlData;
use EbicsApi\Ebics\Models\XmlDocument;
use EbicsApi\Ebics\Services\CryptService;

/**
 * Class OrderDataHandler manages OrderData DOM elements.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 *
 * @internal
 */
abstract class OrderDataHandler
{
    use H00XTrait;

    private User $user;
    protected CryptService $cryptService;
    protected SignatureFactory $signatureFactory;
    private CertificateX509Factory $certificateX509Factory;
    protected BigIntegerFactory $bigIntegerFactory;

    public function __construct(
        User $user,
        CryptService $cryptService,
        SignatureFactory $signatureFactory,
        CertificateX509Factory $certificateX509Factory,
        BigIntegerFactory $bigIntegerFactory
    ) {
        $this->user = $user;
        $this->cryptService = $cryptService;
        $this->signatureFactory = $signatureFactory;
        $this->certificateX509Factory = $certificateX509Factory;
        $this->bigIntegerFactory = $bigIntegerFactory;
    }

    abstract public function handleSignaturePubKey(
        DOMElement $xmlSignaturePubKeyInfo,
        XmlData $xml,
        SignatureInterface $certificateA,
        DateTimeInterface $dateTime,
        ?string $ns = null
    ): void;


    abstract public function handleAuthenticationPubKey(
        DOMElement $xmlAuthenticationPubKeyInfo,
        XmlData $xml,
        SignatureInterface $certificateX,
        DateTimeInterface $dateTime,
        ?string $ns = null
    ): void;

    abstract public function handleEncryptionPubKey(
        DOMElement $xmlEncryptionPubKeyInfo,
        XmlData $xml,
        SignatureInterface $certificateE,
        DateTimeInterface $dateTime,
        ?string $ns = null
    ): void;

    /**
     * Add ds:X509Data to PublicKeyInfo XML Node.
     *
     * @throws CertificateEbicsException
     */
    public function handleX509Data(DOMNode $xmlPublicKeyInfo, DOMDocument $xml, SignatureInterface $certificate): void
    {
        if (!($certificateContent = $certificate->getCertificateContent())) {
            throw new CertificateEbicsException('Certificate X509 is empty.');
        }
        $certificateX509 = $this->certificateX509Factory->createFromContent($certificateContent);

        // Add ds:X509Data to Signature.
        $xmlX509Data = $xml->createElement('ds:X509Data');
        $xmlPublicKeyInfo->appendChild($xmlX509Data);

        // Add ds:X509IssuerSerial to ds:X509Data.
        $xmlX509IssuerSerial = $xml->createElement('ds:X509IssuerSerial');
        $xmlX509Data->appendChild($xmlX509IssuerSerial);

        // Add ds:X509IssuerName to ds:X509IssuerSerial.
        $xmlX509IssuerName = $xml->createElement('ds:X509IssuerName');
        $xmlX509IssuerName->nodeValue = $certificateX509->getIssuerName();
        $xmlX509IssuerSerial->appendChild($xmlX509IssuerName);

        // Add ds:X509SerialNumber to ds:X509IssuerSerial.
        $xmlX509SerialNumber = $xml->createElement('ds:X509SerialNumber');
        $xmlX509SerialNumber->nodeValue = $certificateX509->getSerialNumber();
        $xmlX509IssuerSerial->appendChild($xmlX509SerialNumber);

        // Add ds:X509Certificate to ds:X509Data.
        $xmlX509Certificate = $xml->createElement('ds:X509Certificate');
        $certificateContent = $certificate->getCertificateContent();
        $certificateContent = trim(
            str_replace(
                ['-----BEGIN CERTIFICATE-----', '-----END CERTIFICATE-----', "\n", "\r"],
                '',
                $certificateContent
            )
        );
        $xmlX509Certificate->nodeValue = $certificateContent;
        $xmlX509Data->appendChild($xmlX509Certificate);
    }

    /**
     * Add PartnerID to OrderData XML Node.
     */
    public function handlePartnerId(DOMNode $xmlOrderData, DOMDocument $xml): void
    {
        $xmlPartnerID = $xml->createElement('PartnerID');
        $xmlPartnerID->nodeValue = $this->user->getPartnerId();
        $xmlOrderData->appendChild($xmlPartnerID);
    }

    /**
     * Add UserID to OrderData XML Node.
     */
    public function handleUserId(DOMNode $xmlOrderData, DOMDocument $xml): void
    {
        $xmlUserID = $xml->createElement('UserID');
        $xmlUserID->nodeValue = $this->user->getUserId();
        $xmlOrderData->appendChild($xmlUserID);
    }

    /**
     * Extract Authentication Certificate from the $orderData.
     */
    abstract public function retrieveAuthenticationSignature(XmlDocument $document): SignatureInterface;

    /**
     * Extract Encryption Certificate from the $orderData.
     */
    abstract public function retrieveEncryptionSignature(XmlDocument $document): SignatureInterface;

    public function hash(string $content): string
    {
        return $this->cryptService->hash($content);
    }
}
