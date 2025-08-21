<?php

namespace EbicsApi\Ebics\Models\X509;

use DateTime;
use EbicsApi\Ebics\Contracts\Crypt\RSAInterface;
use EbicsApi\Ebics\Contracts\Crypt\X509Interface;
use EbicsApi\Ebics\Contracts\X509GeneratorInterface;
use EbicsApi\Ebics\Exceptions\X509\X509GeneratorException;
use EbicsApi\Ebics\Factories\Crypt\X509Factory;
use EbicsApi\Ebics\Services\RandomService;
use EbicsApi\Ebics\Services\X509\X509OptionsNormalizer;
use RuntimeException;

/**
 * Default X509 certificate generator @see X509GeneratorInterface.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Guillaume Sainthillier, Andrew Svirin
 */
abstract class X509Generator implements X509GeneratorInterface
{
    protected X509Context $aX509Context;
    protected X509Context $eX509Context;
    protected X509Context $xX509Context;
    protected X509Context $issuerX509Context;
    private X509Factory $x509Factory;
    private RandomService $randomService;

    public function __construct()
    {
        $this->x509Factory = new X509Factory();
        $this->randomService = new RandomService();
        $this->aX509Context = new X509Context(
            $this->generateSerialNumber(),
            (new DateTime())->modify('-1 day'),
            (new DateTime())->modify('+1 year')
        );
        $this->eX509Context = new X509Context(
            $this->generateSerialNumber(),
            (new DateTime())->modify('-1 day'),
            (new DateTime())->modify('+1 year')
        );
        $this->xX509Context = new X509Context(
            $this->generateSerialNumber(),
            (new DateTime())->modify('-1 day'),
            (new DateTime())->modify('+1 year')
        );
        $this->issuerX509Context = new X509Context(
            $this->generateSerialNumber(),
            (new DateTime())->modify('-1 day'),
            (new DateTime())->modify('+10 year')
        );
    }

    /**
     * @inheritDoc
     * @throws X509GeneratorException
     */
    public function generateAX509(): X509Interface
    {
        $this->aX509Context->mergeCertificateOptions(
            [
                'extensions' => [
                    'id-ce-keyUsage' => [
                        'value' => ['nonRepudiation'],
                        'critical' => true,
                    ],
                ],
            ]
        );

        return $this->generateX509($this->aX509Context);
    }

    /**
     * @inheritDoc
     * @throws X509GeneratorException
     */
    public function generateEX509(): X509Interface
    {
        $this->eX509Context->mergeCertificateOptions(
            [
                'extensions' => [
                    'id-ce-keyUsage' => [
                        'value' => ['keyEncipherment'],
                        'critical' => true,
                    ],
                ],
            ]
        );

        return $this->generateX509($this->eX509Context);
    }

    /**
     * @inheritDoc
     * @throws X509GeneratorException
     */
    public function generateXX509(): X509Interface
    {
        $this->xX509Context->mergeCertificateOptions([
            'extensions' => [
                'id-ce-keyUsage' => [
                    'value' => ['digitalSignature'],
                    'critical' => true,
                ],
            ],
        ]);

        return $this->generateX509($this->xX509Context);
    }

    /**
     * @inheritDoc
     * @throws X509GeneratorException
     */
    public function generateIssuerX509(): X509Interface
    {
        $context = $this->issuerX509Context;
        $context->mergeCertificateOptions([
            'issuer' => [
                'DN' => [],
            ],
            'extensions' => [
                'id-ce-basicConstraints' => [
                    'value' => [
                        'cA' => true,
                    ],
                ],
            ],
        ], false);
        $options = $context->getCertificateOptions();

        $x509 = $this->x509Factory->create();
        $x509->setPrivateKey($context->getIssuerPrivateKey());
        $x509->setPublicKey($context->getIssuerPublicKey());

        $x509->setDN($options['issuer']['DN']);
        $x509->setKeyIdentifier($x509->computeKeyIdentifier($context->getIssuerPublicKey()));

        $x509->setStartDate($context->getStartDate()->format('YmdHis'));
        $x509->setEndDate($context->getEndDate()->format('YmdHis'));
        $x509->setSerialNumber($context->getSerialNumber());
        $this->signWithReload($x509, $x509, $x509);
        $this->setExtensions($x509, $options['extensions']);
        // Sign extensions.
        $this->signWithReload($x509, $x509, $x509);

        return $x509;
    }

    /**
     * Generate X509.
     *
     * @param X509Context $context
     * @return X509Interface
     * @throws X509GeneratorException
     */
    private function generateX509(X509Context $context): X509Interface
    {
        $context->mergeCertificateOptions([
            'subject' => [
                'domain' => null,
                'DN' => [],
            ],
            'issuer' => [
                'DN' => [],
            ],
            'extensions' => [
                'id-ce-basicConstraints' => [
                    'value' => [
                        'cA' => false,
                    ],
                ],
                'id-ce-extKeyUsage' => [
                    'value' => ['id-kp-emailProtection'],
                ],
            ],
        ], false);
        $options = $context->getCertificateOptions();

        $subject = $this->generateSubject($context->getSubjectPublicKey(), $options['subject']);
        $issuer = $this->generateIssuer(
            $context->getIssuerPrivateKey(),
            $context->getIssuerPublicKey(),
            $subject,
            $options['issuer']
        );

        $x509 = $this->x509Factory->create();
        $x509->setStartDate($context->getStartDate()->format('YmdHis'));
        $x509->setEndDate($context->getEndDate()->format('YmdHis'));
        $x509->setSerialNumber($context->getSerialNumber());
        $this->signWithReload($x509, $issuer, $subject);
        $this->setExtensions($x509, $options['extensions']);
        // Sign extensions.
        $this->signWithReload($x509, $issuer, $x509);

        return $x509;
    }

    /**
     * Set extensions.
     * @param X509Interface $x509
     * @param array $extensions
     * @return void
     * @throws X509GeneratorException
     */
    private function setExtensions(X509Interface $x509, array $extensions): void
    {
        foreach ($extensions as $id => $extension) {
            $extension = X509OptionsNormalizer::normalizeExtensions($extension);
            $isSetExtension = $x509->setExtension(
                $id,
                $extension['value'],
                $extension['critical'],
                $extension['replace']
            );
            if (false === $isSetExtension) {
                throw new X509GeneratorException(
                    sprintf(
                        'Unable to set "%s" extension with value: %s',
                        $id,
                        var_export($extension['value'], true)
                    )
                );
            }
        }
    }

    private function signWithReload(X509Interface $x509, X509Interface $issuer, X509Interface $subject): void
    {
        $signatureAlgorithm = 'sha256WithRSAEncryption';

        $x509Signed = $x509->sign($issuer, $subject, $signatureAlgorithm);
        $signedX509 = $x509->saveX509($x509Signed);
        $x509->loadX509($signedX509);
    }

    /**
     * @param RSAInterface $publicKey
     * @param array $options
     *
     * @return X509Interface
     */
    protected function generateSubject(RSAInterface $publicKey, array $options): X509Interface
    {
        $subject = $this->x509Factory->create();
        $subject->setPublicKey($publicKey);

        if (!empty($options['DN'])) {
            if (!$subject->setDN($options['DN'])) {
                throw new RuntimeException('Can not set Subject DN.');
            }
        }

        if (!empty($options['domain'])) {
            $subject->setDomain($options['domain']); // @phpstan-ignore-line
        }
        $subject->setKeyIdentifier($subject->computeKeyIdentifier($publicKey)); // id-ce-subjectKeyIdentifier

        return $subject;
    }

    /**
     * @param RSAInterface $privateKey
     * @param RSAInterface $publicKey
     * @param X509Interface $subject
     * @param array $options
     *
     * @return X509Interface
     */
    protected function generateIssuer(
        RSAInterface $privateKey,
        RSAInterface $publicKey,
        X509Interface $subject,
        array $options
    ): X509Interface {
        $issuer = $this->x509Factory->create();
        $issuer->setPrivateKey($privateKey); // $privKey is Crypt_RSA object

        if (!empty($options['DN'])) {
            if (!$issuer->setDN($options['DN'])) {
                throw new RuntimeException('Can not set Issuer DN.');
            }
        } else {
            $issuer->setDN($subject->getDN());
        }
        $issuer->setKeyIdentifier($subject->computeKeyIdentifier($publicKey));

        return $issuer;
    }

    /**
     * Random Number should be of type integer.
     *
     * @return string
     */
    public function generateSerialNumber(): string
    {
        return $this->randomService->digits(9);
    }

    public function getAX509Context(): X509Context
    {
        return $this->aX509Context;
    }

    public function getEX509Context(): X509Context
    {
        return $this->eX509Context;
    }

    public function getXX509Context(): X509Context
    {
        return $this->xX509Context;
    }

    public function getIssuerX509Context(): X509Context
    {
        return $this->issuerX509Context;
    }
}
