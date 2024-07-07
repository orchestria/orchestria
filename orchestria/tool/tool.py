# SPDX-FileCopyrightText: 2024-present Silvano Cerza <silvanocerza@gmail.com>
#
# SPDX-License-Identifier: BSD-3-Clause
import json
from pathlib import Path
from typing import Dict

from orchestria.settings import SETTINGS

from .config import Config


class Tool:
    def __init__(
        self,
        name: str,
        description: str | None,
        language: str,
        source: str,
        version: str,
        inputs_schema: Dict[str, str],
        outputs_schema: Dict[str, str],
    ):
        self.name = name
        self._description = description
        self._language = language
        self._source = source
        self._version = version
        self._inputs_schema = inputs_schema
        self._outputs_schema = outputs_schema

    @classmethod
    def from_config(cls, config: Config):
        return cls(
            name=config.name,
            description=config.description,
            language=config.language,
            source=config.source,
            version=config.version,
            inputs_schema=config.inputs_schema,
            outputs_schema=config.outputs_schema,
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
            tool_path = SETTINGS.clone_tool(source, version)
        else:
            tool_path = Path(tool_path)

        config_path = tool_path / "orchestria_tool.json"

        tool_config = json.loads(config_path.read_text(encoding="utf-8"))

        tool_config["source"] = source
        tool_config["version"] = version

        return Tool.from_config(Config(**tool_config))

    def run(self):
        pass
