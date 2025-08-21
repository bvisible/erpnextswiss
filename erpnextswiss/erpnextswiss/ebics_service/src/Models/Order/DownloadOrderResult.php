<?php

namespace EbicsApi\Ebics\Models\Order;

use EbicsApi\Ebics\Models\Transaction;
use EbicsApi\Ebics\Models\XmlDocument;

/**
 * Order result with extracted data.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class DownloadOrderResult extends OrderResult
{
    private array $dataFiles;
    private XmlDocument $document;
    private Transaction $transaction;

    /**
     * @param XmlDocument[]|string[] $dataFiles
     *
     * @return void
     */
    public function setDataFiles(array $dataFiles): void
    {
        $this->dataFiles = $dataFiles;
    }

    /**
     * @return XmlDocument[]|string[]|null
     */
    public function getDataFiles(): ?array
    {
        return $this->dataFiles;
    }

    public function setDocument(XmlDocument $document): void
    {
        $this->document = $document;
    }

    public function getDocument(): ?XmlDocument
    {
        return $this->document;
    }

    public function setTransaction(Transaction $transaction): void
    {
        $this->transaction = $transaction;
    }

    public function getTransaction(): Transaction
    {
        return $this->transaction;
    }
}
