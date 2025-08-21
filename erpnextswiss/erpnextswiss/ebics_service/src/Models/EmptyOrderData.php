<?php

namespace EbicsApi\Ebics\Models;

use EbicsApi\Ebics\Contracts\OrderDataInterface;

/**
 * Class EmptyOrderData.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class EmptyOrderData extends DOMDocument implements OrderDataInterface
{
    public function getContent(): string
    {
        return ' ';
    }

    public function getFormattedContent(): string
    {
        return ' ';
    }
}
