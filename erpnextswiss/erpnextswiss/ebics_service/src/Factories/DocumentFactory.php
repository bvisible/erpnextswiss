<?php

namespace EbicsApi\Ebics\Factories;

use EbicsApi\Ebics\Models\TxtDocument;
use EbicsApi\Ebics\Models\XmlDocument;

/**
 * Class DocumentFactory represents producers for the @see Document.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class DocumentFactory
{
    /**
     * @param string $content requires already UTF-8 encoded content
     * @return XmlDocument
     */
    public function createXml(string $content): XmlDocument
    {
        $document = new XmlDocument();
        $document->loadXML($content);

        return $document;
    }

    /**
     * @param string $content requires already UTF-8 encoded content
     * @return TxtDocument
     */
    public function createTxt(string $content): TxtDocument
    {
        $document = new TxtDocument();
        $document->setContent($content);

        return $document;
    }

    /**
     * @param string[] $contents
     *
     * @return XmlDocument[]
     */
    public function createMultipleXml(array $contents): array
    {
        $documents = [];
        foreach ($contents as $key => $content) {
            $documents[$key] = $this->createXml($content);
        }

        return $documents;
    }
}
