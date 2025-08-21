<?php

namespace EbicsApi\Ebics;

use EbicsApi\Ebics\Contracts\BankLetter\FormatterInterface;
use EbicsApi\Ebics\Factories\BankLetterFactory;
use EbicsApi\Ebics\Factories\CertificateX509Factory;
use EbicsApi\Ebics\Factories\Crypt\AESFactory;
use EbicsApi\Ebics\Factories\Crypt\RSAFactory;
use EbicsApi\Ebics\Factories\EbicsFactoryV24;
use EbicsApi\Ebics\Factories\EbicsFactoryV25;
use EbicsApi\Ebics\Factories\EbicsFactoryV30;
use EbicsApi\Ebics\Factories\SignatureBankLetterFactory;
use EbicsApi\Ebics\Models\Bank;
use EbicsApi\Ebics\Models\BankLetter;
use EbicsApi\Ebics\Models\Keyring;
use EbicsApi\Ebics\Models\User;
use EbicsApi\Ebics\Services\BankLetter\Formatter\HtmlBankLetterFormatter;
use EbicsApi\Ebics\Services\BankLetter\Formatter\PdfBankLetterFormatter;
use EbicsApi\Ebics\Services\BankLetter\Formatter\TxtBankLetterFormatter;
use EbicsApi\Ebics\Services\BankLetterService;
use EbicsApi\Ebics\Services\CryptService;
use EbicsApi\Ebics\Services\RandomService;
use LogicException;

/**
 * EBICS bank letter prepare.
 * Initialization letter details.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class EbicsBankLetter
{
    private BankLetterService $bankLetterService;
    private BankLetterFactory $bankLetterFactory;
    private CryptService $cryptService;

    public function __construct(array $options = [])
    {
        $this->cryptService = new CryptService(
            new RSAFactory($options['rsa_class_map'] ?? null),
            new AESFactory(),
            new RandomService()
        );
        $this->bankLetterService = new BankLetterService(
            $this->cryptService,
            new SignatureBankLetterFactory(),
            new CertificateX509Factory()
        );
        $this->bankLetterFactory = new BankLetterFactory();
    }

    /**
     * Prepare variables for bank letter.
     * On this moment should be called INI and HEA.
     *
     * @param Bank $bank
     * @param User $user
     * @param Keyring $keyring
     *
     * @return BankLetter
     */
    public function prepareBankLetter(Bank $bank, User $user, Keyring $keyring): BankLetter
    {
        if (Keyring::VERSION_24 === $keyring->getVersion()) {
            $ebicsFactory = new EbicsFactoryV24();
        } elseif (Keyring::VERSION_25 === $keyring->getVersion()) {
            $ebicsFactory = new EbicsFactoryV25();
        } elseif (Keyring::VERSION_30 === $keyring->getVersion()) {
            $ebicsFactory = new EbicsFactoryV30();
        } else {
            throw new LogicException(sprintf('Version "%s" is not implemented', $keyring->getVersion()));
        }

        $digestResolver = $ebicsFactory->createDigestResolver($this->cryptService);

        return $this->bankLetterFactory->create(
            $bank,
            $user,
            $this->bankLetterService->formatSignatureForBankLetter(
                $keyring->getUserSignatureA(),
                $keyring->getUserSignatureAVersion(),
                $digestResolver
            ),
            $this->bankLetterService->formatSignatureForBankLetter(
                $keyring->getUserSignatureE(),
                $keyring->getUserSignatureEVersion(),
                $digestResolver
            ),
            $this->bankLetterService->formatSignatureForBankLetter(
                $keyring->getUserSignatureX(),
                $keyring->getUserSignatureXVersion(),
                $digestResolver
            )
        );
    }

    /**
     * Format bank letter.
     *
     * @param BankLetter $bankLetter
     * @param FormatterInterface $formatter
     *
     * @return string
     */
    public function formatBankLetter(BankLetter $bankLetter, FormatterInterface $formatter): string
    {
        return $formatter->format($bankLetter);
    }

    public function createTxtBankLetterFormatter(): TxtBankLetterFormatter
    {
        return new TxtBankLetterFormatter();
    }

    public function createHtmlBankLetterFormatter(): HtmlBankLetterFormatter
    {
        return new HtmlBankLetterFormatter();
    }

    public function createPdfBankLetterFormatter(): PdfBankLetterFormatter
    {
        return new PdfBankLetterFormatter();
    }
}
