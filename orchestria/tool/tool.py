# SPDX-FileCopyrightText: 2024-present Silvano Cerza <silvanocerza@gmail.com>
#
# SPDX-License-Identifier: BSD-3-Clause
import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List

import dulwich
import dulwich.client
import dulwich.repo

from orchestria.settings import SETTINGS
from orchestria.tool.config import Config


class Tool:
    def __init__(
        self,
        name: str,
        description: str | None,
        language: str,
        entrypoint: str,
        source: str,
        version: str,
        inputs_schema: Dict[str, str],
        outputs_schema: Dict[str, str],
        secrets: List[str] | Dict[str, str] | None = None,
    ):
        self.name = name
        self.description = description
        self._language = language
        self._entrypoint = entrypoint
        self._source = source
        self._version = version
        self.inputs_schema = inputs_schema
        self.outputs_schema = outputs_schema
        # TODO: Ugly, this should be passed as a parameter maybe.
        # Or maybe we should overhaul this SETTINGS thing cause I don't like it.
        self._source_path = SETTINGS.registry["tools"].get(f"{source}_{version}")

        if isinstance(secrets, list):
            self._secrets = {}
            for s in secrets:
                try:
                    self._secrets[s] = os.environ[s]
                except KeyError as exc:
                    msg = f"Secret '{s}' needed by tool '{name}' not found"
                    raise ValueError(msg) from exc
        else:
            self._secrets = secrets

    @classmethod
    def from_config(cls, config: Config):
        return cls(
            name=config.name,
            description=config.description,
            language=config.language,
            entrypoint=config.entrypoint,
            source=config.source,
            version=config.version,
            inputs_schema=config.inputs_schema,
            outputs_schema=config.outputs_schema,
            secrets=config.secrets,
        )

    @classmethod
    def load(cls, source: str, version: str) -> "Tool":
        """
        Load a tool from the source URL and version.

        If the tool is not found locally, it will be cloned from the source URL.
        :param source:
            Git URL of the tool, can be local or remote.
        :param version:
            Version of the tool to load, usually a tag or a commit hash.
        :return:
            Tool instance.
        """

        tool_path = SETTINGS.registry["tools"].get(f"{source}_{version}")

        if not tool_path:
            tool_path = Tool.clone_tool(source, version)
        else:
            tool_path = Path(tool_path)

        config_path = tool_path / "orchestria_tool.json"

        tool_config = json.loads(config_path.read_text(encoding="utf-8"))

        tool_config["source"] = source
        tool_config["version"] = version

        return Tool.from_config(Config(**tool_config))

    @staticmethod
    def clone_tool(source: str, version: str) -> Path:
        """
        Clones the tool from the source URL and returns the local path.
        """
        try:
            client, path = dulwich.client.get_transport_and_path(source)
        except ValueError as exc:
            raise ValueError("Invalid URL") from exc

        target_name = path.replace(".git", "") + f"_{version}"
        target_path = SETTINGS._tools_path / target_name

        target_path.mkdir(parents=True, exist_ok=True)

        client.clone(
            path, target_path=target_path, branch=version.encode(), depth=1, mkdir=False
        )

        # Check the tool is valid.
        # We do this after cloning as it's easier to check the local files
        # rather than checking the remote repository. To check remote repositories we would need to
        # to parse the URL, check the service, know the service API to get the repo files, etc.
        # This works.
        if not (target_path / "orchestria_tool.json").exists():
            shutil.rmtree(target_path)
            raise ValueError("Invalid tool repository, missing orchestria_tool.json")

        # Save the tool in the registry to ease future lookups
        # TODO: Would be better to make target_path relative to ease moving the settings folder around.
        SETTINGS.register_tool(f"{source}_{version}", str(target_path))
        return target_path

    def run(self, args: str) -> Dict[str, Any]:
        if self._language != "python":
            raise NotImplementedError("Only Python tools are supported as of now")

        import json
        import re
        import subprocess

        # Some models are stupid and generate JSON with single quotes.
        args = re.sub(r"(?<!\\)'", '"', args)

        # We need to replace this or the shell will interpret them.
        args = args.replace("{", "{{").replace("}", "}}")

        command = ["hatch", "run", self._entrypoint, f"'{args}'"]
        result = subprocess.run(
            " ".join(command),
            cwd=self._source_path,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
            env=self._secrets,
        )

        return json.loads(result.stdout)
