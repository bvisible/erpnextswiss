<?php

namespace EbicsApi\Ebics\Services;

use EbicsApi\Ebics\Contracts\KeyStorageLocatorInterface;
use EbicsApi\Ebics\Models\Crypt\Key;

/**
 * CryptoStorage.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class CryptoStorage
{
    /**
     * @var KeyStorageLocatorInterface
     */
    private KeyStorageLocatorInterface $keyStorageLocator;

    public function __construct(KeyStorageLocatorInterface $keyStorageLocator)
    {
        $this->keyStorageLocator = $keyStorageLocator;
    }

    /**
     * Write key into key storage.
     *
     * @param Key|null $key
     * @return string|null
     */
    public function writePublicKey(?Key $key): ?string
    {
        return $key ? $this->keyStorageLocator->locate($key->getKey())->writePublicKey($key) : null;
    }

    /**
     * Read key from key storage.
     *
     * @param string|null $key
     * @return Key|null
     */
    public function readPublicKey(?string $key): ?Key
    {
        return $key ? $this->keyStorageLocator->locate($key)->readPublicKey($key) : null;
    }

    /**
     * Write private key into key storage.
     *
     * @param Key|null $key
     * @return string|null
     */
    public function writePrivateKey(?Key $key): ?string
    {
        return $key ? $this->keyStorageLocator->locate($key->getKey())->writePrivateKey($key) : null;
    }

    /**
     * Read private key from key storage.
     *
     * @param string|null $key
     * @return Key|null
     */
    public function readPrivateKey(?string $key): ?Key
    {
        return $key ? $this->keyStorageLocator->locate($key)->readPrivateKey($key) : null;
    }

    /**
     * Write certificate into key storage.
     * @param string|null $certificate
     * @return string|null
     */
    public function writeCertificate(?string $certificate): ?string
    {
        return $certificate ? $this->keyStorageLocator->locate($certificate)->writeCertificate($certificate) : null;
    }

    /**
     * Read certificate from key storage.
     *
     * @param string|null $certificate
     * @return string|null
     */
    public function readCertificate(?string $certificate): ?string
    {
        return $certificate ? $this->keyStorageLocator->locate($certificate)->readCertificate($certificate) : null;
    }
}
