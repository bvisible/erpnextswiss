<?php

namespace EbicsApi\Ebics\Factories;

use EbicsApi\Ebics\Builders\Request\BodyBuilder;
use EbicsApi\Ebics\Builders\Request\DataTransferBuilder;
use EbicsApi\Ebics\Builders\Request\HeaderBuilder;
use EbicsApi\Ebics\Builders\Request\MutableBuilder;
use EbicsApi\Ebics\Builders\Request\OrderDetailsBuilder;
use EbicsApi\Ebics\Builders\Request\RequestBuilder;
use EbicsApi\Ebics\Builders\Request\RootBuilder;
use EbicsApi\Ebics\Builders\Request\StaticBuilder;
use EbicsApi\Ebics\Builders\Request\TransferReceiptBuilder;
use EbicsApi\Ebics\Contexts\RequestContext;
use EbicsApi\Ebics\Contracts\SignatureInterface;
use EbicsApi\Ebics\Exceptions\EbicsException;
use EbicsApi\Ebics\Handlers\OrderDataHandler;
use EbicsApi\Ebics\Handlers\UserSignatureHandler;
use EbicsApi\Ebics\Models\Bank;
use EbicsApi\Ebics\Models\Http\Request;
use EbicsApi\Ebics\Models\Keyring;
use EbicsApi\Ebics\Models\User;
use EbicsApi\Ebics\Services\CryptService;
use EbicsApi\Ebics\Services\DigestResolver;
use EbicsApi\Ebics\Services\ZipService;

/**
 * Class RequestFactory represents producers for the @see Request.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
abstract class RequestFactory
{
    protected Bank $bank;
    protected User $user;
    protected Keyring $keyring;
    protected RequestBuilder $requestBuilder;
    protected OrderDataHandler $orderDataHandler;
    protected DigestResolver $digestResolver;
    protected UserSignatureHandler $userSignatureHandler;
    protected CryptService $cryptService;
    protected ZipService $zipService;

    public function __construct(
        Bank $bank,
        User $user,
        Keyring $keyring,
        UserSignatureHandler $userSignatureHandler,
        OrderDataHandler $orderDataHandler,
        DigestResolver $digestResolver,
        RequestBuilder $requestBuilder,
        CryptService $cryptService,
        ZipService $zipService
    ) {
        $this->bank = $bank;
        $this->user = $user;
        $this->keyring = $keyring;
        $this->userSignatureHandler = $userSignatureHandler;
        $this->orderDataHandler = $orderDataHandler;
        $this->digestResolver = $digestResolver;
        $this->requestBuilder = $requestBuilder;
        $this->cryptService = $cryptService;
        $this->zipService = $zipService;
    }

    abstract public function createRequestBuilderInstance(): RequestBuilder;

    abstract public function addOrderType(
        OrderDetailsBuilder $orderDetailsBuilder,
        string $orderType,
        string $orderAttribute
    ): OrderDetailsBuilder;

    /**
     * @throws EbicsException
     */
    public function createTransferReceipt(string $transactionId, bool $acknowledged): Request
    {
        $context = (new RequestContext())
            ->setBank($this->bank)
            ->setTransactionId($transactionId)
            ->setReceiptCode(
                true === $acknowledged ?
                    TransferReceiptBuilder::CODE_RECEIPT_POSITIVE : TransferReceiptBuilder::CODE_RECEIPT_NEGATIVE
            );

        return $this
            ->createRequestBuilderInstance()
            ->addContainerSecured(function (RootBuilder $builder) use ($context) {
                $builder->addHeader(function (HeaderBuilder $builder) use ($context) {
                    $builder->addStatic(function (StaticBuilder $builder) use ($context) {
                        $builder
                            ->addHostId($context->getBank()->getHostId())
                            ->addTransactionId($context->getTransactionId());
                    })->addMutable(function (MutableBuilder $builder) {
                        $builder->addTransactionPhase(MutableBuilder::PHASE_RECEIPT);
                    });
                })->addBody(function (BodyBuilder $builder) use ($context) {
                    $builder->addTransferReceipt(function (TransferReceiptBuilder $builder) use ($context) {
                        $builder->addReceiptCode($context->getReceiptCode());
                    });
                });
            })
            ->popInstance();
    }

    /**
     * @throws EbicsException
     */
    public function createTransferUpload(
        string $transactionId,
        string $transactionKey,
        string $orderData,
        int $segmentNumber,
        ?bool $isLastSegment = null
    ): Request {
        $context = (new RequestContext())
            ->setBank($this->bank)
            ->setTransactionId($transactionId)
            ->setTransactionKey($transactionKey)
            ->setOrderData($orderData)
            ->setSegmentNumber($segmentNumber)
            ->setIsLastSegment($isLastSegment);

        return $this
            ->createRequestBuilderInstance()
            ->addContainerSecured(function (RootBuilder $builder) use ($context) {
                $builder->addHeader(function (HeaderBuilder $builder) use ($context) {
                    $builder->addStatic(function (StaticBuilder $builder) use ($context) {
                        $builder
                            ->addHostId($context->getBank()->getHostId())
                            ->addTransactionId($context->getTransactionId());
                    })->addMutable(function (MutableBuilder $builder) use ($context) {
                        $builder
                            ->addTransactionPhase(MutableBuilder::PHASE_TRANSFER)
                            ->addSegmentNumber($context->getSegmentNumber(), $context->getIsLastSegment());
                    });
                })->addBody(function (BodyBuilder $builder) use ($context) {
                    $builder->addDataTransfer(function (DataTransferBuilder $builder) use ($context) {
                        $builder->addOrderData($context->getOrderData(), $context->getTransactionKey());
                    });
                });
            })
            ->popInstance();
    }

    /**
     * @throws EbicsException
     */
    public function createTransferDownload(
        string $transactionId,
        int $segmentNumber,
        ?bool $isLastSegment = null
    ): Request {
        $context = (new RequestContext())
            ->setBank($this->bank)
            ->setTransactionId($transactionId)
            ->setSegmentNumber($segmentNumber)
            ->setIsLastSegment($isLastSegment);

        return $this
            ->createRequestBuilderInstance()
            ->addContainerSecured(function (RootBuilder $builder) use ($context) {
                $builder->addHeader(function (HeaderBuilder $builder) use ($context) {
                    $builder->addStatic(function (StaticBuilder $builder) use ($context) {
                        $builder
                            ->addHostId($context->getBank()->getHostId())
                            ->addTransactionId($context->getTransactionId());
                    })->addMutable(function (MutableBuilder $builder) use ($context) {
                        $builder
                            ->addTransactionPhase(MutableBuilder::PHASE_TRANSFER)
                            ->addSegmentNumber($context->getSegmentNumber(), $context->getIsLastSegment());
                    });
                })->addBody();
            })
            ->popInstance();
    }

    public function prepareRequestContext(?RequestContext $requestContext = null): RequestContext
    {
        if (null === $requestContext) {
            $requestContext = new RequestContext();
        }
        $requestContext->setKeyring($this->keyring);
        $requestContext->setBank($this->bank);
        $requestContext->setUser($this->user);

        return $requestContext;
    }

    public function signDigest(SignatureInterface $signature): string
    {
        return $this->digestResolver->signDigest($signature);
    }

    public function userSignA(string $data): string
    {
        return $this->cryptService->sign(
            $this->keyring->getUserSignatureA()->getPrivateKey(),
            $this->keyring->getPassword(),
            $this->keyring->getUserSignatureAVersion(),
            $data
        );
    }
}
