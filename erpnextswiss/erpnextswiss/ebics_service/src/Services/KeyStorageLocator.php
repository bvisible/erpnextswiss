<?php

namespace EbicsApi\Ebics\Services;

use EbicsApi\Ebics\Contracts\KeyStorageInterface;
use EbicsApi\Ebics\Contracts\KeyStorageLocatorInterface;

/**
 * KeyStorageLocator.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class KeyStorageLocator implements KeyStorageLocatorInterface
{
    /**
     * @var array<string, KeyStorageInterface>
     */
    private array $locateMap;

    public function __construct(?array $locateMap = null)
    {
        $this->locateMap = $locateMap ?? [
            KeyStorageLocatorInterface::LOCATE_STRING => new StringKeyStorage(),
        ];
    }

    public function locate($value): KeyStorageInterface
    {
        $type = is_object($value) ? get_class($value) : gettype($value);

        return $this->locateMap[$type];
    }

    public function get(string $key): KeyStorageInterface
    {
        return $this->locateMap[$key];
    }
}
