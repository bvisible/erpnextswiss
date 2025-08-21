<?php

namespace EbicsApi\Ebics\Factories;

use EbicsApi\Ebics\Builders\Request\RequestBuilder;
use EbicsApi\Ebics\Factories\Crypt\BigIntegerFactory;
use EbicsApi\Ebics\Handlers\AuthSignatureHandler;
use EbicsApi\Ebics\Handlers\OrderDataHandler;
use EbicsApi\Ebics\Handlers\ResponseHandler;
use EbicsApi\Ebics\Handlers\UserSignatureHandler;
use EbicsApi\Ebics\Models\Bank;
use EbicsApi\Ebics\Models\Keyring;
use EbicsApi\Ebics\Models\User;
use EbicsApi\Ebics\Services\CryptService;
use EbicsApi\Ebics\Services\DigestResolver;
use EbicsApi\Ebics\Services\SchemaValidator;
use EbicsApi\Ebics\Services\ZipService;

/**
 * Abstract Class EbicsFactory.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
abstract class EbicsFactory
{
    abstract public function createRequestFactory(
        Bank $bank,
        User $user,
        Keyring $keyring,
        UserSignatureHandler $userSignatureHandler,
        OrderDataHandler $orderDataHandler,
        DigestResolver $digestResolver,
        RequestBuilder $requestBuilder,
        CryptService $cryptService,
        ZipService $zipService
    ): RequestFactory;

    abstract public function createAuthSignatureHandler(
        Keyring $keyring,
        CryptService $cryptService
    ): AuthSignatureHandler;

    abstract public function createUserSignatureHandler(
        User $user,
        Keyring $keyring,
        CryptService $cryptService,
        SchemaValidator $schemaValidator
    ): UserSignatureHandler;

    abstract public function createOrderDataHandler(
        User $user,
        Keyring $keyring,
        CryptService $cryptService,
        SignatureFactory $signatureFactory,
        CertificateX509Factory $certificateX509Factory,
        BigIntegerFactory $bigIntegerFactory
    ): OrderDataHandler;

    abstract public function createResponseHandler(
        SegmentFactory $segmentFactory,
        CryptService $cryptService,
        ZipService $zipService,
        BufferFactory $bufferFactory
    ): ResponseHandler;

    abstract public function createDigestResolver(CryptService $cryptService): DigestResolver;

    public function createRequestBuilder(
        Keyring $keyring,
        CryptService $cryptService,
        SchemaValidator $schemaValidator
    ): RequestBuilder {
        return new RequestBuilder($this->createAuthSignatureHandler($keyring, $cryptService), $schemaValidator);
    }
}
