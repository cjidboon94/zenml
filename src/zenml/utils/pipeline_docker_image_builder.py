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
"""Implementation of Docker image builds to run ZenML pipelines."""
import contextlib
import itertools
import os
import subprocess
import sys
from pathlib import PurePath, PurePosixPath
from typing import TYPE_CHECKING, Iterator, List, Optional, Sequence, Tuple

from pydantic import BaseModel

import zenml
from zenml.config.docker_configuration import DockerConfiguration
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import ENV_ZENML_CONFIG_PATH
from zenml.integrations.registry import integration_registry
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils import docker_utils, io_utils, source_utils

if TYPE_CHECKING:
    from zenml.runtime_configuration import RuntimeConfiguration
    from zenml.stack import Stack

logger = get_logger(__name__)

DOCKER_IMAGE_WORKDIR = "/app"
DOCKER_IMAGE_ZENML_CONFIG_DIR = ".zenconfig"
DOCKER_IMAGE_ZENML_CONFIG_PATH = (
    f"{DOCKER_IMAGE_WORKDIR}/{DOCKER_IMAGE_ZENML_CONFIG_DIR}"
)

DEFAULT_DOCKER_PARENT_IMAGE = (
    f"zenmldocker/zenml:{zenml.__version__}-"
    f"py{sys.version_info.major}.{sys.version_info.minor}"
)


@contextlib.contextmanager
def _include_active_profile(
    build_context_root: str,
    load_config_path: PurePath = PurePosixPath(DOCKER_IMAGE_ZENML_CONFIG_PATH),
) -> Iterator[None]:
    """Context manager to include the active profile in a Docker build context.

    Args:
        build_context_root: The root of the build context.
        load_config_path: The path of the global configuration inside the
            image.

    Yields:
        None.
    """
    # Save a copy of the current global configuration with the
    # active profile and the active stack configuration into the build
    # context, to have the active profile and active stack accessible from
    # within the container.
    config_path = os.path.join(
        build_context_root, DOCKER_IMAGE_ZENML_CONFIG_DIR
    )
    try:
        GlobalConfiguration().copy_active_configuration(
            config_path, load_config_path=load_config_path
        )
        yield
    finally:
        fileio.rmtree(config_path)


class PipelineDockerImageBuilder(BaseModel):
    """Builds Docker images to run a ZenML pipeline.

    **Usage**:
    ```python
    class MyStackComponent(StackComponent, PipelineDockerImageBuilder):
        def method_that_requires_docker_image(self):
            image_identifier = self.build_and_push_docker_image(...)
            # use the image ID
    ```

    Attributes:
        docker_parent_image: Full name of the Docker image that should be
            used as the parent for the image that will be built. Defaults to
            a ZenML image built for the active Python and ZenML version.

            Additional information to consider:
            * If you specify a custom image here, you need to make sure it has
            ZenML installed.
            * If this is a non-local image, the environment which is running
            the pipeline and building the Docker image needs to be able to pull
            this image.
    """

    docker_parent_image: Optional[str] = None

    @staticmethod
    def _gather_requirements_files(
        docker_configuration: DockerConfiguration, stack: "Stack"
    ) -> List[Tuple[str, str]]:
        """Gathers and/or generates pip requirements files.

        Args:
            docker_configuration: Docker configuration that specifies which
                requirements to install.
            stack: The stack on which the pipeline will run.

        Raises:
            RuntimeError: If the command to export the local python packages
                failed.

        Returns:
            List of tuples (filename, file_content) of all requirements files.
            The files will be in the following order:
            - Packages installed in the local Python environment
            - User-defined requirements
            - Requirements defined by user-defined and/or stack integrations
        """
        requirements_files = []
        logger.info("Gathering requirements for Docker build:")

        # Generate requirements file for the local environment if configured
        if docker_configuration.replicate_local_python_environment:
            try:
                local_requirements = subprocess.check_output(
                    docker_configuration.replicate_local_python_environment.command,
                    shell=True,
                ).decode()
            except subprocess.CalledProcessError as e:
                raise RuntimeError(
                    "Unable to export local python packages."
                ) from e

            requirements_files.append(
                (".zenml_local_requirements", local_requirements)
            )
            logger.info("\t- Including python packages from local environment")

        # Generate/Read requirements file for user-defined requirements
        if isinstance(docker_configuration.requirements, str):
            user_requirements = io_utils.read_file_contents_as_string(
                docker_configuration.requirements
            )
            logger.info(
                "\t- Including user-defined requirements from file `%s`",
                os.path.abspath(docker_configuration.requirements),
            )
        elif isinstance(docker_configuration.requirements, List):
            user_requirements = "\n".join(docker_configuration.requirements)
            logger.info(
                "\t- Including user-defined requirements: %s",
                ", ".join(f"`{r}`" for r in docker_configuration.requirements),
            )
        else:
            user_requirements = None

        if user_requirements:
            requirements_files.append(
                (".zenml_user_requirements", user_requirements)
            )

        # Generate requirements file for all required integrations
        integration_requirements = set(
            itertools.chain.from_iterable(
                integration_registry.select_integration_requirements(
                    integration
                )
                for integration in docker_configuration.required_integrations
            )
        )

        if docker_configuration.install_stack_requirements:
            integration_requirements.update(stack.requirements())

        if integration_requirements:
            integration_requirements_list = sorted(integration_requirements)
            integration_requirements_file = "\n".join(
                integration_requirements_list
            )
            requirements_files.append(
                (
                    ".zenml_integration_requirements",
                    integration_requirements_file,
                )
            )
            logger.info(
                "\t- Including integration requirements: %s",
                ", ".join(f"`{r}`" for r in integration_requirements_list),
            )

        return requirements_files

    @staticmethod
    def _generate_zenml_pipeline_dockerfile(
        parent_image: str,
        docker_configuration: DockerConfiguration,
        requirements_files: Sequence[str] = (),
        entrypoint: Optional[str] = None,
    ) -> List[str]:
        """Generates a Dockerfile.

        Args:
            parent_image: The image to use as parent for the Dockerfile.
            docker_configuration: Docker configuration for this image build.
            requirements_files: Paths of requirements files to install.
            entrypoint: The default entrypoint command that gets executed when
                running a container of an image created by this Dockerfile.

        Returns:
            Lines of the generated Dockerfile.
        """
        lines = [f"FROM {parent_image}", f"WORKDIR {DOCKER_IMAGE_WORKDIR}"]

        if docker_configuration.copy_profile:
            lines.append(
                f"ENV {ENV_ZENML_CONFIG_PATH}={DOCKER_IMAGE_ZENML_CONFIG_PATH}"
            )

        for key, value in docker_configuration.environment.items():
            lines.append(f"ENV {key.upper()}={value}")

        for file in requirements_files:
            lines.append(f"COPY {file} .")
            lines.append(f"RUN pip install --no-cache-dir -r {file}")

        if docker_configuration.copy_files:
            lines.append("COPY . .")
        elif docker_configuration.copy_profile:
            lines.append(f"COPY {DOCKER_IMAGE_ZENML_CONFIG_DIR} .")

        lines.append("RUN chmod -R a+rw .")

        if entrypoint:
            lines.append(f"ENTRYPOINT {entrypoint}")

        return lines

    def build_docker_image(
        self,
        target_image_name: str,
        pipeline_name: str,
        docker_configuration: DockerConfiguration,
        stack: "Stack",
        entrypoint: Optional[str] = None,
    ) -> None:
        """Builds a Docker image to run a pipeline.

        Args:
            target_image_name: The name of the image to build.
            pipeline_name: Name of the pipeline for which the image(s) should
                be built.
            docker_configuration: Docker configuration that specifies what
                should be included in the image.
            stack: The stack on which the pipeline will be executed.
            entrypoint: Entrypoint to use for the final image. If left empty,
                no entrypoint will be included in the image.

        Raises:
            ValueError: If no Dockerfile and/or custom parent image is
                specified and the Docker configuration doesn't require an
                image build.
        """
        logger.info(
            "Building Docker image(s) for pipeline `%s`.", pipeline_name
        )
        requires_zenml_build = any(
            [
                docker_configuration.requirements,
                docker_configuration.required_integrations,
                docker_configuration.replicate_local_python_environment,
                docker_configuration.install_stack_requirements,
                docker_configuration.environment,
                docker_configuration.copy_files,
                docker_configuration.copy_profile,
                entrypoint,
            ]
        )

        # Fallback to the value defined on the stack component if the
        # pipeline configuration doesn't have a configured value
        parent_image = (
            docker_configuration.parent_image
            or self.docker_parent_image
            or DEFAULT_DOCKER_PARENT_IMAGE
        )

        if docker_configuration.dockerfile:
            if parent_image != DEFAULT_DOCKER_PARENT_IMAGE:
                logger.warning(
                    "You've specified both a Dockerfile and a custom parent "
                    "image, ignoring the parent image."
                )

            if requires_zenml_build:
                # We will build an additional image on top of this one later
                # to include user files and/or install requirements. The image
                # we build now will be used as the parent for the next build.
                user_image_name = f"zenml-intermediate-build:{pipeline_name}"
                parent_image = user_image_name
            else:
                # The image we'll build from the custom Dockerfile will be
                # used directly, so we tag it with the requested target name.
                user_image_name = target_image_name

            docker_utils.build_image(
                image_name=user_image_name,
                dockerfile=docker_configuration.dockerfile,
                build_context_root=docker_configuration.build_context_root,
                **docker_configuration.build_options,
            )
        elif not requires_zenml_build:
            if parent_image == DEFAULT_DOCKER_PARENT_IMAGE:
                raise ValueError(
                    "Unable to run a ZenML pipeline with the given Docker "
                    "configuration: No Dockerfile or custom parent image "
                    "specified and no files will be copied or requirements "
                    "installed."
                )
            else:
                # The parent image will be used directly to run the pipeline and
                # needs to be tagged so it gets pushed later
                docker_utils.tag_image(parent_image, target=target_image_name)

        if requires_zenml_build:
            requirement_files = self._gather_requirements_files(
                docker_configuration=docker_configuration, stack=stack
            )
            requirements_file_names = [f[0] for f in requirement_files]

            dockerfile = self._generate_zenml_pipeline_dockerfile(
                parent_image=parent_image,
                docker_configuration=docker_configuration,
                requirements_files=requirements_file_names,
                entrypoint=entrypoint,
            )

            if parent_image == DEFAULT_DOCKER_PARENT_IMAGE:
                # The default parent image is static and doesn't require a pull
                # each time
                pull_parent_image = False
            else:
                # If the image is local, we don't need to pull it. Otherwise
                # we play it safe and always pull in case the user pushed a new
                # image for the given name and tag
                pull_parent_image = not docker_utils.is_local_image(
                    parent_image
                )

            # Leave the build context empty if we don't want to copy any files
            requires_build_context = (
                docker_configuration.copy_files
                or docker_configuration.copy_profile
            )
            build_context_root = (
                source_utils.get_source_root_path()
                if requires_build_context
                else None
            )
            maybe_include_active_profile = (
                _include_active_profile(build_context_root=build_context_root)  # type: ignore[arg-type]
                if docker_configuration.copy_profile
                else contextlib.nullcontext()
            )

            with maybe_include_active_profile:
                docker_utils.build_image(
                    image_name=target_image_name,
                    dockerfile=dockerfile,
                    build_context_root=build_context_root,
                    dockerignore=docker_configuration.dockerignore,
                    extra_files=requirement_files,
                    pull=pull_parent_image,
                )

    def build_and_push_docker_image(
        self,
        pipeline_name: str,
        docker_configuration: DockerConfiguration,
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
        entrypoint: Optional[str] = None,
    ) -> str:
        """Builds and pushes a Docker image to run a pipeline.

        Use the image name returned by this method whenever you need to uniquely
        reference the pushed image in order to pull or run it.

        Args:
            pipeline_name: Name of the pipeline for which the image(s) should
                be built.
            docker_configuration: Docker configuration that specifies what
                should be included in the image.
            stack: The stack on which the pipeline will be executed.
            runtime_configuration: The runtime configuration for the pipeline
                run.
            entrypoint: Entrypoint to use for the final image. If left empty,
                no entrypoint will be included in the image.

        Returns:
            The Docker repository digest of the pushed image.

        Raises:
            RuntimeError: If the stack doesn't contain a container registry.
        """
        container_registry = stack.container_registry
        if not container_registry:
            raise RuntimeError(
                "Unable to build and push Docker image because stack "
                f"`{stack.name}` has no container registry."
            )

        target_image_name = (
            f"{container_registry.uri}/"
            f"{docker_configuration.target_repository}:{pipeline_name}"
        )

        self.build_docker_image(
            target_image_name=target_image_name,
            pipeline_name=pipeline_name,
            docker_configuration=docker_configuration,
            stack=stack,
            entrypoint=entrypoint,
        )

        repo_digest = container_registry.push_image(target_image_name)
        # Store the docker repo digest in the runtime configuration so it gets
        # tracked in the ZenStore
        runtime_configuration["docker_image"] = repo_digest

        return repo_digest
