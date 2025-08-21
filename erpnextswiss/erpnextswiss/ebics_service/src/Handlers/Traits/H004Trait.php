<?php

namespace EbicsApi\Ebics\Handlers\Traits;

/**
 * Trait H004Trait settings.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
trait H004Trait
{
    public function getH00XVersion(): string
    {
        return 'H004';
    }

    public function getH00XNamespace(): string
    {
        return 'urn:org:ebics:H004';
    }

    public function getS00XVersion(): string
    {
        return 'S001';
    }
}
