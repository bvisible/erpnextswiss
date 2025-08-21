<?php

namespace EbicsApi\Ebics\Builders\Request;

use Closure;
use DateTimeInterface;
use DOMDocument;
use DOMElement;
use EbicsApi\Ebics\Services\CryptService;

/**
 * Class StaticBuilder builder for request container.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
abstract class StaticBuilder extends XmlBuilder
{
    const SECURITY_MEDIUM_0000 = '0000';
    const SECURITY_MEDIUM_0200 = '0200';

    protected DOMElement $instance;
    protected CryptService $cryptService;

    public function __construct(CryptService $cryptService, DOMDocument $dom)
    {
        $this->cryptService = $cryptService;
        parent::__construct($dom);
    }

    public function createInstance(): StaticBuilder
    {
        $this->instance = $this->createEmptyElement('static');

        return $this;
    }

    public function addHostId(string $hostId): StaticBuilder
    {
        $this->appendElementTo('HostID', $hostId, $this->instance);

        return $this;
    }

    public function addRandomNonce(): StaticBuilder
    {
        $this->appendElementTo('Nonce', $this->cryptService->generateNonce(), $this->instance);

        return $this;
    }

    public function addTimestamp(DateTimeInterface $dateTime): StaticBuilder
    {
        $milliseconds = (int)($dateTime->format('u') / 1000);

        $formatted = $dateTime->format('Y-m-d\TH:i:s') . sprintf('.%03dZ', $milliseconds);

        $this->appendElementTo('Timestamp', $formatted, $this->instance);

        return $this;
    }

    public function addPartnerId(string $partnerId): StaticBuilder
    {
        $this->appendElementTo('PartnerID', $partnerId, $this->instance);

        return $this;
    }

    public function addUserId(string $userId): StaticBuilder
    {
        $this->appendElementTo('UserID', $userId, $this->instance);

        return $this;
    }

    public function addSystemId(string $systemId): StaticBuilder
    {
        $this->appendElementTo('SystemID', $systemId, $this->instance);

        return $this;
    }

    public function addProduct(string $product, string $language): StaticBuilder
    {
        $this->appendElementTo('Product', $product, $this->instance, ['Language' => $language]);

        return $this;
    }

    abstract public function addOrderDetails(?Closure $callable = null): StaticBuilder;

    public function addNumSegments(int $numSegments): StaticBuilder
    {
        $this->appendElementTo('NumSegments', (string)$numSegments, $this->instance);

        return $this;
    }

    public function addBankPubKeyDigests(
        string $versionX,
        string $signXDigest,
        string $versionE,
        string $signEDigest,
        string $algorithm = 'sha256'
    ): StaticBuilder {
        $xmlBankPubKeyDigests = $this->appendEmptyElementTo('BankPubKeyDigests', $this->instance);

        $this->appendElementTo(
            'Authentication',
            base64_encode($signXDigest),
            $xmlBankPubKeyDigests,
            [
                'Version' => $versionX,
                'Algorithm' => sprintf('http://www.w3.org/2001/04/xmlenc#%s', $algorithm),
            ]
        );

        $this->appendElementTo(
            'Encryption',
            base64_encode($signEDigest),
            $xmlBankPubKeyDigests,
            [
                'Version' => $versionE,
                'Algorithm' => sprintf('http://www.w3.org/2001/04/xmlenc#%s', $algorithm),
            ]
        );

        return $this;
    }

    public function addSecurityMedium(string $securityMedium): StaticBuilder
    {
        $this->appendElementTo('SecurityMedium', $securityMedium, $this->instance);

        return $this;
    }

    public function addTransactionId(string $transactionId): StaticBuilder
    {
        $this->appendElementTo('TransactionID', $transactionId, $this->instance);

        return $this;
    }

    public function getInstance(): DOMElement
    {
        return $this->instance;
    }
}
