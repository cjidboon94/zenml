#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Implementation of an Azure Container Registry class."""

from typing import ClassVar

from zenml.container_registries.base_container_registry import (
    BaseContainerRegistry,
)
from zenml.enums import ContainerRegistryFlavor


class AzureContainerRegistry(BaseContainerRegistry):
    """Class for Azure Container Registry."""

    # Class Configuration
    FLAVOR: ClassVar[str] = ContainerRegistryFlavor.AZURE.value
