<?php

namespace EbicsApi\Ebics\Handlers\Traits;

/**
 * Trait H003Trait settings.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
trait H003Trait
{
    public function getH00XVersion(): string
    {
        return 'H003';
    }

    public function getH00XNamespace(): string
    {
        return 'http://www.ebics.org/H003';
    }

    public function getS00XVersion(): string
    {
        return 'S001';
    }
}
