<?php

namespace EbicsApi\Ebics\Orders;

use EbicsApi\Ebics\Builders\Request\BodyBuilder;
use EbicsApi\Ebics\Builders\Request\DataEncryptionInfoBuilder;
use EbicsApi\Ebics\Builders\Request\DataTransferBuilder;
use EbicsApi\Ebics\Builders\Request\HeaderBuilder;
use EbicsApi\Ebics\Builders\Request\MutableBuilder;
use EbicsApi\Ebics\Builders\Request\OrderDetailsBuilder;
use EbicsApi\Ebics\Builders\Request\RootBuilder;
use EbicsApi\Ebics\Builders\Request\StaticBuilder;
use EbicsApi\Ebics\Contexts\FULContext;
use EbicsApi\Ebics\Contexts\RequestContext;
use EbicsApi\Ebics\Contracts\OrderDataInterface;
use EbicsApi\Ebics\Exceptions\MethodNotImplemented;
use EbicsApi\Ebics\Models\Http\Request;
use EbicsApi\Ebics\Models\Keyring;
use EbicsApi\Ebics\Models\Order\UploadOrder;
use EbicsApi\Ebics\Models\UserSignature;

/**
 * Standard order type for submitting the files to the bank. Using this order type ensures a
 * transparent transfer of files of any format.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class FUL extends UploadOrder
{
    private FULContext $fulContext;

    public function __construct(
        FULContext $fulContext,
        OrderDataInterface $orderData,
        ?RequestContext $context = null
    ) {
        $this->fulContext = $fulContext;
        $this->orderData = $orderData;
        $this->context = $context;
    }

    public function prepareContext(): void
    {
        parent::prepareContext();
        if (null === $this->fulContext->getCountryCode()) {
            $this->fulContext->setCountryCode($this->context->getBank()->getCountryCode());
        }
    }

    public function createRequest(): Request
    {
        if ($this->getVersion() === Keyring::VERSION_30) {
            throw new MethodNotImplemented('3.0');
        }

        return $this->buildRequest();
    }

    private function buildRequest(): Request
    {
        $signatureData = new UserSignature();
        $this->userSignatureHandler->handle($signatureData, $this->transaction->getDigest());

        $this->context
            ->setOrderType('FUL')
            ->setTransactionKey($this->transaction->getKey())
            ->setNumSegments($this->transaction->getNumSegments())
            ->setSignatureData($signatureData);

        return $this->requestFactory
            ->createRequestBuilderInstance()
            ->addContainerSecured(function (RootBuilder $builder) {
                $builder->addHeader(function (HeaderBuilder $builder) {
                    $builder->addStatic(function (StaticBuilder $builder) {
                        $builder
                            ->addHostId($this->context->getBank()->getHostId())
                            ->addRandomNonce()
                            ->addTimestamp($this->context->getDateTime())
                            ->addPartnerId($this->context->getUser()->getPartnerId())
                            ->addUserId($this->context->getUser()->getUserId())
                            ->addProduct($this->context->getProduct(), $this->context->getLanguage())
                            ->addOrderDetails(function (OrderDetailsBuilder $orderDetailsBuilder) {
                                $this->requestFactory
                                    ->addOrderType(
                                        $orderDetailsBuilder,
                                        $this->context->getOrderType(),
                                        $this->context->getWithES() ?
                                            OrderDetailsBuilder::ORDER_ATTRIBUTE_OZHNN :
                                            OrderDetailsBuilder::ORDER_ATTRIBUTE_DZHNN
                                    );
                                $this->addFULOrderParams($orderDetailsBuilder);
                            })
                            ->addBankPubKeyDigests(
                                $this->context->getKeyring()->getBankSignatureXVersion(),
                                $this->requestFactory->signDigest($this->context->getKeyring()->getBankSignatureX()),
                                $this->context->getKeyring()->getBankSignatureEVersion(),
                                $this->requestFactory->signDigest($this->context->getKeyring()->getBankSignatureE())
                            )
                            ->addSecurityMedium(StaticBuilder::SECURITY_MEDIUM_0000)
                            ->addNumSegments($this->context->getNumSegments());
                    })->addMutable(function (MutableBuilder $builder) {
                        $builder->addTransactionPhase(MutableBuilder::PHASE_INITIALIZATION);
                    });
                })->addBody(function (BodyBuilder $builder) {
                    $builder->addDataTransfer(function (DataTransferBuilder $builder) {
                        $builder
                            ->addDataEncryptionInfo(function (DataEncryptionInfoBuilder $builder) {
                                $builder
                                    ->addEncryptionPubKeyDigest($this->context->getKeyring())
                                    ->addTransactionKey(
                                        $this->context->getTransactionKey(),
                                        $this->context->getKeyring()
                                    );
                            })
                            ->addSignatureData($this->context->getSignatureData(), $this->context->getTransactionKey());
                    });
                });
            })
            ->popInstance();
    }

    private function addFULOrderParams(OrderDetailsBuilder $orderDetailsBuilder): void
    {
        $xmlFULOrderParams = $orderDetailsBuilder->appendEmptyElementTo(
            'FULOrderParams',
            $orderDetailsBuilder->getInstance()
        );

        $orderDetailsBuilder->addParameters($xmlFULOrderParams, $this->fulContext->getParameters());

        $orderDetailsBuilder->appendElementTo('FileFormat', $this->fulContext->getFileFormat(), $xmlFULOrderParams, [
            'CountryCode' => $this->fulContext->getCountryCode(),
        ]);
    }
}
