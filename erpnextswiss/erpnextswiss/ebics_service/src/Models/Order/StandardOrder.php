<?php

namespace EbicsApi\Ebics\Models\Order;

use EbicsApi\Ebics\Contracts\Order\StandardOrderInterface;

/**
 * StandardOrder abstract class.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
abstract class StandardOrder extends Order implements StandardOrderInterface
{
    public function prepareContext(): void
    {
        $this->context = $this->requestFactory->prepareRequestContext($this->context);
    }

    public function afterExecute(StandardOrderResult $orderResult): void
    {
        // Stub for hook.
    }
}
