<?php

namespace EbicsApi\Ebics\Factories;

use EbicsApi\Ebics\Models\Order\DownloadOrderResult;
use EbicsApi\Ebics\Models\Order\InitializationOrderResult;
use EbicsApi\Ebics\Models\Order\StandardOrderResult;
use EbicsApi\Ebics\Models\Order\UploadOrderResult;

/**
 * Class SegmentFactory represents producers for the @see OrderResult.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class OrderResultFactory
{
    public function createStandardOrderResult(): StandardOrderResult
    {
        return new StandardOrderResult();
    }

    public function createInitializationOrderResult(): InitializationOrderResult
    {
        return new InitializationOrderResult();
    }

    public function createDownloadOrderResult(): DownloadOrderResult
    {
        return new DownloadOrderResult();
    }

    public function createUploadOrderResult(): UploadOrderResult
    {
        return new UploadOrderResult();
    }
}
