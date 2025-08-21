<?php

namespace EbicsApi\Ebics\Factories;

use EbicsApi\Ebics\Contracts\Crypt\BigIntegerInterface;
use EbicsApi\Ebics\Contracts\SignatureInterface;
use EbicsApi\Ebics\Contracts\X509GeneratorInterface;
use EbicsApi\Ebics\Factories\Crypt\RSAFactory;
use EbicsApi\Ebics\Models\Crypt\Key;
use EbicsApi\Ebics\Models\Crypt\KeyPair;
use EbicsApi\Ebics\Models\Crypt\RSA;
use EbicsApi\Ebics\Models\Signature;
use LogicException;
use RuntimeException;

/**
 * Class SignatureFactory represents producers for the @see Signature.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin, Guillaume Sainthillier
 */
final class SignatureFactory
{
    private RSAFactory $rsaFactory;

    public function __construct(RSAFactory $rsaFactory)
    {
        $this->rsaFactory = $rsaFactory;
    }

    /**
     * @param string $type
     * @param Key $publicKey
     * @param Key|null $privateKey
     *
     * @return SignatureInterface
     */
    public function create(string $type, Key $publicKey, ?Key $privateKey = null): SignatureInterface
    {
        switch ($type) {
            case SignatureInterface::TYPE_A:
                $signature = $this->createSignatureA($publicKey, $privateKey);
                break;
            case SignatureInterface::TYPE_E:
                $signature = $this->createSignatureE($publicKey, $privateKey);
                break;
            case SignatureInterface::TYPE_X:
                $signature = $this->createSignatureX($publicKey, $privateKey);
                break;
            default:
                throw new LogicException('Unpredictable case.');
        }

        return $signature;
    }

    /**
     * @param Key $publicKey
     * @param Key $privateKey
     *
     * @return SignatureInterface
     */
    public function createSignatureA(Key $publicKey, Key $privateKey): SignatureInterface
    {
        return new Signature(SignatureInterface::TYPE_A, $publicKey, $privateKey);
    }

    /**
     * @param Key $publicKey
     * @param Key|null $privateKey
     *
     * @return SignatureInterface
     */
    public function createSignatureE(Key $publicKey, ?Key $privateKey = null): SignatureInterface
    {
        return new Signature(SignatureInterface::TYPE_E, $publicKey, $privateKey);
    }

    /**
     * @param Key $publicKey
     * @param Key|null $privateKey
     *
     * @return SignatureInterface
     */
    public function createSignatureX(Key $publicKey, ?Key $privateKey = null): SignatureInterface
    {
        return new Signature(SignatureInterface::TYPE_X, $publicKey, $privateKey);
    }

    /**
     * @param KeyPair $keyPair
     * @param X509GeneratorInterface|null $x509Generator
     *
     * @return SignatureInterface
     */
    public function createSignatureAFromKeys(
        KeyPair $keyPair,
        ?X509GeneratorInterface $x509Generator = null
    ): SignatureInterface {
        return $this->createSignatureFromKeys($keyPair, SignatureInterface::TYPE_A, $x509Generator);
    }

    /**
     * @param KeyPair $keyPair
     * @param X509GeneratorInterface|null $x509Generator
     *
     * @return SignatureInterface
     */
    public function createSignatureEFromKeys(
        KeyPair $keyPair,
        ?X509GeneratorInterface $x509Generator = null
    ): SignatureInterface {
        return $this->createSignatureFromKeys($keyPair, SignatureInterface::TYPE_E, $x509Generator);
    }

    /**
     * @param KeyPair $keyPair
     * @param X509GeneratorInterface|null $x509Generator
     *
     * @return SignatureInterface
     */
    public function createSignatureXFromKeys(
        KeyPair $keyPair,
        ?X509GeneratorInterface $x509Generator = null
    ): SignatureInterface {
        return $this->createSignatureFromKeys($keyPair, SignatureInterface::TYPE_X, $x509Generator);
    }

    /**
     * @param BigIntegerInterface $exponent
     * @param BigIntegerInterface $modulus
     *
     * @return SignatureInterface
     */
    public function createSignatureEFromDetails(
        BigIntegerInterface $exponent,
        BigIntegerInterface $modulus
    ): SignatureInterface {
        return $this->createCertificateFromDetails(SignatureInterface::TYPE_E, $exponent, $modulus);
    }

    /**
     * @param BigIntegerInterface $exponent
     * @param BigIntegerInterface $modulus
     *
     * @return SignatureInterface
     */
    public function createSignatureXFromDetails(
        BigIntegerInterface $exponent,
        BigIntegerInterface $modulus
    ): SignatureInterface {
        return $this->createCertificateFromDetails(SignatureInterface::TYPE_X, $exponent, $modulus);
    }

    /**
     * @param KeyPair $keyPair
     * @param string $type
     * @param X509GeneratorInterface|null $x509Generator
     *
     * @return SignatureInterface
     */
    private function createSignatureFromKeys(
        KeyPair $keyPair,
        string $type,
        ?X509GeneratorInterface $x509Generator = null
    ): SignatureInterface {
        $signature = new Signature($type, $keyPair->getPublicKey(), $keyPair->getPrivateKey());

        if (null !== $x509Generator) {
            $privateKey = $this->rsaFactory->createPrivate($keyPair->getPrivateKey(), $keyPair->getPassword());
            $publicKey = $this->rsaFactory->createPublic($keyPair->getPublicKey());

            switch ($type) {
                case SignatureInterface::TYPE_A:
                    $x509Context = $x509Generator->getAX509Context();
                    $x509Context->setSubjectPublicKey($publicKey);
                    if (null === $x509Context->getIssuerPrivateKey()) {
                        $x509Context->setIssuerPublicKey($publicKey);
                        $x509Context->setIssuerPrivateKey($privateKey);
                    }
                    $x509 = $x509Generator->generateAX509();
                    break;
                case SignatureInterface::TYPE_E:
                    $x509Context = $x509Generator->getEX509Context();
                    $x509Context->setSubjectPublicKey($publicKey);
                    if (null === $x509Context->getIssuerPrivateKey()) {
                        $x509Context->setIssuerPublicKey($publicKey);
                        $x509Context->setIssuerPrivateKey($privateKey);
                    }
                    $x509 = $x509Generator->generateEX509();
                    break;
                case SignatureInterface::TYPE_X:
                    $x509Context = $x509Generator->getXX509Context();
                    $x509Context->setSubjectPublicKey($publicKey);
                    if (null === $x509Context->getIssuerPrivateKey()) {
                        $x509Context->setIssuerPublicKey($publicKey);
                        $x509Context->setIssuerPrivateKey($privateKey);
                    }
                    $x509 = $x509Generator->generateXX509();
                    break;
                default:
                    throw new RuntimeException('Unpredictable type.');
            }

            if (!($certificateContent = $x509->saveX509CurrentCert())) {
                throw new RuntimeException('Can not save current certificate.');
            }

            $signature->setCertificateContent($certificateContent);
        }

        return $signature;
    }

    /**
     * @param string $type
     * @param BigIntegerInterface $exponent
     * @param BigIntegerInterface $modulus
     *
     * @return SignatureInterface
     */
    private function createCertificateFromDetails(
        string $type,
        BigIntegerInterface $exponent,
        BigIntegerInterface $modulus
    ): SignatureInterface {
        $rsa = $this->rsaFactory->compositePublicKey($exponent, $modulus, RSA::PUBLIC_FORMAT_PKCS1);
        $publicKey = new Key($rsa->getPublicKey(RSA::PUBLIC_FORMAT_PKCS1), RSA::PUBLIC_FORMAT_PKCS1);

        return new Signature($type, $publicKey, null);
    }

    /**
     * @param X509GeneratorInterface $x509Generator
     * @param KeyPair $keyPair
     * @return string
     */
    public function createIssuerCertificate(X509GeneratorInterface $x509Generator, KeyPair $keyPair): string
    {
        $x509Context = $x509Generator->getIssuerX509Context();

        $publicKey = $this->rsaFactory->createPublic($keyPair->getPublicKey());
        $privateKey = $this->rsaFactory->createPrivate($keyPair->getPrivateKey(), $keyPair->getPassword());

        $x509Context->setIssuerPublicKey($publicKey);
        $x509Context->setIssuerPrivateKey($privateKey);

        $certificateContent = $x509Generator->generateIssuerX509()->saveX509CurrentCert();

        if (!$certificateContent) {
            throw new RuntimeException('Can not save current certificate.');
        }

        return $certificateContent;
    }
}
