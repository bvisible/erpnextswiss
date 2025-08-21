<?php

namespace EbicsApi\Ebics\Models\Order;

use EbicsApi\Ebics\Models\Http\Response;

/**
 * Order result with extracted data.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class StandardOrderResult extends OrderResult
{
    private Response $response;

    public function setResponse(Response $xmlData): void
    {
        $this->response = $xmlData;
    }

    public function getResponse(): Response
    {
        return $this->response;
    }
}
