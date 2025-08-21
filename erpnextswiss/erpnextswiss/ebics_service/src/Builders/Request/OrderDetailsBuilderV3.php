<?php

namespace EbicsApi\Ebics\Builders\Request;

use LogicException;

/**
 * Ebics 3.0 Class OrderDetailsBuilder builder for request container.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class OrderDetailsBuilderV3 extends OrderDetailsBuilder
{
    public function addOrderType(string $orderType): OrderDetailsBuilder
    {
        throw new LogicException('Unsupported yet');
    }

    public function addAdminOrderType(string $orderType): OrderDetailsBuilder
    {
        $this->appendElementTo('AdminOrderType', $orderType, $this->instance);

        return $this;
    }

    public function addOrderAttribute(
        string $orderAttribute
    ): OrderDetailsBuilder {
        throw new LogicException('Unsupported yet');
    }
}
