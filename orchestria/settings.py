# SPDX-FileCopyrightText: 2024-present Silvano Cerza <silvanocerza@gmail.com>
#
# SPDX-License-Identifier: BSD-3-Clause
import json
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Dict

import dulwich
import dulwich.client
import dulwich.repo


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

    def _register_tool(self, source_version: str, folder: str):
        """
        Saves a new toll in the register.
        """
        registry = self.registry
        registry["tools"][source_version] = folder
        self._config.write_text(json.dumps(registry))

    def _register_agent(self, name: str, folder: str):
        """
        Saves a new agent in the register.
        """
        registry = self.registry
        registry["agents"][name] = folder
        self._config.write_text(json.dumps(registry))

    # TODO: Move the below methods somewhere else, this class should only handle settings.
    def store_agent(self, config: "Config"):
        """
        Stores an agent in the settings folder.
        """
        agent_path = self._agents_path / f"{config.name}.json"
        agent_path.write_text(json.dumps(asdict(config)))

        self._register_agent(config.name, str(agent_path))

    def clone_tool(self, source: str, version: str) -> Path:
        """
        Clones the tool from the source URL and returns the local path.
        """
        try:
            client, path = dulwich.client.get_transport_and_path(source)
        except ValueError as exc:
            raise ValueError("Invalid URL") from exc

        target_name = path.replace(".git", "") + f"_{version}"
        target_path = self._tools_path / target_name

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
        self._register_tool(f"{source}_{version}", str(target_path))
        return target_path


# Dirty and ugly but does the job for the time being
# TODO: Handle this in a better way
SETTINGS = _Settings(Path.home() / ".orchestria")
