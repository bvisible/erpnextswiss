<?php

namespace EbicsApi\Ebics\Models\X509;

use EbicsApi\Ebics\Models\Bank;
use LogicException;

/**
 * Automatic resolving by bank X509 certificate generator @see X509GeneratorInterface.
 * Suspected that commonName should be built from client data, not bank data.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class BankX509Generator extends X509Generator
{
    /**
     * Set certificate options by Bank.
     */
    public function setCertificateOptionsByBank(Bank $bank): void
    {
        $url = $bank->getUrl();

        $countryName = $this->resolveCountryName($url);
        $domainName = $this->resolveDomainName($url);
        $establishmentName = $this->resolveEstablishmentName($url);

        $certificateOptions = [
            'subject' => [
                'DN' => [
                    'id-at-countryName' => $countryName,
                    'id-at-commonName' => $domainName,
                ],
            ],
            'issuer' => [
                'DN' => [
                    'id-at-countryName' => $countryName,
                    'id-at-commonName' => $establishmentName,
                ],
            ],
        ];

        $this->aX509Context->mergeCertificateOptions($certificateOptions);
        $this->eX509Context->mergeCertificateOptions($certificateOptions);
        $this->xX509Context->mergeCertificateOptions($certificateOptions);
        $this->issuerX509Context->mergeCertificateOptions($certificateOptions);
    }

    /**
     * Resolve country name by URL.
     */
    private function resolveCountryName(string $url): string
    {
        $host = parse_url($url, PHP_URL_HOST);
        if (empty($host)) {
            throw new LogicException('Host not parsed.');
        }

        $explode = explode('.', $host);
        $domain = end($explode);

        switch ($domain) {
            case 'fr':
                return Bank::COUNTRY_CODE_FR;
            case 'ch':
                return Bank::COUNTRY_CODE_CH;
            case 'de':
                return Bank::COUNTRY_CODE_DE;
            case 'at':
                return Bank::COUNTRY_CODE_AT;
            default:
                return Bank::COUNTRY_CODE_EU;
        }
    }

    /**
     * Resolve domain name by URL.
     */
    private function resolveDomainName(string $url): string
    {
        $host = parse_url($url, PHP_URL_HOST);
        if (empty($host)) {
            throw new LogicException('Host not parsed.');
        }

        $explode = explode('.', $host);
        $explode[0] = '*';

        return implode('.', $explode);
    }

    /**
     * Resolve establishment name by URL.
     */
    private function resolveEstablishmentName(string $url): string
    {
        $host = parse_url($url, PHP_URL_HOST);
        if (empty($host)) {
            throw new LogicException('Host not parsed.');
        }

        $explode = explode('.', $host);

        return ucfirst($explode[max(count($explode) - 2, 0)]);
    }
}
