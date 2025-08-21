<?php

namespace EbicsApi\Ebics\Services;

use EbicsApi\Ebics\Contracts\HttpClientInterface;
use EbicsApi\Ebics\Exceptions\TimeoutEbicsException;
use EbicsApi\Ebics\Models\Http\Request;
use EbicsApi\Ebics\Models\Http\Response;
use RuntimeException;

/**
 * Curl Http client.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class CurlHttpClient extends HttpClient implements HttpClientInterface
{
    /**
     * @inheritDoc
     * @throws \EbicsApi\Ebics\Exceptions\TimeoutEbicsException
     */
    public function post(string $url, Request $request): Response
    {
        $body = $request->getContent();

        $ch = curl_init($url);
        if (false === $ch) {
            throw new RuntimeException('Can not create curl.');
        }
        curl_setopt($ch, CURLOPT_HTTPHEADER, [
            'Content-Type: ' . self::CONTENT_TYPE,
        ]);
        curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 0);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, 0);
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $body);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_FAILONERROR, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 400);
        $contents = curl_exec($ch);
        if (curl_errno($ch)) {
            $errorMsg = curl_error($ch);
        }
        curl_close($ch);

        if (!is_string($contents)) {
            throw new TimeoutEbicsException(
                'EBICS Bank response is not a string. Timeout is 400s. ' . ($errorMsg ?? '')
            );
        }

        return $this->createResponse($contents);
    }
}
