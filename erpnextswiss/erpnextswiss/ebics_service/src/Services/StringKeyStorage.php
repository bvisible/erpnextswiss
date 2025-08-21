<?php

namespace EbicsApi\Ebics\Services;

use EbicsApi\Ebics\Contracts\KeyStorageInterface;
use EbicsApi\Ebics\Models\Crypt\Key;
use EbicsApi\Ebics\Models\Crypt\RSA;

/**
 * StringKeyStorage.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class StringKeyStorage implements KeyStorageInterface
{
    /**
     * @inheritDoc
     */
    public function writePublicKey(Key $key): string
    {
        return base64_encode($key->getKey());
    }

    /**
     * @inheritDoc
     */
    public function readPublicKey(string $key): Key
    {
        return new Key(base64_decode($key), RSA::PUBLIC_FORMAT_PKCS1);
    }

    /**
     * @inheritDoc
     */
    public function writePrivateKey(Key $key): string
    {
        return base64_encode($key->getKey());
    }

    /**
     * @inheritDoc
     */
    public function readPrivateKey(string $key): Key
    {
        return new Key(base64_decode($key), RSA::PRIVATE_FORMAT_PKCS1);
    }

    /**
     * @inheritDoc
     */
    public function writeCertificate(string $certificate): string
    {
        return base64_encode($certificate);
    }

    /**
     * @inheritDoc
     */
    public function readCertificate(string $certificate): string
    {
        return base64_decode($certificate);
    }
}
