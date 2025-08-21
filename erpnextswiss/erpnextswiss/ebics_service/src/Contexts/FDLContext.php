<?php

namespace EbicsApi\Ebics\Contexts;

use EbicsApi\Ebics\Contracts\EbicsClientInterface;
use EbicsApi\Ebics\Contracts\OrderContextInterface;

/**
 * Class Parameters context container for FUL/FDL orders
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class FDLContext extends FFLContext
{
    private string $parserFormat = EbicsClientInterface::FILE_PARSER_FORMAT_TEXT;

    public function setParserFormat(string $parserFormat): self
    {
        $this->parserFormat = $parserFormat;

        return $this;
    }

    public function getParserFormat(): string
    {
        return $this->parserFormat;
    }

    public static function resolveInstance(?OrderContextInterface $orderContext = null): FDLContext
    {
        if ($orderContext instanceof FDLContext) {
            return $orderContext;
        }

        return new FDLContext();
    }
}
