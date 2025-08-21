<?php

namespace EbicsApi\Ebics\Exceptions;

/**
 * MethodNotImplemented error
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class MethodNotImplemented extends EbicsException
{
    public function __construct(string $version)
    {
        parent::__construct('Method not impelmented for EBICS ' . $version);
    }
}
