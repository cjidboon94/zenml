#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

from rich import print as rich_print

from zenml.integrations.kserve.services import KServeDeploymentService
from zenml.steps import step


@step
def kserve_predictor(
    service: KServeDeploymentService,
    data: str,
) -> None:
    """Run a inference request against the kserve prediction service.

    According to the KServe documentation, the predicted response is a JSON object
    with the following structure: {"predictions": []}.

    Args:
        service: The kserve deployment service.
        data: The data to predict.
    """

    service.start(timeout=120)  # should be a NOP if already started
    response = service.predict(data)
    rich_print(response)
