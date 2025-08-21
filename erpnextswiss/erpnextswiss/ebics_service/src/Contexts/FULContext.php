<?php

namespace EbicsApi\Ebics\Contexts;

use EbicsApi\Ebics\Contracts\OrderContextInterface;

/**
 * Class context for FUL order.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class FULContext extends FFLContext
{
    public static function resolveInstance(?OrderContextInterface $orderContext = null): FULContext
    {
        if ($orderContext instanceof FULContext) {
            return $orderContext;
        }

        return new FULContext();
    }
}
