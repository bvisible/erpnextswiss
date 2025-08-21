<?php

namespace EbicsApi\Ebics\Builders\Request;

use LogicException;

/**
 * Ebics 2.4/2.5 Class OrderDetailsBuilder builder for request container.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class OrderDetailsBuilderV2 extends OrderDetailsBuilder
{
    public function addOrderType(string $orderType): OrderDetailsBuilder
    {
        $this->appendElementTo('OrderType', $orderType, $this->instance);

        return $this;
    }

    public function addAdminOrderType(string $orderType): OrderDetailsBuilder
    {
        throw new LogicException('Unsupported yet');
    }

    public function addOrderAttribute(string $orderAttribute): OrderDetailsBuilder
    {
        $this->appendElementTo('OrderAttribute', $orderAttribute, $this->instance);

        return $this;
    }
}
