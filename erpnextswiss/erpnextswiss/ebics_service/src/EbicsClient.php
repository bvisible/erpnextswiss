<?php

namespace EbicsApi\Ebics;

use EbicsApi\Ebics\Contracts\EbicsClientInterface;
use EbicsApi\Ebics\Contracts\HttpClientInterface;
use EbicsApi\Ebics\Contracts\Order\DownloadOrderInterface;
use EbicsApi\Ebics\Contracts\Order\InitializationOrderInterface;
use EbicsApi\Ebics\Contracts\Order\StandardOrderInterface;
use EbicsApi\Ebics\Contracts\Order\UploadOrderInterface;
use EbicsApi\Ebics\Contracts\OrderDataInterface;
use EbicsApi\Ebics\Contracts\SignatureInterface;
use EbicsApi\Ebics\Exceptions\EbicsException;
use EbicsApi\Ebics\Exceptions\EbicsResponseException;
use EbicsApi\Ebics\Exceptions\IncorrectResponseEbicsException;
use EbicsApi\Ebics\Exceptions\PasswordEbicsException;
use EbicsApi\Ebics\Factories\BufferFactory;
use EbicsApi\Ebics\Factories\CertificateX509Factory;
use EbicsApi\Ebics\Factories\Crypt\AESFactory;
use EbicsApi\Ebics\Factories\Crypt\BigIntegerFactory;
use EbicsApi\Ebics\Factories\Crypt\RSAFactory;
use EbicsApi\Ebics\Factories\DocumentFactory;
use EbicsApi\Ebics\Factories\EbicsExceptionFactory;
use EbicsApi\Ebics\Factories\EbicsFactoryV24;
use EbicsApi\Ebics\Factories\EbicsFactoryV25;
use EbicsApi\Ebics\Factories\EbicsFactoryV30;
use EbicsApi\Ebics\Factories\OrderResultFactory;
use EbicsApi\Ebics\Factories\RequestFactory;
use EbicsApi\Ebics\Factories\SegmentFactory;
use EbicsApi\Ebics\Factories\SignatureFactory;
use EbicsApi\Ebics\Factories\TransactionFactory;
use EbicsApi\Ebics\Handlers\OrderDataHandler;
use EbicsApi\Ebics\Handlers\ResponseHandler;
use EbicsApi\Ebics\Handlers\UserSignatureHandler;
use EbicsApi\Ebics\Models\Bank;
use EbicsApi\Ebics\Models\Crypt\Key;
use EbicsApi\Ebics\Models\Crypt\KeyPair;
use EbicsApi\Ebics\Models\DownloadSegment;
use EbicsApi\Ebics\Models\DownloadTransaction;
use EbicsApi\Ebics\Models\Http\Request;
use EbicsApi\Ebics\Models\Http\Response;
use EbicsApi\Ebics\Models\InitializationSegment;
use EbicsApi\Ebics\Models\InitializationTransaction;
use EbicsApi\Ebics\Models\Keyring;
use EbicsApi\Ebics\Models\Order\DownloadOrderResult;
use EbicsApi\Ebics\Models\Order\InitializationOrderResult;
use EbicsApi\Ebics\Models\Order\StandardOrderResult;
use EbicsApi\Ebics\Models\Order\UploadOrderResult;
use EbicsApi\Ebics\Models\UploadTransaction;
use EbicsApi\Ebics\Models\User;
use EbicsApi\Ebics\Models\X509\ContentX509Generator;
use EbicsApi\Ebics\Services\CryptService;
use EbicsApi\Ebics\Services\CurlHttpClient;
use EbicsApi\Ebics\Services\RandomService;
use EbicsApi\Ebics\Services\SchemaValidator;
use EbicsApi\Ebics\Services\XmlService;
use EbicsApi\Ebics\Services\ZipService;
use LogicException;

/**
 * EBICS client representation.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class EbicsClient implements EbicsClientInterface
{
    private Bank $bank;
    private User $user;
    private Keyring $keyring;
    private OrderDataHandler $orderDataHandler;
    private UserSignatureHandler $userSignatureHandler;
    private ResponseHandler $responseHandler;
    private RequestFactory $requestFactory;
    private CryptService $cryptService;
    private ZipService $zipService;
    private XmlService $xmlService;
    private DocumentFactory $documentFactory;
    private OrderResultFactory $orderResultFactory;
    private SignatureFactory $signatureFactory;
    private HttpClientInterface $httpClient;
    private TransactionFactory $transactionFactory;
    private SegmentFactory $segmentFactory;
    private BufferFactory $bufferFactory;
    private RSAFactory $rsaFactory;
    private SchemaValidator $schemaValidator;

    /**
     * Constructor.
     *
     * @param Bank $bank
     * @param User $user
     * @param Keyring $keyring
     * @param array $options
     */
    public function __construct(Bank $bank, User $user, Keyring $keyring, array $options = [])
    {
        $this->bank = $bank;
        $this->user = $user;
        $this->keyring = $keyring;

        if (Keyring::VERSION_24 === $keyring->getVersion()) {
            $ebicsFactory = new EbicsFactoryV24();
        } elseif (Keyring::VERSION_25 === $keyring->getVersion()) {
            $ebicsFactory = new EbicsFactoryV25();
        } elseif (Keyring::VERSION_30 === $keyring->getVersion()) {
            $ebicsFactory = new EbicsFactoryV30();
        } else {
            throw new LogicException(sprintf('Version "%s" is not implemented', $keyring->getVersion()));
        }

        $this->rsaFactory = new RSAFactory($options['rsa_class_map'] ?? null);

        $this->segmentFactory = new SegmentFactory();
        $this->cryptService = new CryptService($this->rsaFactory, new AESFactory(), new RandomService());
        $this->zipService = new ZipService();
        $this->signatureFactory = new SignatureFactory($this->rsaFactory);
        $this->bufferFactory = new BufferFactory($options['buffer_filename'] ?? 'php://memory');

        $this->orderDataHandler = $ebicsFactory->createOrderDataHandler(
            $user,
            $keyring,
            $this->cryptService,
            $this->signatureFactory,
            new CertificateX509Factory(),
            new BigIntegerFactory()
        );

        $this->schemaValidator = new SchemaValidator($options['schema_dir'] ?? null);

        $this->userSignatureHandler = $ebicsFactory->createUserSignatureHandler(
            $user,
            $keyring,
            $this->cryptService,
            $this->schemaValidator
        );

        $this->requestFactory = $ebicsFactory->createRequestFactory(
            $bank,
            $user,
            $keyring,
            $this->userSignatureHandler,
            $this->orderDataHandler,
            $ebicsFactory->createDigestResolver($this->cryptService),
            $ebicsFactory->createRequestBuilder($keyring, $this->cryptService, $this->schemaValidator),
            $this->cryptService,
            $this->zipService
        );

        $this->responseHandler = $ebicsFactory->createResponseHandler(
            $this->segmentFactory,
            $this->cryptService,
            $this->zipService,
            $this->bufferFactory
        );

        $this->xmlService = new XmlService();
        $this->documentFactory = new DocumentFactory();
        $this->orderResultFactory = new OrderResultFactory();
        $this->transactionFactory = new TransactionFactory();
        $this->httpClient = $options['http_client'] ?? new CurlHttpClient();
    }

    public function executeInitializationOrder(InitializationOrderInterface $order): InitializationOrderResult
    {
        $order->useRequestFactory($this->requestFactory);
        $order->useOrderDataHandler($this->orderDataHandler);
        $order->useUserSignatureHandler($this->userSignatureHandler);
        $order->prepareContext();
        $transaction = $this->initializeTransaction(
            function () use ($order) {
                return $order->createRequest();
            }
        );
        $result = $this->createInitializationOrderResult($transaction);
        $order->afterExecute($result);

        return $result;
    }

    public function executeStandardOrder(StandardOrderInterface $order): StandardOrderResult
    {
        $order->useRequestFactory($this->requestFactory);
        $order->useOrderDataHandler($this->orderDataHandler);
        $order->useUserSignatureHandler($this->userSignatureHandler);
        $order->prepareContext();
        $request = $order->createRequest();
        $response = $this->httpClient->post($this->bank->getUrl(), $request);
        $this->responseHandler->checkResponseReturnCode($request, $response);
        $result = $this->createStandardOrderResult($response);
        $order->afterExecute($result);

        return $result;
    }

    public function executeDownloadOrder(DownloadOrderInterface $order): DownloadOrderResult
    {
        $order->useRequestFactory($this->requestFactory);
        $order->useOrderDataHandler($this->orderDataHandler);
        $order->useUserSignatureHandler($this->userSignatureHandler);
        $order->prepareContext();
        $transaction = $this->downloadTransaction(
            function () use ($order) {
                return $order->createRequest();
            },
            $order->getContext()->getAckClosure()
        );
        $result = $this->createDownloadOrderResult($transaction, $order->getParserFormat());
        $order->afterExecute($result);

        return $result;
    }

    public function executeUploadOrder(UploadOrderInterface $order): UploadOrderResult
    {
        $order->useRequestFactory($this->requestFactory);
        $order->useOrderDataHandler($this->orderDataHandler);
        $order->useUserSignatureHandler($this->userSignatureHandler);
        $order->prepareContext();
        $transaction = $this->uploadTransaction(
            function (UploadTransaction $transaction) use ($order) {
                $order->setTransaction($transaction);
                $orderData = $order->getOrderData();
                $this->schemaValidator->validate($orderData);
                $transaction->setOrderData($orderData->getContent());
                $transaction->setNumSegments($orderData->getContent() == ' ' ? 0 : 1);
                $transaction->setDigest($this->cryptService->hash($transaction->getOrderData()));

                return $order->createRequest();
            }
        );
        $result = $this->createUploadOrderResult($transaction, $order->getOrderData());
        $order->afterExecute($result);

        return $result;
    }

    /**
     * @inheritDoc
     * @throws EbicsException
     */
    public function createUserSignatures(?array $options = null): void
    {
        $signatureA = $this->createUserSignature(SignatureInterface::TYPE_A, $options['a_details'] ?? null);
        $this->keyring->setUserSignatureAVersion($options['a_version'] ?? SignatureInterface::A_VERSION6);
        $this->keyring->setUserSignatureA($signatureA);

        $signatureE = $this->createUserSignature(SignatureInterface::TYPE_E, $options['e_details'] ?? null);
        $this->keyring->setUserSignatureE($signatureE);

        $signatureX = $this->createUserSignature(SignatureInterface::TYPE_X, $options['x_details'] ?? null);
        $this->keyring->setUserSignatureX($signatureX);
    }

    /**
     * @inheritDoc
     */
    public function generateIssuerCertificate(): array
    {
        $keyPair = $this->cryptService->generateKeyPair($this->keyring->getPassword());

        $x509Generator = $this->keyring->getCertificateGenerator();

        if ($x509Generator) {
            $certificate = $this->signatureFactory->createIssuerCertificate($x509Generator, $keyPair);
        }

        return [
            'publickey' => $keyPair->getPublicKey()->getKey(),
            'publickey_type' => $keyPair->getPublicKey()->getType(),
            'privatekey' => $keyPair->getPrivateKey()->getKey(),
            'privatekey_type' => $keyPair->getPrivateKey()->getType(),
            'certificate' => $certificate ?? null,
        ];
    }

    /**
     * Mark download or upload transaction as receipt or not.
     *
     * @throws EbicsException
     * @throws Exceptions\EbicsResponseException
     */
    private function transferReceipt(DownloadTransaction $transaction, bool $acknowledged): void
    {
        $request = $this->requestFactory->createTransferReceipt($transaction->getId(), $acknowledged);
        $response = $this->httpClient->post($this->bank->getUrl(), $request);

        $this->checkH00XReturnCode($request, $response);

        $transaction->setReceipt($response);
    }

    /**
     * Upload transaction segments and mark transaction as transfer.
     *
     * @throws EbicsException
     * @throws Exceptions\EbicsResponseException
     */
    private function transferTransfer(UploadTransaction $uploadTransaction): void
    {
        foreach ($uploadTransaction->getSegments() as $segment) {
            $request = $this->requestFactory->createTransferUpload(
                $segment->getTransactionId(),
                $segment->getTransactionKey(),
                $segment->getOrderData(),
                $segment->getSegmentNumber(),
                $segment->getIsLastSegment()
            );
            $response = $this->httpClient->post($this->bank->getUrl(), $request);
            $this->checkH00XReturnCode($request, $response);

            $segment->setResponse($response);
        }
    }

    /**
     * @param Request $request
     * @param Response $response
     *
     * @throws Exceptions\IncorrectResponseEbicsException
     */
    private function checkH00XReturnCode(Request $request, Response $response): void
    {
        $errorCode = $this->responseHandler->retrieveH00XBodyOrHeaderReturnCode($response);

        if ('000000' === $errorCode) {
            return;
        }

        // For Transaction Done.
        if ('011000' === $errorCode) {
            return;
        }

        $reportText = $this->responseHandler->retrieveH00XReportText($response);
        EbicsExceptionFactory::buildExceptionFromCode($errorCode, $reportText, $request, $response);
    }


    /**
     * Walk by segments to build transaction.
     *
     * @throws EbicsException
     * @throws IncorrectResponseEbicsException
     */
    private function initializeTransaction(callable $requestClosure): InitializationTransaction
    {
        $transaction = $this->transactionFactory->createInitializationTransaction();

        $request = call_user_func($requestClosure);

        $segment = $this->retrieveInitializationSegment($request);
        $transaction->setInitializationSegment($segment);

        return $transaction;
    }

    /**
     * @throws EbicsException
     * @throws IncorrectResponseEbicsException
     */
    private function retrieveInitializationSegment(Request $request): InitializationSegment
    {
        $response = $this->httpClient->post($this->bank->getUrl(), $request);

        $this->checkH00XReturnCode($request, $response);

        return $this->responseHandler->extractInitializationSegment($response, $this->keyring);
    }

    /**
     * Walk by segments to build transaction.
     *
     * @param callable $requestClosure
     * @param callable|null $ackClosure Custom closure to handle acknowledge.
     *
     * @return DownloadTransaction
     * @throws EbicsException
     * @throws EbicsResponseException
     */
    private function downloadTransaction(callable $requestClosure, ?callable $ackClosure = null): DownloadTransaction
    {
        $transaction = $this->transactionFactory->createDownloadTransaction();

        $segmentNumber = null;
        $isLastSegment = null;

        $request = call_user_func_array($requestClosure, [$segmentNumber, $isLastSegment]);

        $segment = $this->retrieveDownloadSegment($request);
        $transaction->addSegment($segment);

        $lastSegment = $transaction->getLastSegment();

        while (!$lastSegment->isLastSegmentNumber()) {
            $nextSegmentNumber = $lastSegment->getNextSegmentNumber();
            $isLastNextSegmentNumber = $lastSegment->isLastNextSegmentNumber();

            $request = $this->requestFactory->createTransferDownload(
                $lastSegment->getTransactionId(),
                $nextSegmentNumber,
                $isLastNextSegmentNumber
            );

            $segment = $this->retrieveDownloadSegment($request);
            $transaction->addSegment($segment);

            $segment->setNumSegments($lastSegment->getNumSegments());
            $segment->setTransactionKey($lastSegment->getTransactionKey());

            $lastSegment = $segment;
        }

        if (null !== $ackClosure) {
            $acknowledged = call_user_func_array($ackClosure, [$transaction]);
        } else {
            $acknowledged = true;
        }

        $this->transferReceipt($transaction, $acknowledged);

        $orderDataEncoded = $this->bufferFactory->create();
        foreach ($transaction->getSegments() as $segment) {
            $orderDataEncoded->write($segment->getOrderData());
            $segment->setOrderData('');
        }
        $orderDataEncoded->rewind();

        $orderDataDecoded = $this->bufferFactory->create();
        while (!$orderDataEncoded->eof()) {
            $orderDataDecoded->write(base64_decode($orderDataEncoded->read()));
        }
        $orderDataDecoded->rewind();
        unset($orderDataEncoded);

        $orderDataCompressed = $this->bufferFactory->create();
        $this->cryptService->decryptOrderDataCompressed(
            $this->keyring,
            $orderDataDecoded,
            $orderDataCompressed,
            $lastSegment->getTransactionKey()
        );
        unset($orderDataDecoded);

        $orderData = $this->bufferFactory->create();
        $this->zipService->uncompress($orderDataCompressed, $orderData);
        unset($orderDataCompressed);

        $transaction->setOrderData($orderData->readContent());
        unset($orderData);

        return $transaction;
    }

    /**
     * @throws EbicsException
     */
    private function retrieveDownloadSegment(Request $request): DownloadSegment
    {
        $response = $this->httpClient->post($this->bank->getUrl(), $request);

        $this->checkH00XReturnCode($request, $response);

        return $this->responseHandler->extractDownloadSegment($response);
    }

    /**
     * @throws EbicsException
     * @throws EbicsResponseException
     * @throws IncorrectResponseEbicsException
     */
    private function uploadTransaction(callable $requestClosure): UploadTransaction
    {
        $transaction = $this->transactionFactory->createUploadTransaction();
        $transaction->setKey($this->cryptService->generateTransactionKey());

        $request = call_user_func_array($requestClosure, [$transaction]);

        $response = $this->httpClient->post($this->bank->getUrl(), $request);
        $this->checkH00XReturnCode($request, $response);

        $uploadSegment = $this->responseHandler->extractUploadSegment($request, $response);
        $transaction->setInitialization($uploadSegment);

        $segment = $this->segmentFactory->createTransferSegment();
        $segment->setTransactionKey($transaction->getKey());
        $segment->setSegmentNumber(1);
        $segment->setIsLastSegment(true);
        $segment->setNumSegments($transaction->getNumSegments());
        $segment->setOrderData($transaction->getOrderData());
        $segment->setTransactionId($transaction->getInitialization()->getTransactionId());

        if ($segment->getTransactionId()) {
            $transaction->addSegment($segment);
            $transaction->setKey($segment->getTransactionId());
            $this->transferTransfer($transaction);
        }

        return $transaction;
    }

    private function createStandardOrderResult(Response $response): StandardOrderResult
    {
        $orderResult = $this->orderResultFactory->createStandardOrderResult();
        $orderResult->setResponse($response);

        return $orderResult;
    }

    private function createInitializationOrderResult(InitializationTransaction $transaction): InitializationOrderResult
    {
        $orderResult = $this->orderResultFactory->createInitializationOrderResult();
        $orderResult->setTransaction($transaction);
        $orderResult->setData($transaction->getOrderData());
        $orderResult->setDocument($this->documentFactory->createXml($orderResult->getData()));

        return $orderResult;
    }

    private function createDownloadOrderResult(
        DownloadTransaction $transaction,
        string $parserFormat
    ): DownloadOrderResult {
        $orderResult = $this->orderResultFactory->createDownloadOrderResult();
        $orderResult->setTransaction($transaction);
        $orderResult->setData($transaction->getOrderData());

        switch ($parserFormat) {
            case self::FILE_PARSER_FORMAT_TEXT:
                break;
            case self::FILE_PARSER_FORMAT_XML:
                $orderResult->setDocument($this->documentFactory->createXml($orderResult->getData()));
                break;
            case self::FILE_PARSER_FORMAT_XML_FILES:
                $files = $this->xmlService->extractFilesFromString($orderResult->getData());
                $orderResult->setDataFiles($this->documentFactory->createMultipleXml($files));
                break;
            case self::FILE_PARSER_FORMAT_ZIP_FILES:
                $orderResult->setDataFiles($this->zipService->extractFilesFromString($orderResult->getData()));
                break;
            default:
                throw new LogicException('Incorrect format');
        }

        return $orderResult;
    }

    private function createUploadOrderResult(
        UploadTransaction $transaction,
        OrderDataInterface $document
    ): UploadOrderResult {
        $orderResult = $this->orderResultFactory->createUploadOrderResult();
        $orderResult->setTransaction($transaction);
        $orderResult->setDataDocument($document);
        $orderResult->setData($document->getContent());

        return $orderResult;
    }

    /**
     * @inheritDoc
     */
    public function getKeyring(): Keyring
    {
        return $this->keyring;
    }

    /**
     * @inheritDoc
     */
    public function getBank(): Bank
    {
        return $this->bank;
    }

    /**
     * @inheritDoc
     */
    public function getUser(): User
    {
        return $this->user;
    }

    /**
     * Create new signature.
     *
     * @param string $type
     * @param array|null $details
     * @return SignatureInterface
     * @throws PasswordEbicsException
     */
    private function createUserSignature(string $type, ?array $details = null): SignatureInterface
    {
        switch ($type) {
            case SignatureInterface::TYPE_A:
                if (null !== $details) {
                    $keyPair = new KeyPair(
                        new Key($details['publickey'], $details['publickey_type']),
                        new Key($details['privatekey'], $details['privatekey_type']),
                        $this->keyring->getPassword()
                    );
                    if (isset($details['certificate'])) {
                        $certificateGenerator = new ContentX509Generator();
                        $certificateGenerator->setAContent($details['certificate']);
                    } else {
                        $certificateGenerator = null;
                    }
                } else {
                    $keyPair = $this->cryptService->generateKeyPair($this->keyring->getPassword());
                    $certificateGenerator = $this->keyring->getCertificateGenerator();
                }

                $signature = $this->signatureFactory->createSignatureAFromKeys(
                    $keyPair,
                    $certificateGenerator
                );
                break;
            case SignatureInterface::TYPE_E:
                $keyPair = $this->cryptService->generateKeyPair($this->keyring->getPassword());
                $signature = $this->signatureFactory->createSignatureEFromKeys(
                    $keyPair,
                    $this->keyring->getCertificateGenerator()
                );
                break;
            case SignatureInterface::TYPE_X:
                $keyPair = $this->cryptService->generateKeyPair($this->keyring->getPassword());
                $signature = $this->signatureFactory->createSignatureXFromKeys(
                    $keyPair,
                    $this->keyring->getCertificateGenerator()
                );
                break;
            default:
                throw new LogicException(sprintf('Type "%s" not allowed', $type));
        }

        return $signature;
    }

    /**
     * @inheritDoc
     */
    public function getResponseHandler(): ResponseHandler
    {
        return $this->responseHandler;
    }

    /**
     * @inheritDoc
     * @throws PasswordEbicsException
     */
    public function checkKeyring(): bool
    {
        return $this->cryptService->checkPrivateKey(
            $this->keyring->getUserSignatureX()->getPrivateKey(),
            $this->keyring->getPassword()
        );
    }

    /**
     * @inheritDoc
     * @throws PasswordEbicsException
     */
    public function changeKeyringPassword(string $newPassword): void
    {
        $keyPair = $this->cryptService->changePrivateKeyPassword(
            new KeyPair(
                $this->keyring->getUserSignatureA()->getPublicKey(),
                $this->keyring->getUserSignatureA()->getPrivateKey(),
                $this->keyring->getPassword()
            ),
            $this->keyring->getPassword(),
            $newPassword
        );

        $signature = $this->signatureFactory->createSignatureAFromKeys(
            $keyPair,
            $this->keyring->getCertificateGenerator()
        );

        $this->keyring->setUserSignatureA($signature);

        $keyPair = $this->cryptService->changePrivateKeyPassword(
            new KeyPair(
                $this->keyring->getUserSignatureX()->getPublicKey(),
                $this->keyring->getUserSignatureX()->getPrivateKey(),
                $this->keyring->getPassword()
            ),
            $this->keyring->getPassword(),
            $newPassword
        );

        $signature = $this->signatureFactory->createSignatureXFromKeys(
            $keyPair,
            $this->keyring->getCertificateGenerator()
        );

        $this->keyring->setUserSignatureX($signature);

        $keyPair = $this->cryptService->changePrivateKeyPassword(
            new KeyPair(
                $this->keyring->getUserSignatureE()->getPublicKey(),
                $this->keyring->getUserSignatureE()->getPrivateKey(),
                $this->keyring->getPassword()
            ),
            $this->keyring->getPassword(),
            $newPassword
        );

        $signature = $this->signatureFactory->createSignatureEFromKeys(
            $keyPair,
            $this->keyring->getCertificateGenerator()
        );

        $this->keyring->setUserSignatureE($signature);

        $this->keyring->setPassword($newPassword);
    }
}
