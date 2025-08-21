<?php

namespace EbicsApi\Ebics\Builders\Request;

use DOMElement;

/**
 * Class MutableBuilder builder for request container.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class MutableBuilder extends XmlBuilder
{
    const PHASE_INITIALIZATION = 'Initialisation';
    const PHASE_RECEIPT = 'Receipt';
    const PHASE_TRANSFER = 'Transfer';

    private DOMElement $instance;

    /**
     * Create body for UnsecuredRequest.
     *
     * @return $this
     */
    public function createInstance(): MutableBuilder
    {
        $this->instance = $this->createEmptyElement('mutable');

        return $this;
    }

    public function addTransactionPhase(string $transactionPhase): MutableBuilder
    {
        $this->appendElementTo('TransactionPhase', $transactionPhase, $this->instance);

        return $this;
    }

    public function addSegmentNumber(?int $segmentNumber = null, ?bool $isLastSegment = null): MutableBuilder
    {
        if (null !== $segmentNumber) {
            $this->appendElementTo('SegmentNumber', (string)$segmentNumber, $this->instance, [
                'lastSegment' => $isLastSegment ? 'true' : 'false',
            ]);
        }

        return $this;
    }

    public function getInstance(): DOMElement
    {
        return $this->instance;
    }
}
