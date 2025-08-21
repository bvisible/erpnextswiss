<?php

namespace EbicsApi\Ebics\Services;

use EbicsApi\Ebics\Contracts\HttpClientInterface;
use EbicsApi\Ebics\Exceptions\DebuggerException;
use EbicsApi\Ebics\Models\Http\Request;
use EbicsApi\Ebics\Models\Http\Response;

/**
 * Class DebuggerHttpClient.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class DebuggerHttpClient implements HttpClientInterface
{

    public function post(string $url, Request $request): Response
    {
        throw new DebuggerException($url, $request->getContent());
    }
}
