<?php

namespace EbicsApi\Ebics\Models\X509;

use DateTime;
use EbicsApi\Ebics\Contracts\Crypt\X509Interface;
use EbicsApi\Ebics\Contracts\X509GeneratorInterface;
use EbicsApi\Ebics\Factories\Crypt\X509Factory;
use LogicException;

/**
 * Generator simulation for already created certificates and loaded from content.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class ContentX509Generator implements X509GeneratorInterface
{
    private X509Factory $x509Factory;

    private string $aContent;

    private string $eContent;

    private string $xContent;

    public function __construct()
    {
        $this->x509Factory = new X509Factory();
    }

    public function setAContent(string $content): void
    {
        $this->aContent = $content;
    }

    public function setEContent(string $content): void
    {
        $this->eContent = $content;
    }

    public function setXContent(string $content): void
    {
        $this->xContent = $content;
    }

    public function generateAX509(): X509Interface
    {
        $cert = $this->x509Factory->create();

        $cert->loadX509($this->aContent);

        return $cert;
    }

    public function generateEX509(): X509Interface
    {
        $cert = $this->x509Factory->create();

        $cert->loadX509($this->eContent);

        return $cert;
    }

    public function generateXX509(): X509Interface
    {
        $cert = $this->x509Factory->create();

        $cert->loadX509($this->xContent);

        return $cert;
    }

    public function generateIssuerX509(): X509Interface
    {
        throw new LogicException('Method should not be called.');
    }

    public function getAX509Context(): X509Context
    {
        return new X509Context('', new DateTime(), new DateTime());
    }

    public function getEX509Context(): X509Context
    {
        return new X509Context('', new DateTime(), new DateTime());
    }

    public function getXX509Context(): X509Context
    {
        return new X509Context('', new DateTime(), new DateTime());
    }

    public function getIssuerX509Context(): X509Context
    {
        return new X509Context('', new DateTime(), new DateTime());
    }
}
