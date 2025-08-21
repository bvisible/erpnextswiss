<?php

namespace EbicsApi\Ebics\Services\X509;

/**
 * X509 extensions options normalizer.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Guillaume Sainthillier, Andrew Svirin
 *
 * @internal
 */
final class X509OptionsNormalizer
{
    /**
     * @param mixed|string|array $options = [
     *  'value' => '<string>',
     *  'critical' => '<bool>',
     *  'replace' => '<string>',
     * ]
     *
     * @return array = [
     *  'value' => '<string>',
     *  'critical' => '<bool>',
     *  'replace' => '<string>',
     * ]
     *
     * @see \EbicsApi\Ebics\Models\Crypt\X509::setExtension()
     */
    public static function normalizeExtensions($options): array
    {
        $critical = false;
        $replace = true;

        if (!is_array($options)) {
            $value = $options;
        } else {
            if (!isset($options['value'])) {
                $value = $options;
            } else {
                $value = $options['value'];
                if (isset($options['critical'])) {
                    $critical = $options['critical'];
                }
                if (isset($options['replace'])) {
                    $replace = $options['replace'];
                }
            }
        }

        return [
            'value' => $value,
            'critical' => $critical,
            'replace' => $replace,
        ];
    }

    public static function denormalizeDN(array $options): array
    {
        $result = [];
        foreach ($options['rdnSequence'] as $rdnSequence) {
            $result[$rdnSequence[0]['type']] = reset($rdnSequence[0]['value']);
        }

        return $result;
    }
}
