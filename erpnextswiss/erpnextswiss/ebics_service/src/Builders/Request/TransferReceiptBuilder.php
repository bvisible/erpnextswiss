<?php

namespace EbicsApi\Ebics\Builders\Request;

use DOMElement;

/**
 * Class TransferReceiptBuilder builder for request container.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class TransferReceiptBuilder extends XmlBuilder
{
    // The value of the acknowledgement is 0 (“positive acknowledgement”)
    // if download and processing of the order data was successful
    const CODE_RECEIPT_POSITIVE = '0';

    // Otherwise the value of the acknowledgement is 1 (“negative acknowledgement”).
    const CODE_RECEIPT_NEGATIVE = '1';

    private DOMElement $instance;

    public function createInstance(): TransferReceiptBuilder
    {
        $this->instance = $this->createEmptyElement('TransferReceipt', ['authenticate' => 'true']);

        return $this;
    }

    public function addReceiptCode(string $receiptCode): TransferReceiptBuilder
    {
        $this->appendElementTo('ReceiptCode', $receiptCode, $this->instance);

        return $this;
    }

    public function getInstance(): DOMElement
    {
        return $this->instance;
    }
}
