<?php

namespace EbicsApi\Ebics\Builders\Request;

/**
 * Ebics 3.0 Class DataTransferBuilder builder for request container.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class DataTransferBuilderV3 extends DataTransferBuilder
{
    public function addDataDigest(string $signatureVersion, ?string $digest = null): DataTransferBuilder
    {
        $xmlDataDigest = $this->appendEmptyElementTo('DataDigest', $this->instance, [
            'SignatureVersion' => $signatureVersion,
        ]);

        if (null !== $digest) {
            $xmlDataDigest->nodeValue = base64_encode($digest);
        }

        return $this;
    }

    public function addAdditionalOrderInfo(): DataTransferBuilder
    {
        $this->appendEmptyElementTo('AdditionalOrderInfo', $this->instance);

        return $this;
    }
}
