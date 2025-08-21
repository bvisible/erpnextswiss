<?php

namespace EbicsApi\Ebics\Models\Order;

use EbicsApi\Ebics\Models\InitializationTransaction;
use EbicsApi\Ebics\Models\XmlDocument;

/**
 * Order result with extracted data.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class InitializationOrderResult extends OrderResult
{
    private XmlDocument $document;

    private InitializationTransaction $transaction;

    public function setDocument(XmlDocument $document): void
    {
        $this->document = $document;
    }

    public function getDocument(): ?XmlDocument
    {
        return $this->document;
    }

    public function setTransaction(InitializationTransaction $transaction): void
    {
        $this->transaction = $transaction;
    }

    public function getTransaction(): InitializationTransaction
    {
        return $this->transaction;
    }
}
