<?php

namespace EbicsApi\Ebics\Contracts\Order;

use EbicsApi\Ebics\Models\Order\DownloadOrderResult;

/**
 * EBICS DownloadOrderInterface representation.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
interface DownloadOrderInterface extends OrderInterface
{
    public function getParserFormat(): string;

    public function afterExecute(DownloadOrderResult $orderResult): void;
}
