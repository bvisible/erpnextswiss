<?php

namespace EbicsApi\Ebics\Models\X509;

use DateTimeInterface;
use EbicsApi\Ebics\Contracts\Crypt\RSAInterface;
use EbicsApi\Ebics\Contracts\Crypt\X509Interface;
use EbicsApi\Ebics\Services\X509\X509OptionsNormalizer;

/**
 * Class X509Context is a context for X509 Generator
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class X509Context
{
    private string $serialNumber;
    private DateTimeInterface $startDate;
    private DateTimeInterface $endDate;
    private RSAInterface $subjectPublicKey;
    private RSAInterface $issuerPublicKey;
    private ?RSAInterface $issuerPrivateKey = null;
    private array $certificateOptions = [];

    public function __construct(string $serialNumber, DateTimeInterface $startDate, DateTimeInterface $endDate)
    {
        $this->serialNumber = $serialNumber;
        $this->startDate = $startDate;
        $this->endDate = $endDate;
    }

    public function setSerialNumber(string $serialNumber): void
    {
        $this->serialNumber = $serialNumber;
    }

    public function getSerialNumber(): string
    {
        return $this->serialNumber;
    }

    public function setStartDate(DateTimeInterface $startDate): void
    {
        $this->startDate = $startDate;
    }

    public function getStartDate(): DateTimeInterface
    {
        return $this->startDate;
    }

    public function setEndDate(DateTimeInterface $endDate): void
    {
        $this->endDate = $endDate;
    }

    public function getEndDate(): DateTimeInterface
    {
        return $this->endDate;
    }

    public function setSubjectPublicKey(RSAInterface $subjectPublicKey): void
    {
        $this->subjectPublicKey = $subjectPublicKey;
    }

    public function getSubjectPublicKey(): RSAInterface
    {
        return $this->subjectPublicKey;
    }

    public function setIssuerPublicKey(RSAInterface $issuerPublicKey): void
    {
        $this->issuerPublicKey = $issuerPublicKey;
    }

    public function getIssuerPublicKey(): RSAInterface
    {
        return $this->issuerPublicKey;
    }

    public function setIssuerPrivateKey(RSAInterface $issuerPrivateKey): void
    {
        $this->issuerPrivateKey = $issuerPrivateKey;
    }

    public function getIssuerPrivateKey(): ?RSAInterface
    {
        return $this->issuerPrivateKey;
    }

    /**
     * Merge arrays recursively by substitution not assoc arrays.
     *
     * @param array $options1
     * @param array $options2
     *
     * @return array
     */
    private function mergeOptions(array $options1, array $options2): array
    {
        foreach ($options2 as $key => $value) {
            if (is_string($key) && array_key_exists($key, $options1) && is_array($value)) {
                $options1[$key] = $this->mergeOptions($options1[$key], $options2[$key]);
            } else {
                $options1[$key] = $value;
            }
        }

        return $options1;
    }

    /**
     * Merge arrays recursively by substitution not assoc arrays.
     *
     * @param array $options
     * @param bool $over
     * @return void
     */
    public function mergeCertificateOptions(array $options, bool $over = true): void
    {
        if ($over) {
            $this->certificateOptions = $this->mergeOptions($this->certificateOptions, $options);
        } else {
            $this->certificateOptions = $this->mergeOptions($options, $this->certificateOptions);
        }
    }

    public function getCertificateOptions(): array
    {
        return $this->certificateOptions;
    }

    public function applyIssuerDN(X509Interface $x509): void
    {
        $this->mergeCertificateOptions([
            'issuer' => [
                'DN' => X509OptionsNormalizer::denormalizeDN($x509->getDN()),
            ],
        ]);
    }
}
