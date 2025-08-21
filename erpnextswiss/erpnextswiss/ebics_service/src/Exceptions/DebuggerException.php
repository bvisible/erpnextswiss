<?php

namespace EbicsApi\Ebics\Exceptions;

use Exception;

/**
 * DebuggerException class representation.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class DebuggerException extends Exception
{
    private string $url;
    private string $requestMessage;

    public function __construct(string $url, string $requestMessage)
    {
        $this->url = $url;
        $this->requestMessage = $requestMessage;

        parent::__construct();
    }

    public function getUrl(): string
    {
        return $this->url;
    }

    public function getRequestMessage(): string
    {
        return $this->requestMessage;
    }
}
