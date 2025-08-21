<?php

namespace EbicsApi\Ebics\Models\Order;

use EbicsApi\Ebics\Contracts\Order\UploadOrderInterface;
use EbicsApi\Ebics\Contracts\OrderDataInterface;
use EbicsApi\Ebics\Models\UploadTransaction;
use LogicException;

/**
 * UploadOrder abstract class.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
abstract class UploadOrder extends Order implements UploadOrderInterface
{
    protected OrderDataInterface $orderData;

    protected UploadTransaction $transaction;

    public function prepareContext(): void
    {
        $this->context = $this->requestFactory->prepareRequestContext($this->context);
    }

    public function setTransaction(UploadTransaction $transaction): void
    {
        $this->transaction = $transaction;
    }

    public function getOrderData(): OrderDataInterface
    {
        return $this->orderData;
    }

    public function afterExecute(UploadOrderResult $orderResult): void
    {
        // Stub for hook.
    }

    public function copyContext(Order $target): void
    {
        if (!($target instanceof UploadOrderInterface)) {
            throw new LogicException('Invalid order context');
        }
        parent::copyContext($target);
        $target->setTransaction($this->transaction);
    }
}
