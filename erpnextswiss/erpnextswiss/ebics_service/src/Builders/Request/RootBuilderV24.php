<?php

namespace EbicsApi\Ebics\Builders\Request;

use Closure;
use EbicsApi\Ebics\Handlers\Traits\H003Trait;

/**
 * Ebics 2.4 RootBuilder.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class RootBuilderV24 extends RootBuilder
{
    use H003Trait;

    public function addHeader(Closure $callback): RootBuilder
    {
        $headerBuilder = new HeaderBuilderV2($this->cryptService, $this->dom);
        $header = $headerBuilder->createInstance()->getInstance();
        $this->instance->appendChild($header);

        call_user_func($callback, $headerBuilder);

        return $this;
    }

    public function addBody(?Closure $callback = null): RootBuilder
    {
        $bodyBuilder = new BodyBuilderV2($this->zipService, $this->cryptService, $this->dom);
        $body = $bodyBuilder->createInstance()->getInstance();
        $this->instance->appendChild($body);

        if (null !== $callback) {
            call_user_func($callback, $bodyBuilder);
        }

        return $this;
    }
}
