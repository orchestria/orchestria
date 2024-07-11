# SPDX-FileCopyrightText: 2024-present Silvano Cerza <silvanocerza@gmail.com>
#
# SPDX-License-Identifier: BSD-3-Clause
import json
from pathlib import Path
from typing import Dict


class _Settings:
    """
    Manages the whole app settings.
    """

    def __init__(self, folder: Path):
        self.folder = folder
        if not self.folder.exists():
            self.folder.mkdir(parents=True)

        self._agents_path = folder / "agents"
        if not self._agents_path.exists():
            self._agents_path.mkdir(parents=True)

        self._tools_path = folder / "tools"
        if not self._tools_path.exists():
            self._tools_path.mkdir(parents=True)

        # Global config files
        self._config = folder / "config.json"
        if not self._config.exists():
            self._config.write_text("{}")

    @property
    def registry(self) -> Dict[str, Dict[str, str]]:
        """
        Returns the registry of tools and agents.

        For the time being it's a simple dictionary containing:
        * `agents`: a dictionary where the key is the Agent name and the value is the local path.
        * `tools`: a dictionary where the key is the Tool source URL and the value is the local path.
        """
        data = json.loads(self._config.read_text())
        if "tools" not in data:
            data["tools"] = {}
        if "agents" not in data:
            data["agents"] = {}
        return data

    def register_tool(self, source_version: str, folder: str):
        """
        Saves a new toll in the register.
        """
        registry = self.registry
        registry["tools"][source_version] = folder
        self._config.write_text(json.dumps(registry))

    def register_agent(self, name: str, folder: str):
        """
        Saves a new agent in the register.
        """
        registry = self.registry
        registry["agents"][name] = folder
        self._config.write_text(json.dumps(registry))


# Dirty and ugly but does the job for the time being
# TODO: Handle this in a better way
SETTINGS = _Settings(Path.home() / ".orchestria")
