# SPDX-FileCopyrightText: 2024-present Silvano Cerza <silvanocerza@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import os
from pathlib import Path
from typing import Any, Dict, List

import yaml

from orchestria.settings import SETTINGS
from orchestria.tool.config import Config


class Tool:
    def __init__(
        self,
        name: str,
        description: str | None,
        language: str,
        entrypoint: str,
        version: str,
        inputs_schema: Dict[str, str],
        outputs_schema: Dict[str, str],
        secrets: List[str] | Dict[str, str] | None = None,
    ):
        self.name = name
        self.description = description
        self._language = language
        self._entrypoint = entrypoint
        self._version = version
        self.inputs_schema = inputs_schema
        self.outputs_schema = outputs_schema
        # TODO: Ugly, this should be passed as a parameter maybe.
        # Or maybe we should overhaul this SETTINGS thing cause I don't like it.
        if versions := SETTINGS.registry["tools"][name]:
            self._source_path = list(versions.values())[0]

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
            version=config.version,
            inputs_schema=config.inputs_schema,
            outputs_schema=config.outputs_schema,
            secrets=config.secrets,
        )

    @classmethod
    def from_file(cls, path: Path, name: str = "") -> "Tool":
        """
        Load a tool from a yaml file.
        If there are multiple tools in the file and the name is not provided it will raise.
        """
        configs = yaml.safe_load(path.read_text(encoding="utf-8"))
        # This must be a dict
        assert isinstance(configs, dict)

        if "tools" not in configs:
            msg = f"No tools found in file '{path}'"
            raise ValueError(msg)

        configs = configs["tools"]

        if not isinstance(configs, list):
            msg = "Tools must be a list"
            raise ValueError(msg)

        if len(configs) > 1 and not name:
            msg = "Multiple tools in file, name must be provided"
            raise ValueError(msg)

        for c in configs:
            if c["name"] == name:
                # TODO: This is quite ugly, maybe we should pass the version as a parameter.
                # For the time being it's fine as Tool is always using the latest version in any case.
                return cls.from_config(Config(**c, version=""))

        msg = f"Tool '{name}' not found in file '{path}'"
        raise ValueError(msg)

    def run(self, args: str) -> Dict[str, Any]:
        if self._language != "python":
            raise NotImplementedError("Only Python tools are supported as of now")

        import re
        import subprocess

        # Some models are stupid and generate JSON with single quotes.
        args = re.sub(r"(?<!\\)'", '"', args)

        # We need to replace this or the shell will interpret them.
        args = args.replace("{", "{{").replace("}", "}}")

        # We use a custom data dir so that we don't pollute the user's environment with tons of venvs.
        # This way we can also delete the env easily when the user wants to delete a tool.
        command = ["hatch", "--data-dir", ".venv", "run", self._entrypoint, f"'{args}'"]
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
