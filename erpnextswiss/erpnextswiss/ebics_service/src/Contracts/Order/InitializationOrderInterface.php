<?php

namespace EbicsApi\Ebics\Contracts\Order;

use EbicsApi\Ebics\Models\Order\InitializationOrderResult;

/**
 * EBICS InitializationOrderInterface representation.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
interface InitializationOrderInterface extends OrderInterface
{
    public function afterExecute(InitializationOrderResult $orderResult): void;
}
