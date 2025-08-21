<?php

namespace EbicsApi\Ebics\Services;

use EbicsApi\Ebics\Contracts\HttpClientInterface;
use EbicsApi\Ebics\Models\Http\Request;
use EbicsApi\Ebics\Models\Http\Response;
use LogicException;

/**
 * Class FakerHttpClient.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
final class FakerHttpClient implements HttpClientInterface
{
    /**
     * @var string
     */
    private $fixturesDir;

    /**
     * @var array
     */
    private $extendedOrderTypes;

    public function __construct(string $fixturesDir, array $extendedOrderTypes = null)
    {
        $this->fixturesDir = $fixturesDir;

        $this->extendedOrderTypes = $extendedOrderTypes ?? ['FUL', 'FDL', 'BTU', 'BTD'];
    }

    public function post(string $url, Request $request): Response
    {
        $requestContent = $request->getContent();

        $orderTypeMatches = [];
        $orderTypeMatch = preg_match(
            '/(<OrderType>|<AdminOrderType>)(?<order_type>.*?)(<\/OrderType>|<\/AdminOrderType>)/',
            $requestContent,
            $orderTypeMatches
        );

        if ($orderTypeMatch) {
            $fileFormatMatches = [];
            preg_match(
                '/<FileFormat.*>(?<file_format>.*)<\/FileFormat>/',
                $requestContent,
                $fileFormatMatches
            );

            $btfOrderParamsMatches = [];
            preg_match(
                '/<ServiceName.*>(?<service_name>.*)<\/ServiceName>.*?<MsgName.*>(?<msg_name>.*)<\/MsgName>/',
                $requestContent,
                $btfOrderParamsMatches
            );

            $svcOrderParamsMatches = [];
            preg_match(
                '/<OrderType.*>(?<order_type>.*)<\/OrderType>/',
                $requestContent,
                $svcOrderParamsMatches
            );

            $fileName = $this->fixtureFileName(
                $orderTypeMatches['order_type'],
                [
                    'file_format' => $fileFormatMatches['file_format'] ??
                        (
                        (!empty($btfOrderParamsMatches['service_name']) && !empty($btfOrderParamsMatches['msg_name'])) ?
                            $btfOrderParamsMatches['service_name'] . '.' . $btfOrderParamsMatches['msg_name']
                            : ($svcOrderParamsMatches['order_type'] ?? null)
                        ),
                ]
            );

            return $this->readFixture($fileName);
        }

        $transactionPhaseMatches = [];
        $transactionPhaseMatch = preg_match(
            '/<TransactionPhase>(?<transaction_phase>.*)<\/TransactionPhase>/',
            $requestContent,
            $transactionPhaseMatches
        );

        if ($transactionPhaseMatch) {
            return $this->fixtureTransactionPhase($transactionPhaseMatches['transaction_phase']);
        }

        $hevRequestMatch = preg_match(
            '/<ebicsHEVRequest .*>/',
            $requestContent
        );

        if ($hevRequestMatch) {
            return $this->readFixture('hev.xml');
        }

        return new Response();
    }

    /**
     * Fake Order type responses.
     *
     * @param string $orderType
     * @param array|null $options = [
     *     'file_format' => '<string>',
     * ]
     *
     * @return string
     */
    protected function fixtureFileName(string $orderType, ?array $options = null): string
    {
        if (in_array($orderType, $this->extendedOrderTypes)) {
            $fileName = sprintf(strtolower($orderType) . '.%s.xml', strtolower($options['file_format']));
        } else {
            $fileName = strtolower($orderType) . '.xml';
        }

        return $fileName;
    }

    /**
     * Fake transaction phase responses.
     *
     * @param string $transactionPhase
     *
     * @return Response
     */
    private function fixtureTransactionPhase(string $transactionPhase): Response
    {
        switch ($transactionPhase) {
            case 'Receipt':
            case 'Transfer':
                $fileName = strtolower($transactionPhase) . '.xml';
                break;
            default:
                throw new LogicException(sprintf('Faked transaction phase `%s` not supported.', $transactionPhase));
        }

        return $this->readFixture($fileName);
    }

    private function readFixture(string $fileName): Response
    {
        $fixturePath = $this->fixturesDir . '/' . $fileName;

        if (!is_file($fixturePath)) {
            throw new LogicException(sprintf('Fixtures file %s does not exists.', $fileName));
        }

        $response = new Response();

        $responseContent = file_get_contents($fixturePath);

        if (!is_string($responseContent)) {
            throw new LogicException('Response content is not valid.');
        }

        $responseContent = preg_replace('/[\r\n]/u', '', $responseContent);

        if (!is_string($responseContent)) {
            throw new LogicException('Response content is not valid.');
        }

        $response->loadXML($responseContent);

        return $response;
    }
}
