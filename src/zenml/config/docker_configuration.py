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
"""Docker configuration."""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Extra

from zenml.logger import get_logger

logger = get_logger(__name__)


class PythonEnvironmentExportMethod(Enum):
    """Different methods to export the local Python environment."""

    PIP_FREEZE = "pip_freeze"
    POETRY_EXPORT = "poetry_export"

    @property
    def command(self) -> str:
        """Shell command that outputs local python packages.

        The output string must be something that can be interpreted as a
        requirements file for pip once it's written to a file.

        Returns:
            Shell command.
        """
        return {
            PythonEnvironmentExportMethod.PIP_FREEZE: "pip freeze",
            PythonEnvironmentExportMethod.POETRY_EXPORT: "poetry export --format=requirements.txt",
        }[self]


class DockerConfiguration(BaseModel):
    """Configuration for building Docker images to run ZenML pipelines.

    Build process:
    --------------
    * No `dockerfile` specified: If any of the configuration options regarding
    requirements, environment variables or copying files require us to build an
    image, ZenML will build this image. Otherwise the `parent_image` will be
    used to run the pipeline.
    * `dockerfile` specified: ZenML will first build an image based on the
    specified Dockerfile. If any of the configuration options regarding
    requirements, environment variables or copying files require an additional
    image built on top of that, ZenML will build a second image. If not, the
    image build from the specified Dockerfile will be used to run the pipeline.

    Requirements installation order:
    --------------------------------
    Depending on the configuration of this object, requirements will be
    installed in the following order (each step optional):
    - The packages installed in your local python environment
    - The packages specified via the `requirements` attribute
    - The packages specified via the `required_integrations` and potentially
      stack requirements

    Attributes:
        parent_image: Full name of the Docker image that should be
            used as the parent for the image that will be built. Defaults to
            a ZenML image built for the active Python and ZenML version.

            Additional notes:
            * If you specify a custom image here, you need to make sure it has
            ZenML installed.
            * If this is a non-local image, the environment which is running
            the pipeline and building the Docker image needs to be able to pull
            this image.
            * If a custom `dockerfile` is specified for this configuration
            object, this parent image will be ignored.
        dockerfile: Path to a custom Dockerfile that should be built. Depending
            on the other values you specify in this configuration, the resulting
            image will be used directly to run your pipeline or ZenML will use
            it as a parent image to build on top of. See the general docstring
            of this class for more information.

            Additional notes:
            * If you specify this, the `parent_image` attribute will be ignored.
            * If you specify this, the image built from this Dockerfile needs
            to have ZenML installed.
        build_context_root: Build context root for the Docker build, only used
            when the `dockerfile` attribute is set. If this is left empty, the
            build context will only contain the Dockerfile.
        build_options: Additional options that will be passed unmodified to the
            Docker build call when building an image using the specified
            `dockerfile`. You can use this to for example specify build
            args or a target stage. See
            https://docker-py.readthedocs.io/en/stable/images.html#docker.models.images.ImageCollection.build
            for a full list of available options.
        docker_target_repository: Name of the Docker repository to which the
            image should be pushed. This repository will be appended to the
            registry URI of the container registry of your stack and should
            therefore **not** include any registry.
        replicate_local_python_environment: If not `None`, ZenML will use the
            specified method to generate a requirements file that replicates
            the packages installed in the currently running python environment.
            This requirements file will then be installed in the Docker image.
        requirements: Path to a requirements file or a list of required pip
            packages. During the image build, these requirements will be
            installed using pip. If you need to use a different tool to
            resolve and/or install your packages, please use a custom parent
            image or specify a custom `dockerfile`.
        required_integrations: List of ZenML integrations that should be
            installed. All requirements for the specified integrations will
            be installed inside the Docker image.
        install_stack_requirements: If `True`, ZenML will automatically detect
            if components of your active stack are part of a ZenML integration
            and install the corresponding requirements. If you set this to
            `False` or use custom components in your stack, you need to make
            sure these get installed by specifying them in the `requirements`
            attribute.
        environment: Dictionary of environment variables to set inside the
            Docker image.
        dockerignore: Path to a dockerignore file to use when building the
            Docker image.
        copy_files: If `True`, user files will be copied into the Docker image.
            If this is set to `False`, ZenML will not copy any of your files
            into the Docker image and you're responsible that all the files
            to run your pipeline exist in the right place.
        copy_profile: If `True`, the configuration of the active profile and
            stack will be copied into the Docker image. If this is set to
            `False`, ZenML will not copy this configuration and you're
            responsible for making sure the right stack is active inside the
            Docker image.
    """

    parent_image: Optional[str] = None
    dockerfile: Optional[str] = None
    build_context_root: Optional[str] = None
    build_options: Dict[str, Any] = {}

    target_repository: str = "zenml"

    replicate_local_python_environment: Optional[
        PythonEnvironmentExportMethod
    ] = None
    requirements: Union[None, str, List[str]] = None
    required_integrations: List[str] = []
    install_stack_requirements: bool = True

    environment: Dict[str, Any] = {}
    dockerignore: Optional[str] = None
    copy_files: bool = True
    copy_profile: bool = True

    class Config:
        """Pydantic configuration class."""

        # public attributes are immutable
        allow_mutation = False
        # prevent extra attributes during model initialization
        extra = Extra.forbid
