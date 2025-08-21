<?php

namespace EbicsApi\Ebics\Factories;

use EbicsApi\Ebics\Builders\Request\OrderDetailsBuilder;
use EbicsApi\Ebics\Builders\Request\RequestBuilder;
use EbicsApi\Ebics\Builders\Request\RootBuilderV30;
use EbicsApi\Ebics\Models\Http\Request;

/**
 * Ebics 3.0 RequestFactory.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class RequestFactoryV30 extends RequestFactory
{
    public function createRequestBuilderInstance(): RequestBuilder
    {
        return $this->requestBuilder
            ->createInstance(function (Request $request) {
                return new RootBuilderV30($this->zipService, $this->cryptService, $request);
            });
    }

    public function addOrderType(
        OrderDetailsBuilder $orderDetailsBuilder,
        string $orderType,
        string $orderAttribute
    ): OrderDetailsBuilder {
        return $orderDetailsBuilder->addAdminOrderType($orderType);
    }
}
