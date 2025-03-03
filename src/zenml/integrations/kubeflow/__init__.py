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
"""Initialization of the Kubeflow integration for ZenML.

The Kubeflow integration sub-module powers an alternative to the local
orchestrator. You can enable it by registering the Kubeflow orchestrator with
the CLI tool.
"""
from typing import List

from zenml.enums import StackComponentType
from zenml.integrations.constants import KUBEFLOW
from zenml.integrations.integration import Integration
from zenml.zen_stores.models import FlavorWrapper

KUBEFLOW_METADATA_STORE_FLAVOR = "kubeflow"
KUBEFLOW_ORCHESTRATOR_FLAVOR = "kubeflow"


class KubeflowIntegration(Integration):
    """Definition of Kubeflow Integration for ZenML."""

    NAME = KUBEFLOW
    REQUIREMENTS = ["kfp==1.8.9"]

    @classmethod
    def flavors(cls) -> List[FlavorWrapper]:
        """Declare the stack component flavors for the Kubeflow integration.

        Returns:
            List of stack component flavors for this integration.
        """
        return [
            FlavorWrapper(
                name=KUBEFLOW_METADATA_STORE_FLAVOR,
                source="zenml.integrations.kubeflow.metadata_stores.KubeflowMetadataStore",
                type=StackComponentType.METADATA_STORE,
                integration=cls.NAME,
            ),
            FlavorWrapper(
                name=KUBEFLOW_ORCHESTRATOR_FLAVOR,
                source="zenml.integrations.kubeflow.orchestrators.KubeflowOrchestrator",
                type=StackComponentType.ORCHESTRATOR,
                integration=cls.NAME,
            ),
        ]


KubeflowIntegration.check_installation()
