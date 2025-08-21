<?php

namespace EbicsApi\Ebics\Models\Order;

use EbicsApi\Ebics\Contracts\Order\DownloadOrderInterface;
use LogicException;

/**
 * DownloadOrder abstract class.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
abstract class DownloadOrder extends Order implements DownloadOrderInterface
{
    public function prepareContext(): void
    {
        $this->context = $this->requestFactory->prepareRequestContext($this->context);
    }

    public function afterExecute(DownloadOrderResult $orderResult): void
    {
        // Stub for hook.
    }

    public function copyContext(Order $target): void
    {
        if (!($target instanceof DownloadOrderInterface)) {
            throw new LogicException('Invalid order context');
        }
        parent::copyContext($target);
    }
}
