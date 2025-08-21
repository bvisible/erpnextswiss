<?php

namespace EbicsApi\Ebics\Orders;

use EbicsApi\Ebics\Builders\Request\RootBuilder;
use EbicsApi\Ebics\Models\Http\Request;
use EbicsApi\Ebics\Models\Order\StandardOrder;

/**
 * Download supported protocol versions for the Bank.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class HEV extends StandardOrder
{
    public function createRequest(): Request
    {
        return $this->buildRequest();
    }

    private function buildRequest(): Request
    {
        return $this->requestFactory->createRequestBuilderInstance()
            ->addContainerHEV(function (RootBuilder $builder) {
                $builder->addHostId($this->context->getBank()->getHostId());
            })
            ->popInstance();
    }
}
