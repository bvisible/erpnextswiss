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
 * Make HIA request.
 * Send to the bank public signatures of authentication (X002) and encryption (E002).
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class HIA extends StandardOrder
{
    private SignatureInterface $signatureE;
    private SignatureInterface $signatureX;

    public function __construct(?RequestContext $context = null)
    {
        $this->context = $context;
    }

    public function createRequest(): Request
    {
        $this->signatureE = $this->context->getKeyring()->getUserSignatureE();
        $this->signatureX = $this->context->getKeyring()->getUserSignatureX();

        return $this->buildRequest();
    }

    public function afterExecute(StandardOrderResult $orderResult): void
    {
        $this->context->getKeyring()->setUserSignatureE($this->signatureE);
        $this->context->getKeyring()->setUserSignatureX($this->signatureX);
    }

    private function buildRequest(): Request
    {
        $orderData = $this->createOrderData();

        $this->context
            ->setOrderType('HIA')
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

    private function createOrderData(): Customer
    {
        $xml = new Customer();

        // Add HIARequestOrderData to root.
        $xmlHIARequestOrderData = $xml->createElementNS(
            $this->orderDataHandler->getH00XNamespace(),
            'HIARequestOrderData'
        );
        $xmlHIARequestOrderData->setAttributeNS(
            'http://www.w3.org/2000/xmlns/',
            'xmlns:ds',
            'http://www.w3.org/2000/09/xmldsig#'
        );

        $xml->appendChild($xmlHIARequestOrderData);

        // Add AuthenticationPubKeyInfo to HIARequestOrderData.
        $xmlAuthenticationPubKeyInfo = $xml->createElement('AuthenticationPubKeyInfo');
        $xmlHIARequestOrderData->appendChild($xmlAuthenticationPubKeyInfo);

        if ($this->context->getKeyring()->isCertified()) {
            $this->orderDataHandler->handleX509Data($xmlAuthenticationPubKeyInfo, $xml, $this->signatureX);
        }

        $this->orderDataHandler->handleAuthenticationPubKey(
            $xmlAuthenticationPubKeyInfo,
            $xml,
            $this->signatureX,
            $this->context->getDateTime()
        );

        // Add AuthenticationVersion to AuthenticationPubKeyInfo.
        $xmlAuthenticationVersion = $xml->createElement('AuthenticationVersion');
        $xmlAuthenticationVersion->nodeValue = $this->context->getKeyring()->getUserSignatureXVersion();
        $xmlAuthenticationPubKeyInfo->appendChild($xmlAuthenticationVersion);

        // Add EncryptionPubKeyInfo to HIARequestOrderData.
        $xmlEncryptionPubKeyInfo = $xml->createElement('EncryptionPubKeyInfo');
        $xmlHIARequestOrderData->appendChild($xmlEncryptionPubKeyInfo);

        if ($this->context->getKeyring()->isCertified()) {
            $this->orderDataHandler->handleX509Data($xmlEncryptionPubKeyInfo, $xml, $this->signatureE);
        }

        $this->orderDataHandler->handleEncryptionPubKey(
            $xmlEncryptionPubKeyInfo,
            $xml,
            $this->signatureE,
            $this->context->getDateTime()
        );

        // Add EncryptionVersion to EncryptionPubKeyInfo.
        $xmlEncryptionVersion = $xml->createElement('EncryptionVersion');
        $xmlEncryptionVersion->nodeValue = $this->context->getKeyring()->getUserSignatureEVersion();
        $xmlEncryptionPubKeyInfo->appendChild($xmlEncryptionVersion);

        // Add PartnerID to HIARequestOrderData.
        $this->orderDataHandler->handlePartnerId($xmlHIARequestOrderData, $xml);

        // Add UserID to HIARequestOrderData.
        $this->orderDataHandler->handleUserId($xmlHIARequestOrderData, $xml);

        return $xml;
    }
}
