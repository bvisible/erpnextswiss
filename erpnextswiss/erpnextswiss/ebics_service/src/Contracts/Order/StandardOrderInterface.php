<?php

namespace EbicsApi\Ebics\Contracts\Order;

use EbicsApi\Ebics\Models\Order\StandardOrderResult;

/**
 * EBICS StandardOrderInterface representation.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
interface StandardOrderInterface extends OrderInterface
{
    public function afterExecute(StandardOrderResult $orderResult): void;
}
