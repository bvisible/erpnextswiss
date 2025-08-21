<?php

namespace EbicsApi\Ebics\Handlers\Traits;

use DOMNode;
use DOMNodeList;
use EbicsApi\Ebics\Exceptions\AlgoEbicsException;

/**
 * Class C14NTrait manage c14n building.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
trait C14NTrait
{
    /**
     * Extract C14N content by path from the XML DOM.
     *
     * @throws AlgoEbicsException
     */
    private function calculateC14N(
        DOMNodeList $nodes,
        string $algorithm = 'REC-xml-c14n-20010315'
    ): string {
        switch ($algorithm) {
            case 'REC-xml-c14n-20010315':
                $exclusive = false;
                $withComments = false;
                break;
            default:
                throw new AlgoEbicsException(sprintf('Define algo for %s', $algorithm));
        }
        $result = '';

        /* @var $node DOMNode */
        foreach ($nodes as $node) {
            $result .= $node->C14N($exclusive, $withComments);
        }

        return trim($result);
    }
}
