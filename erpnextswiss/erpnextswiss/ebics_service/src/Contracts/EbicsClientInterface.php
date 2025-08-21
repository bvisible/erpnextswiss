<?php

namespace EbicsApi\Ebics\Contracts;

use EbicsApi\Ebics\Contracts\Order\DownloadOrderInterface;
use EbicsApi\Ebics\Contracts\Order\InitializationOrderInterface;
use EbicsApi\Ebics\Contracts\Order\StandardOrderInterface;
use EbicsApi\Ebics\Contracts\Order\UploadOrderInterface;
use EbicsApi\Ebics\Handlers\ResponseHandler;
use EbicsApi\Ebics\Models\Bank;
use EbicsApi\Ebics\Models\Keyring;
use EbicsApi\Ebics\Models\Order\DownloadOrderResult;
use EbicsApi\Ebics\Models\Order\InitializationOrderResult;
use EbicsApi\Ebics\Models\Order\StandardOrderResult;
use EbicsApi\Ebics\Models\Order\UploadOrderResult;
use EbicsApi\Ebics\Models\User;

/**
 * EBICS client representation.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
interface EbicsClientInterface
{
    public const FILE_PARSER_FORMAT_TEXT = 'text';
    public const FILE_PARSER_FORMAT_XML = 'xml';
    public const FILE_PARSER_FORMAT_XML_FILES = 'xml_files';
    public const FILE_PARSER_FORMAT_ZIP_FILES = 'zip_files';

    /**
     * Create user signatures A, E and X on first launch.
     * @param array|null $options Setup to specify custom certificate, private, public keys and version
     * for Electronic Signature, Authorization and Identification, Encryption details.
     */
    public function createUserSignatures(?array $options = null): void;

    /**
     * Generate certificate for issuer.
     * @return array
     */
    public function generateIssuerCertificate(): array;

    /**
     * Execute Initialization Order.
     * @param InitializationOrderInterface $order
     * @return InitializationOrderResult
     */
    public function executeInitializationOrder(InitializationOrderInterface $order): InitializationOrderResult;

    /**
     * Execute Standard Order.
     * @param StandardOrderInterface $order
     * @return StandardOrderResult
     */
    public function executeStandardOrder(StandardOrderInterface $order): StandardOrderResult;

    /**
     * Execute Download Order.
     * @param DownloadOrderInterface $order
     * @return DownloadOrderResult
     */
    public function executeDownloadOrder(DownloadOrderInterface $order): DownloadOrderResult;

    /**
     * Execute Upload Order.
     * @param UploadOrderInterface $order
     * @return UploadOrderResult
     */
    public function executeUploadOrder(UploadOrderInterface $order): UploadOrderResult;

    /**
     * Get Keyring.
     *
     * @return Keyring
     */
    public function getKeyring(): Keyring;

    /**
     * Get Bank.
     *
     * @return Bank
     */
    public function getBank(): Bank;

    /**
     * Get User.
     *
     * @return User
     */
    public function getUser(): User;

    /**
     * Get response handler for manual process response.
     *
     * @return ResponseHandler
     */
    public function getResponseHandler(): ResponseHandler;

    /**
     * Check keyring is valid.
     *
     * @return bool
     */
    public function checkKeyring(): bool;

    /**
     * Change password for keyring.
     *
     * @param string $newPassword
     *
     * @return void
     */
    public function changeKeyringPassword(string $newPassword): void;
}
