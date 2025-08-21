<?php

namespace EbicsApi\Ebics\Builders\Request;

use Closure;
use DOMDocument;
use DOMElement;
use EbicsApi\Ebics\Services\CryptService;

/**
 * Class HeaderBuilder builder for request container.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
abstract class HeaderBuilder extends XmlBuilder
{
    protected CryptService $cryptService;
    protected DOMElement $instance;

    public function __construct(CryptService $cryptService, DOMDocument $dom)
    {
        $this->cryptService = $cryptService;
        parent::__construct($dom);
    }

    public function createInstance(): HeaderBuilder
    {
        $this->instance = $this->createEmptyElement('header', ['authenticate' => 'true']);

        return $this;
    }

    abstract public function addStatic(Closure $callback): HeaderBuilder;

    public function addMutable(?Closure $callable = null): HeaderBuilder
    {
        $mutableBuilder = new MutableBuilder($this->dom);
        $this->instance->appendChild($mutableBuilder->createInstance()->getInstance());

        if (null !== $callable) {
            call_user_func($callable, $mutableBuilder);
        }

        return $this;
    }

    public function getInstance(): DOMElement
    {
        return $this->instance;
    }
}
