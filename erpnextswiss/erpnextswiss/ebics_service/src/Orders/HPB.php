<?php

namespace EbicsApi\Ebics\Orders;

use EbicsApi\Ebics\Builders\Request\HeaderBuilder;
use EbicsApi\Ebics\Builders\Request\OrderDetailsBuilder;
use EbicsApi\Ebics\Builders\Request\RootBuilder;
use EbicsApi\Ebics\Builders\Request\StaticBuilder;
use EbicsApi\Ebics\Contexts\RequestContext;
use EbicsApi\Ebics\Models\Http\Request;
use EbicsApi\Ebics\Models\Order\InitializationOrder;
use EbicsApi\Ebics\Models\Order\InitializationOrderResult;

/**
 * Download the Bank public signatures authentication (X002) and encryption (E002).
 * Prepare E002 and X002 bank signatures for Keyring.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class HPB extends InitializationOrder
{
    public function __construct(?RequestContext $context = null)
    {
        $this->context = $context;
    }

    public function createRequest(): Request
    {
        return $this->buildRequest();
    }

    public function afterExecute(InitializationOrderResult $orderResult): void
    {
        $signatureX = $this->orderDataHandler->retrieveAuthenticationSignature($orderResult->getDocument());
        $signatureE = $this->orderDataHandler->retrieveEncryptionSignature($orderResult->getDocument());
        $this->context->getKeyring()->setBankSignatureX($signatureX);
        $this->context->getKeyring()->setBankSignatureE($signatureE);
    }

    private function buildRequest(): Request
    {
        $this->context
            ->setOrderType('HPB');

        return $this->requestFactory
            ->createRequestBuilderInstance()
            ->addContainerSecuredNoPubKeyDigests(function (RootBuilder $builder) {
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
                                $this->requestFactory->addOrderType(
                                    $orderDetailsBuilder,
                                    $this->context->getOrderType(),
                                    $this->context->getWithES() ?
                                        OrderDetailsBuilder::ORDER_ATTRIBUTE_OZHNN :
                                        OrderDetailsBuilder::ORDER_ATTRIBUTE_DZHNN
                                );
                            })
                            ->addSecurityMedium(StaticBuilder::SECURITY_MEDIUM_0000);
                    })->addMutable();
                })->addBody();
            })
            ->popInstance();
    }
}
