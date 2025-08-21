<?php

namespace EbicsApi\Ebics\Models;

use EbicsApi\Ebics\Contracts\SignatureInterface;
use EbicsApi\Ebics\Models\Crypt\Key;

/**
 * Class Signature represents Signature model.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class Signature implements SignatureInterface
{
    private string $type;
    private Key $publicKey;
    private ?Key $privateKey;
    private ?string $certificateContent;

    /**
     * @param string $type
     * @param Key $publicKey
     * @param Key|null $privateKey
     */
    public function __construct(string $type, Key $publicKey, ?Key $privateKey)
    {
        $this->type = $type;
        $this->publicKey = $publicKey;
        $this->privateKey = $privateKey;
    }

    /**
     * @inheritDoc
     */
    public function getType(): string
    {
        return $this->type;
    }

    /**
     * @inheritDoc
     */
    public function getPublicKey(): Key
    {
        return $this->publicKey;
    }

    /**
     * @inheritDoc
     */
    public function getPrivateKey(): ?Key
    {
        return $this->privateKey ?? null;
    }

    /**
     * @inheritDoc
     */
    public function setCertificateContent(?string $certificateContent): void
    {
        $this->certificateContent = $certificateContent;
    }

    /**
     * @inheritDoc
     */
    public function getCertificateContent(): ?string
    {
        return $this->certificateContent ?? null;
    }
}
