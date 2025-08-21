<?php

namespace EbicsApi\Ebics\Models\Order;

use EbicsApi\Ebics\Contracts\Order\InitializationOrderInterface;

/**
 * DownloadOrder abstract class.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
abstract class InitializationOrder extends Order implements InitializationOrderInterface
{
    public function prepareContext(): void
    {
        $this->context = $this->requestFactory->prepareRequestContext($this->context);
    }

    public function afterExecute(InitializationOrderResult $orderResult): void
    {
        // Stub for hook.
    }
}
