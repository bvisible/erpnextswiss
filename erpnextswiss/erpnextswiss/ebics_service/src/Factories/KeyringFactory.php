<?php

namespace EbicsApi\Ebics\Factories;

use EbicsApi\Ebics\Contracts\SignatureInterface;
use EbicsApi\Ebics\Models\Keyring;
use EbicsApi\Ebics\Services\CryptoStorage;

/**
 * Class KeyringFactory represents producers for the @see Keyring
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class KeyringFactory
{
    private SignatureFactory $signatureFactory;

    private CryptoStorage $cryptoStorage;

    public function __construct(SignatureFactory $signatureFactory, CryptoStorage $cryptoStorage)
    {
        $this->signatureFactory = $signatureFactory;
        $this->cryptoStorage = $cryptoStorage;
    }

    /**
     * @param array $data
     *
     * @return Keyring
     */
    public function createKeyringFromData(array $data): Keyring
    {
        $keyring = new Keyring($data[Keyring::VERSION_PREFIX]);

        $keyring->setUserSignatureAVersion(
            $data[Keyring::USER_PREFIX][Keyring::SIGNATURE_PREFIX_A][Keyring::VERSION_PREFIX]
        );
        $keyring->setUserSignatureA(
            $this->buildKeyringFromDataForTypeKeyring($data, Keyring::USER_PREFIX, Keyring::SIGNATURE_PREFIX_A)
        );

        $keyring->setUserSignatureE(
            $this->buildKeyringFromDataForTypeKeyring($data, Keyring::USER_PREFIX, Keyring::SIGNATURE_PREFIX_E)
        );

        $keyring->setUserSignatureX(
            $this->buildKeyringFromDataForTypeKeyring($data, Keyring::USER_PREFIX, Keyring::SIGNATURE_PREFIX_X)
        );

        $keyring->setBankSignatureE(
            $this->buildKeyringFromDataForTypeKeyring($data, Keyring::BANK_PREFIX, Keyring::SIGNATURE_PREFIX_E)
        );

        $keyring->setBankSignatureX(
            $this->buildKeyringFromDataForTypeKeyring($data, Keyring::BANK_PREFIX, Keyring::SIGNATURE_PREFIX_X)
        );

        return $keyring;
    }

    /**
     * @param array $data
     * @param string $typePrefix
     * @param string $signaturePrefix
     *
     * @return SignatureInterface|null
     */
    private function buildKeyringFromDataForTypeKeyring(
        array $data,
        string $typePrefix,
        string $signaturePrefix
    ): ?SignatureInterface {
        if (empty($data[$typePrefix][$signaturePrefix][Keyring::PUBLIC_KEY_PREFIX])) {
            return null;
        }
        $certificateContent
            = $data[$typePrefix][$signaturePrefix][Keyring::CERTIFICATE_PREFIX];
        $publicKey
            = $data[$typePrefix][$signaturePrefix][Keyring::PUBLIC_KEY_PREFIX];
        $privateKey
            = $data[$typePrefix][$signaturePrefix][Keyring::PRIVATE_KEY_PREFIX];

        $signature = $this->signatureFactory->create(
            $signaturePrefix,
            $this->cryptoStorage->readPublicKey($publicKey),
            $this->cryptoStorage->readPrivateKey($privateKey),
        );

        if (!empty($certificateContent)) {
            $signature->setCertificateContent($this->cryptoStorage->readCertificate($certificateContent));
        }

        return $signature;
    }

    /**
     * @param Keyring $keyring
     *
     * @return array
     */
    public function buildDataFromKeyring(Keyring $keyring): array
    {
        if (null !== $keyring->getUserSignatureA()) {
            $userSignatureAB64 = $keyring->getUserSignatureA()->getCertificateContent();
            $userSignatureAPublicKey = $keyring->getUserSignatureA()->getPublicKey();
            $userSignatureAPrivateKey = $keyring->getUserSignatureA()->getPrivateKey();
        }
        if (null !== $keyring->getUserSignatureE()) {
            $userSignatureEB64 = $keyring->getUserSignatureE()->getCertificateContent();
            $userSignatureEPublicKey = $keyring->getUserSignatureE()->getPublicKey();
            $userSignatureEPrivateKey = $keyring->getUserSignatureE()->getPrivateKey();
        }
        if (null !== $keyring->getUserSignatureX()) {
            $userSignatureXB64 = $keyring->getUserSignatureX()->getCertificateContent();
            $userSignatureXPublicKey = $keyring->getUserSignatureX()->getPublicKey();
            $userSignatureXPrivateKey = $keyring->getUserSignatureX()->getPrivateKey();
        }
        if (null !== $keyring->getBankSignatureE()) {
            $bankSignatureEB64 = $keyring->getBankSignatureE()->getCertificateContent();
            $bankSignatureEPublicKey = $keyring->getBankSignatureE()->getPublicKey();
            $bankSignatureEPrivateKey = $keyring->getBankSignatureE()->getPrivateKey();
        }
        if (null !== $keyring->getBankSignatureX()) {
            $bankSignatureXB64 = $keyring->getBankSignatureX()->getCertificateContent();
            $bankSignatureXPublicKey = $keyring->getBankSignatureX()->getPublicKey();
            $bankSignatureXPrivateKey = $keyring->getBankSignatureX()->getPrivateKey();
        }

        return [
            Keyring::VERSION_PREFIX => $keyring->getVersion(),
            Keyring::USER_PREFIX => [
                Keyring::SIGNATURE_PREFIX_A => [
                    Keyring::VERSION_PREFIX => $keyring->getUserSignatureAVersion(),
                    Keyring::CERTIFICATE_PREFIX => $this->cryptoStorage
                        ->writeCertificate($userSignatureAB64 ?? null),
                    Keyring::PUBLIC_KEY_PREFIX => $this->cryptoStorage
                        ->writePublicKey($userSignatureAPublicKey ?? null),
                    Keyring::PRIVATE_KEY_PREFIX => $this->cryptoStorage
                        ->writePrivateKey($userSignatureAPrivateKey ?? null),
                ],
                Keyring::SIGNATURE_PREFIX_E => [
                    Keyring::CERTIFICATE_PREFIX => $this->cryptoStorage
                        ->writeCertificate($userSignatureEB64 ?? null),
                    Keyring::PUBLIC_KEY_PREFIX => $this->cryptoStorage
                        ->writePublicKey($userSignatureEPublicKey ?? null),
                    Keyring::PRIVATE_KEY_PREFIX => $this->cryptoStorage
                        ->writePrivateKey($userSignatureEPrivateKey ?? null),
                ],
                Keyring::SIGNATURE_PREFIX_X => [
                    Keyring::CERTIFICATE_PREFIX => $this->cryptoStorage
                        ->writeCertificate($userSignatureXB64 ?? null),
                    Keyring::PUBLIC_KEY_PREFIX => $this->cryptoStorage
                        ->writePublicKey($userSignatureXPublicKey ?? null),
                    Keyring::PRIVATE_KEY_PREFIX => $this->cryptoStorage
                        ->writePrivateKey($userSignatureXPrivateKey ?? null),
                ],
            ],
            Keyring::BANK_PREFIX => [
                Keyring::SIGNATURE_PREFIX_E => [
                    Keyring::CERTIFICATE_PREFIX => $this->cryptoStorage
                        ->writeCertificate($bankSignatureEB64 ?? null),
                    Keyring::PUBLIC_KEY_PREFIX => $this->cryptoStorage
                        ->writePublicKey($bankSignatureEPublicKey ?? null),
                    Keyring::PRIVATE_KEY_PREFIX => $this->cryptoStorage
                        ->writePrivateKey($bankSignatureEPrivateKey ?? null),
                ],
                Keyring::SIGNATURE_PREFIX_X => [
                    Keyring::CERTIFICATE_PREFIX => $this->cryptoStorage
                        ->writeCertificate($bankSignatureXB64 ?? null),
                    Keyring::PUBLIC_KEY_PREFIX => $this->cryptoStorage
                        ->writePublicKey($bankSignatureXPublicKey ?? null),
                    Keyring::PRIVATE_KEY_PREFIX => $this->cryptoStorage
                        ->writePrivateKey($bankSignatureXPrivateKey ?? null),
                ],
            ],
        ];
    }
}
