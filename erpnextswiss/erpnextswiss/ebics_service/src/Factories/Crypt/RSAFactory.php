<?php

namespace EbicsApi\Ebics\Factories\Crypt;

use EbicsApi\Ebics\Contracts\Crypt\BigIntegerInterface;
use EbicsApi\Ebics\Contracts\Crypt\RSAInterface;
use EbicsApi\Ebics\Models\Crypt\Key;
use EbicsApi\Ebics\Models\Crypt\RSA;

/**
 * Class RSAFactory represents producers for the @see RSA.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class RSAFactory
{
    /**
     * @var array<int, class-string<RSAInterface>>
     */
    private array $classMap;

    /**
     * @param array<int, class-string<RSAInterface>> $classMap
     */
    public function __construct(?array $classMap = null)
    {
        $this->classMap = $classMap ?? [
            RSA::PRIVATE_FORMAT_PKCS1 => RSA::class,
            RSA::PUBLIC_FORMAT_PKCS1 => RSA::class,
        ];
    }

    /**
     * @param int $type
     * @return RSAInterface
     */
    public function create(int $type): RSAInterface
    {
        return new $this->classMap[$type]();
    }

    /**
     * Create RSA from private key.
     *
     * @param Key $privateKey
     * @param string $password
     * @return RSAInterface
     */
    public function createPrivate(Key $privateKey, string $password): RSAInterface
    {
        $rsa = $this->create($privateKey->getType());
        $rsa->setPassword($password);
        $rsa->loadKey($privateKey->getKey(), $privateKey->getType());

        return $rsa;
    }

    /**
     * Create RSA from public key.
     *
     * @param Key $publicKey
     * @return RSAInterface
     */
    public function createPublic(Key $publicKey): RSAInterface
    {
        $rsa = $this->create($publicKey->getType());
        $rsa->loadKey($publicKey->getKey());
        $rsa->setPublicKey();

        return $rsa;
    }

    /**
     * Composite public key.
     * @param BigIntegerInterface $modulus
     * @param BigIntegerInterface $exponent
     * @param int $type
     * @return RSAInterface
     */
    public function compositePublicKey(
        BigIntegerInterface $modulus,
        BigIntegerInterface $exponent,
        int $type
    ): RSAInterface {
        $rsa = $this->create($type);
        $rsa->loadKey(['n' => $modulus, 'e' => $exponent]);
        $rsa->setPublicKey();

        return $rsa;
    }
}
