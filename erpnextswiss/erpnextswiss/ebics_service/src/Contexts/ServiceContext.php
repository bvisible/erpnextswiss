<?php

namespace EbicsApi\Ebics\Contexts;

use EbicsApi\Ebics\Contracts\OrderContextInterface;

/**
 * General service context.
 *
 * @license http://www.opensource.org/licenses/mit-license.html  MIT License
 * @author Andrew Svirin
 */
abstract class ServiceContext implements OrderContextInterface
{
    private string $serviceName;
    private ?string $scope = null;
    private ?string $serviceOption = null;
    private ?string $containerType = null;
    private string $msgName;
    private ?string $msgNameVariant = null;
    private ?string $msgNameVersion = null;
    private ?string $msgNameFormat = null;

    public function setServiceName(string $serviceName): ServiceContext
    {
        $this->serviceName = $serviceName;

        return $this;
    }

    public function getServiceName(): string
    {
        return $this->serviceName;
    }

    public function setScope(?string $scope): ServiceContext
    {
        $this->scope = $scope;

        return $this;
    }

    public function getScope(): ?string
    {
        return $this->scope;
    }

    public function setServiceOption(string $serviceOption): ServiceContext
    {
        $this->serviceOption = $serviceOption;

        return $this;
    }

    public function getServiceOption(): ?string
    {
        return $this->serviceOption;
    }

    public function setContainerType(string $containerType): self
    {
        $this->containerType = $containerType;

        return $this;
    }

    public function getContainerType(): ?string
    {
        return $this->containerType;
    }

    public function setMsgName(string $msgName): ServiceContext
    {
        $this->msgName = $msgName;

        return $this;
    }

    public function getMsgName(): string
    {
        return $this->msgName;
    }

    public function setMsgNameVariant(string $msgNameVariant): self
    {
        $this->msgNameVariant = $msgNameVariant;

        return $this;
    }

    public function getMsgNameVariant(): ?string
    {
        return $this->msgNameVariant;
    }

    public function setMsgNameVersion(?string $msgNameVersion): self
    {
        $this->msgNameVersion = $msgNameVersion;

        return $this;
    }

    public function getMsgNameVersion(): ?string
    {
        return $this->msgNameVersion;
    }

    public function setMsgNameFormat(string $msgNameFormat): self
    {
        $this->msgNameFormat = $msgNameFormat;

        return $this;
    }

    public function getMsgNameFormat(): ?string
    {
        return $this->msgNameFormat;
    }
}
