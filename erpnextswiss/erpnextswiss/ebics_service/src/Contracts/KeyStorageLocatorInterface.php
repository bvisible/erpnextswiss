<?php

namespace EbicsApi\Ebics\Contracts;

/**
 * KeyStorageLocatorInterface.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
interface KeyStorageLocatorInterface
{
    public const LOCATE_STRING = 'string';

    /**
     * Find appropriate key storage.
     *
     * @param mixed|string $value
     *
     * @return KeyStorageInterface
     */
    public function locate($value): KeyStorageInterface;

    /**
     * Get key storage.
     *
     * @param string $key
     *
     * @return KeyStorageInterface
     */
    public function get(string $key): KeyStorageInterface;
}
