<?php

namespace EbicsApi\Ebics\Models\Crypt;

/**
 * Key.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class Key
{
    /**
     * @var mixed|string
     */
    private $key;

    private int $type;

    /**
     * @param mixed|string $key
     * @param int $type
     */
    public function __construct($key, int $type)
    {
        $this->key = $key;
        $this->type = $type;
    }

    /**
     * @return mixed|string
     */
    public function getKey()
    {
        return $this->key;
    }

    public function getType(): int
    {
        return $this->type;
    }
}
