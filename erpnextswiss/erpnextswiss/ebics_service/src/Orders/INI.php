<?php

namespace EbicsApi\Ebics\Orders;

use EbicsApi\Ebics\Builders\Request\BodyBuilder;
use EbicsApi\Ebics\Builders\Request\DataTransferBuilder;
use EbicsApi\Ebics\Builders\Request\HeaderBuilder;
use EbicsApi\Ebics\Builders\Request\OrderDetailsBuilder;
use EbicsApi\Ebics\Builders\Request\RootBuilder;
use EbicsApi\Ebics\Builders\Request\StaticBuilder;
use EbicsApi\Ebics\Contexts\RequestContext;
use EbicsApi\Ebics\Contracts\SignatureInterface;
use EbicsApi\Ebics\Models\Customer;
use EbicsApi\Ebics\Models\Http\Request;
use EbicsApi\Ebics\Models\Order\StandardOrder;
use EbicsApi\Ebics\Models\Order\StandardOrderResult;

/**
 * Make INI request.
 * Send to the bank public signature of signature A005|A006.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class INI extends StandardOrder
{
    private SignatureInterface $signatureA;

    public function __construct(?RequestContext $context = null)
    {
        $this->context = $context;
    }

    public function createRequest(): Request
    {
        $this->signatureA = $this->context->getKeyring()->getUserSignatureA();

        return $this->buildRequest();
    }

    public function afterExecute(StandardOrderResult $orderResult): void
    {
        $this->context->getKeyring()->setUserSignatureA($this->signatureA);
    }

    private function buildRequest(): Request
    {
        $orderData = $this->createOrderData();

        $this->context
            ->setOrderType('INI')
            ->setOrderData($orderData->getContent());

        return $this->requestFactory
            ->createRequestBuilderInstance()
            ->addContainerUnsecured(function (RootBuilder $builder) {
                $builder->addHeader(function (HeaderBuilder $builder) {
                    $builder->addStatic(function (StaticBuilder $builder) {
                        $builder
                            ->addHostId($this->context->getBank()->getHostId())
                            ->addPartnerId($this->context->getUser()->getPartnerId())
                            ->addUserId($this->context->getUser()->getUserId())
                            ->addProduct($this->context->getProduct(), $this->context->getLanguage())
                            ->addOrderDetails(function (OrderDetailsBuilder $orderDetailsBuilder) {
                                $this->requestFactory->addOrderType(
                                    $orderDetailsBuilder,
                                    $this->context->getOrderType(),
                                    OrderDetailsBuilder::ORDER_ATTRIBUTE_DZNNN
                                );
                            })
                            ->addSecurityMedium(StaticBuilder::SECURITY_MEDIUM_0000);
                    })->addMutable();
                })->addBody(function (BodyBuilder $builder) {
                    $builder->addDataTransfer(function (DataTransferBuilder $builder) {
                        $builder->addOrderData($this->context->getOrderData());
                    });
                });
            })
            ->popInstance();
    }

    public function createOrderData(): Customer
    {
        $xml = new Customer();

        // Add SignaturePubKeyOrderData to root.
        $xmlSignaturePubKeyOrderData =  $xml->createElementNS(
            'http://www.ebics.org/' . $this->orderDataHandler->getS00XVersion(),
            'SignaturePubKeyOrderData'
        );

        $xmlSignaturePubKeyOrderData->setAttributeNS(
            'http://www.w3.org/2000/xmlns/',
            'xmlns:ds',
            'http://www.w3.org/2000/09/xmldsig#'
        );
        $xml->appendChild($xmlSignaturePubKeyOrderData);

        // Add SignaturePubKeyInfo to SignaturePubKeyOrderData.
        $xmlSignaturePubKeyInfo = $xml->createElement('SignaturePubKeyInfo');
        $xmlSignaturePubKeyOrderData->appendChild($xmlSignaturePubKeyInfo);

        if ($this->context->getKeyring()->isCertified()) {
            $this->orderDataHandler->handleX509Data($xmlSignaturePubKeyInfo, $xml, $this->signatureA);
        }

        $this->orderDataHandler->handleSignaturePubKey(
            $xmlSignaturePubKeyInfo,
            $xml,
            $this->signatureA,
            $this->context->getDateTime()
        );

        // Add SignatureVersion to SignaturePubKeyInfo.
        $xmlSignatureVersion = $xml->createElement('SignatureVersion');
        $xmlSignatureVersion->nodeValue = $this->context->getKeyring()->getUserSignatureAVersion();
        $xmlSignaturePubKeyInfo->appendChild($xmlSignatureVersion);

        // Add PartnerID to SignaturePubKeyOrderData.
        $this->orderDataHandler->handlePartnerId($xmlSignaturePubKeyOrderData, $xml);

        // Add UserID to SignaturePubKeyOrderData.
        $this->orderDataHandler->handleUserId($xmlSignaturePubKeyOrderData, $xml);

        return $xml;
    }
}
