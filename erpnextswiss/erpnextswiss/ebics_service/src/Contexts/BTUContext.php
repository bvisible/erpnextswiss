<?php

namespace EbicsApi\Ebics\Contexts;

use EbicsApi\Ebics\Contracts\OrderContextInterface;

/**
 * Class BTUContext context container for BTU orders - requires EBICS 3.0
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class BTUContext extends BTFContext
{
    private string $fileName;

    public function setFileName(string $fileName): BTUContext
    {
        $this->fileName = $fileName;

        return $this;
    }

    public function getFileName(): string
    {
        return $this->fileName;
    }

    public static function resolveInstance(?OrderContextInterface $orderContext = null): BTUContext
    {
        if ($orderContext instanceof BTUContext) {
            return $orderContext;
        }

        return new BTUContext();
    }
}
