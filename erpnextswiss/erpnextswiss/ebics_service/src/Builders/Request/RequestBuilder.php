<?php

namespace EbicsApi\Ebics\Builders\Request;

use Closure;
use EbicsApi\Ebics\Handlers\AuthSignatureHandler;
use EbicsApi\Ebics\Models\Http\Request;
use EbicsApi\Ebics\Services\SchemaValidator;

/**
 * Class RequestBuilder builder for model @see \EbicsApi\Ebics\Models\Http\Request
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class RequestBuilder
{
    private AuthSignatureHandler $authSignatureHandler;
    private ?Request $instance;
    private RootBuilder $rootBuilder;
    private SchemaValidator $validator;

    public function __construct(AuthSignatureHandler $authSignatureHandler, SchemaValidator $validator)
    {
        $this->authSignatureHandler = $authSignatureHandler;
        $this->validator = $validator;
    }

    public function createInstance(Closure $callback): RequestBuilder
    {
        $this->instance = new Request();

        $this->rootBuilder = call_user_func($callback, $this->instance);

        return $this;
    }

    public function addContainerUnsecured(Closure $callback): RequestBuilder
    {
        $this->instance->appendChild($this->rootBuilder->createUnsecured()->getInstance());

        call_user_func($callback, $this->rootBuilder);

        return $this;
    }

    public function addContainerSecuredNoPubKeyDigests(Closure $callback): RequestBuilder
    {
        $this->instance->appendChild($this->rootBuilder->createSecuredNoPubKeyDigests()->getInstance());

        call_user_func($callback, $this->rootBuilder);

        return $this;
    }

    public function addContainerSecured(Closure $callback): RequestBuilder
    {
        $this->instance->appendChild($this->rootBuilder->createSecured()->getInstance());

        call_user_func($callback, $this->rootBuilder);

        return $this;
    }

    public function addContainerUnsigned(Closure $callback): RequestBuilder
    {
        $this->instance->appendChild($this->rootBuilder->createUnsigned()->getInstance());

        call_user_func($callback, $this->rootBuilder);

        return $this;
    }

    public function addContainerHEV(Closure $callback): RequestBuilder
    {
        $this->instance->appendChild($this->rootBuilder->createHEV()->getInstance());

        call_user_func($callback, $this->rootBuilder);

        return $this;
    }

    public function popInstance(): Request
    {
        if ($this->rootBuilder->isSecured($this->instance->documentElement->tagName)) {
            $this->authSignatureHandler->handle($this->instance);
        }

        $this->validator->validate($this->instance);

        $instance = $this->instance;
        $this->instance = null;

        return $instance;
    }
}
