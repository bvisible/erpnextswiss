<?php

namespace EbicsApi\Ebics\Builders\Request;

use Closure;
use DOMDocument;
use DOMElement;
use EbicsApi\Ebics\Services\CryptService;
use EbicsApi\Ebics\Services\ZipService;

/**
 * Class RootBuilder builder for request container.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
abstract class RootBuilder extends XmlBuilder
{
    private const EBICS_REQUEST = 'ebicsRequest';
    private const EBICS_UNSECURED_REQUEST = 'ebicsUnsecuredRequest';
    private const EBICS_UNSIGNED_REQUEST = 'ebicsUnsignedRequest';
    private const EBICS_NO_PUB_KEY_DIGESTS = 'ebicsNoPubKeyDigestsRequest';
    private const EBICS_HEV = 'ebicsHEVRequest';

    private const SECURED_MAP = [
        self::EBICS_REQUEST => true,
        self::EBICS_UNSECURED_REQUEST => false,
        self::EBICS_UNSIGNED_REQUEST => false,
        self::EBICS_NO_PUB_KEY_DIGESTS => true,
        self::EBICS_HEV => false,
    ];

    protected ZipService $zipService;
    protected CryptService $cryptService;
    protected DOMElement $instance;

    public function __construct(
        ZipService $zipService,
        CryptService $cryptService,
        DOMDocument $dom
    ) {
        $this->zipService = $zipService;
        $this->cryptService = $cryptService;
        parent::__construct($dom);
    }

    public function createUnsecured(): RootBuilder
    {
        return $this->createH00X(self::EBICS_UNSECURED_REQUEST);
    }

    public function createSecuredNoPubKeyDigests(): RootBuilder
    {
        return $this->createH00X(self::EBICS_NO_PUB_KEY_DIGESTS);
    }

    public function createSecured(): RootBuilder
    {
        return $this->createH00X(self::EBICS_REQUEST);
    }

    public function createUnsigned(): RootBuilder
    {
        return $this->createH00X(self::EBICS_UNSIGNED_REQUEST);
    }

    abstract public function getH00XVersion(): string;

    abstract public function getH00XNamespace(): string;

    private function createH00X(string $container): RootBuilder
    {
        $secured = self::SECURED_MAP[$container];

        $this->instance = $this->createEmptyElement($container, [
            'Version' => $this->getH00XVersion(),
            'Revision' => '1',
        ], $this->getH00XNamespace());
        if ($secured) {
            $this->instance->setAttributeNS(
                'http://www.w3.org/2000/xmlns/',
                'xmlns:ds',
                'http://www.w3.org/2000/09/xmldsig#'
            );
        }
        $this->instance->setAttributeNS(
            'http://www.w3.org/2001/XMLSchema-instance',
            'xsi:schemaLocation',
            'http://www.ebics.org/' . $this->getH00XVersion() .
            ' http://www.ebics.org/' . $this->getH00XVersion() . '/ebics_' . $this->getH00XVersion() . '.xsd'
        );

        return $this;
    }

    public function createHEV(): RootBuilder
    {
        return $this->createH000(self::EBICS_HEV);
    }

    private function createH000(string $container): RootBuilder
    {
        $this->instance = $this->createEmptyElement($container, [], 'http://www.ebics.org/H000');
        $this->instance->setAttributeNS(
            'http://www.w3.org/2001/XMLSchema-instance',
            'xsi:schemaLocation',
            'http://www.ebics.org/H000 http://www.ebics.org/H000/ebics_hev.xsd'
        );

        return $this;
    }

    abstract public function addHeader(Closure $callback): RootBuilder;

    abstract public function addBody(?Closure $callback = null): RootBuilder;

    public function addHostId(string $hostId): RootBuilder
    {
        $this->appendElementTo('HostID', $hostId, $this->instance);

        return $this;
    }

    public function getInstance(): DOMElement
    {
        return $this->instance;
    }

    public function isSecured(string $container): bool
    {
        return self::SECURED_MAP[$container];
    }
}
