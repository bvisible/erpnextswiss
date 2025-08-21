<?php

namespace EbicsApi\Ebics\Models\Crypt;

/**
 * Key pair.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class KeyPair
{
    private Key $publicKey;

    private Key $privateKey;

    private string $password;

    public function __construct(Key $publicKey, Key $privateKey, string $password)
    {
        $this->publicKey = $publicKey;
        $this->privateKey = $privateKey;
        $this->password = $password;
    }

    public function getPublicKey(): Key
    {
        return $this->publicKey;
    }

    public function getPrivateKey(): Key
    {
        return $this->privateKey;
    }

    public function getPassword(): string
    {
        return $this->password;
    }
}
