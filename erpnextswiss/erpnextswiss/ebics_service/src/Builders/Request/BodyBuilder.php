<?php

namespace EbicsApi\Ebics\Builders\Request;

use Closure;
use DOMDocument;
use DOMElement;
use EbicsApi\Ebics\Services\CryptService;
use EbicsApi\Ebics\Services\ZipService;

/**
 * Class BodyBuilder builder for request container.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
abstract class BodyBuilder extends XmlBuilder
{
    protected ZipService $zipService;
    protected CryptService $cryptService;
    protected DOMElement $instance;

    public function __construct(ZipService $zipService, CryptService $cryptService, DOMDocument $dom)
    {
        $this->zipService = $zipService;
        $this->cryptService = $cryptService;
        parent::__construct($dom);
    }

    public function createInstance(): BodyBuilder
    {
        $this->instance = $this->createEmptyElement('body');

        return $this;
    }

    abstract public function addDataTransfer(Closure $callback): BodyBuilder;

    public function addTransferReceipt(Closure $callback): BodyBuilder
    {
        $transferReceiptBuilder = new TransferReceiptBuilder($this->dom);
        $this->instance->appendChild($transferReceiptBuilder->createInstance()->getInstance());

        call_user_func($callback, $transferReceiptBuilder);

        return $this;
    }

    public function getInstance(): DOMElement
    {
        return $this->instance;
    }
}
