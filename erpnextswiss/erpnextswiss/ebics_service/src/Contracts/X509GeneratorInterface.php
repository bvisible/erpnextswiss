<?php

namespace EbicsApi\Ebics\Contracts;

use EbicsApi\Ebics\Contracts\Crypt\X509Interface;
use EbicsApi\Ebics\Models\X509\X509Context;

/**
 * X509 Factory Interface representation.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin, Guillaume Sainthillier
 */
interface X509GeneratorInterface
{
    /**
     * Generate a X509 (Authorization) and returns its content.
     *
     * @return X509Interface
     */
    public function generateAX509(): X509Interface;

    /**
     * Generate a X509 (Authorization) and returns its content.
     *
     * @return X509Interface
     */
    public function generateEX509(): X509Interface;

    /**
     * Generate a X509 (Authorization) and returns its content.
     *
     * @return X509Interface
     */
    public function generateXX509(): X509Interface;

    /**
     * Generate issuer X509 using settled public and private key.
     * @return X509Interface
     */
    public function generateIssuerX509(): X509Interface;

    public function getAX509Context(): X509Context;

    public function getEX509Context(): X509Context;

    public function getXX509Context(): X509Context;

    public function getIssuerX509Context(): X509Context;
}
