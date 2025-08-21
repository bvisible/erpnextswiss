<?php

namespace EbicsApi\Ebics\Contracts;

use EbicsApi\Ebics\Models\Crypt\Key;

/**
 * KeyStorageInterface.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
interface KeyStorageInterface
{
    /**
     * Write public key to storage.
     *
     * @param Key $key
     *
     * @return string
     */
    public function writePublicKey(Key $key): string;

    /**
     * Read public key from storage.
     *
     * @param string $key
     *
     * @return Key
     */
    public function readPublicKey(string $key): Key;

    /**
     * Write private key to storage.
     *
     * @param Key $key
     *
     * @return string
     */
    public function writePrivateKey(Key $key): string;

    /**
     * Read private key from storage.
     *
     * @param string $key
     *
     * @return Key
     */
    public function readPrivateKey(string $key): Key;

    /**
     * Write certificate to storage.
     *
     * @param string $certificate
     *
     * @return string
     */
    public function writeCertificate(string $certificate): string;

    /**
     * Read certificate from storage.
     *
     * @param string $certificate
     *
     * @return string
     */
    public function readCertificate(string $certificate): string;
}
