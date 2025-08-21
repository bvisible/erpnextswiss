<?php

namespace EbicsApi\Ebics\Contracts\Order;

use EbicsApi\Ebics\Contracts\OrderDataInterface;
use EbicsApi\Ebics\Handlers\OrderDataHandler;
use EbicsApi\Ebics\Models\Order\UploadOrderResult;
use EbicsApi\Ebics\Models\UploadTransaction;

/**
 * EBICS UploadOrderInterface representation.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
interface UploadOrderInterface extends OrderInterface
{
    public function useOrderDataHandler(OrderDataHandler $orderDataHandler): void;

    public function setTransaction(UploadTransaction $transaction): void;

    public function getOrderData(): OrderDataInterface;

    public function afterExecute(UploadOrderResult $orderResult): void;
}
