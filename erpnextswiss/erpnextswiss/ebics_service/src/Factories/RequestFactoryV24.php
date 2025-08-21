<?php

namespace EbicsApi\Ebics\Factories;

use EbicsApi\Ebics\Builders\Request\OrderDetailsBuilder;
use EbicsApi\Ebics\Builders\Request\RequestBuilder;
use EbicsApi\Ebics\Builders\Request\RootBuilderV24;
use EbicsApi\Ebics\Models\Http\Request;

/**
 * Ebics 2.4 RequestFactory.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class RequestFactoryV24 extends RequestFactory
{
    public function createRequestBuilderInstance(): RequestBuilder
    {
        return $this->requestBuilder
            ->createInstance(function (Request $request) {
                return new RootBuilderV24($this->zipService, $this->cryptService, $request);
            });
    }

    public function addOrderType(
        OrderDetailsBuilder $orderDetailsBuilder,
        string $orderType,
        string $orderAttribute
    ): OrderDetailsBuilder {
        $orderId = $this->cryptService->generateOrderId();

        return $orderDetailsBuilder
            ->addOrderType($orderType)
            ->addOrderId($orderId)
            ->addOrderAttribute($orderAttribute);
    }
}
