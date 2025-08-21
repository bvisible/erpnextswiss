<?php

namespace EbicsApi\Ebics\Contracts\Order;

use EbicsApi\Ebics\Contexts\RequestContext;
use EbicsApi\Ebics\Factories\RequestFactory;
use EbicsApi\Ebics\Handlers\OrderDataHandler;
use EbicsApi\Ebics\Handlers\UserSignatureHandler;
use EbicsApi\Ebics\Models\Http\Request;

/**
 * EBICS OrderInterface representation.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
interface OrderInterface
{
    public function prepareContext(): void;

    public function getContext(): RequestContext;

    public function createRequest(): Request;

    public function useRequestFactory(RequestFactory $requestFactory): void;

    public function useOrderDataHandler(OrderDataHandler $orderDataHandler): void;

    public function useUserSignatureHandler(UserSignatureHandler $userSignatureHandler): void;
}
