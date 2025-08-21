<?php

namespace EbicsApi\Ebics\Models\Order;

use EbicsApi\Ebics\Contexts\RequestContext;
use EbicsApi\Ebics\Contracts\Order\OrderInterface;
use EbicsApi\Ebics\Factories\RequestFactory;
use EbicsApi\Ebics\Handlers\OrderDataHandler;
use EbicsApi\Ebics\Handlers\UserSignatureHandler;

/**
 * Order abstract class.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
abstract class Order implements OrderInterface
{
    protected ?RequestContext $context = null;

    protected RequestFactory $requestFactory;

    protected OrderDataHandler $orderDataHandler;

    protected UserSignatureHandler $userSignatureHandler;

    public function useRequestFactory(RequestFactory $requestFactory): void
    {
        $this->requestFactory = $requestFactory;
    }

    public function useOrderDataHandler(OrderDataHandler $orderDataHandler): void
    {
        $this->orderDataHandler = $orderDataHandler;
    }

    public function useUserSignatureHandler(UserSignatureHandler $userSignatureHandler): void
    {
        $this->userSignatureHandler = $userSignatureHandler;
    }

    public function getContext(): RequestContext
    {
        return $this->context;
    }

    protected function getVersion(): string
    {
        return $this->context->getKeyring()->getVersion();
    }

    public function copyContext(Order $target): void
    {
        $target->useUserSignatureHandler($this->userSignatureHandler);
        $target->useOrderDataHandler($this->orderDataHandler);
        $target->useRequestFactory($this->requestFactory);
        $target->prepareContext();
    }
}
