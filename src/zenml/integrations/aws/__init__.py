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
"""Integrates multiple AWS Tools as Stack Components.

The AWS integration provides a way for our users to manage their secrets
through AWS, a way to use the aws container registry. Additionally, the
Sagemaker integration submodule provides a way to run ZenML steps in
Sagemaker.
"""
from typing import List

from zenml.enums import StackComponentType
from zenml.integrations.constants import AWS
from zenml.integrations.integration import Integration
from zenml.zen_stores.models import FlavorWrapper

AWS_SECRET_MANAGER_FLAVOR = "aws"
AWS_CONTAINER_REGISTRY_FLAVOR = "aws"
AWS_SAGEMAKER_STEP_OPERATOR_FLAVOR = "sagemaker"


class AWSIntegration(Integration):
    """Definition of AWS integration for ZenML."""

    NAME = AWS
    REQUIREMENTS = ["boto3==1.21.0", "sagemaker==2.82.2"]

    @classmethod
    def flavors(cls) -> List[FlavorWrapper]:
        """Declare the stack component flavors for the AWS integration.

        Returns:
            List of stack component flavors for this integration.
        """
        return [
            FlavorWrapper(
                name=AWS_SECRET_MANAGER_FLAVOR,
                source="zenml.integrations.aws.secrets_managers"
                ".AWSSecretsManager",
                type=StackComponentType.SECRETS_MANAGER,
                integration=cls.NAME,
            ),
            FlavorWrapper(
                name=AWS_CONTAINER_REGISTRY_FLAVOR,
                source="zenml.integrations.aws.container_registries"
                ".AWSContainerRegistry",
                type=StackComponentType.CONTAINER_REGISTRY,
                integration=cls.NAME,
            ),
            FlavorWrapper(
                name=AWS_SAGEMAKER_STEP_OPERATOR_FLAVOR,
                source="zenml.integrations.aws.step_operators"
                ".SagemakerStepOperator",
                type=StackComponentType.STEP_OPERATOR,
                integration=cls.NAME,
            ),
        ]


AWSIntegration.check_installation()
