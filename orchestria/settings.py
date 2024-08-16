# SPDX-FileCopyrightText: 2024-present Silvano Cerza <silvanocerza@gmail.com>
#
# SPDX-License-Identifier: BSD-3-Clause
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List

import yaml

import dulwich
import dulwich.client
import dulwich.repo

MANIFEST = ".orchestria.yml"


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
    def registry(self) -> Dict[str, Dict[str, Any]]:
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

    def get_agent_path(self, name: str) -> Path | None:
        """
        Returns the path of the agent with the given name.
        """
        if name not in self.registry["agents"]:
            return None
        return Path(self.registry["agents"][name])

    def get_tool_path(self, name: str, version: str = "") -> Path | None:
        """
        Returns the path of the tool with the given name and version.
        If no version is provided, the latest version is returned.
        """
        if name not in self.registry["tools"]:
            return None
        if version and version not in self.registry["tools"][name]:
            return None
        if not version:
            # TODO: Get the latest version checking semver
            return Path(self.registry["tools"][name].values()[0]) / MANIFEST
        return Path(self.registry["tools"][name][version]) / MANIFEST

    def get_all_tools_path(self) -> Dict[str, Path]:
        """
        Returns a dictionary with tool's name as key and the path to the manifest file as value.
        If multiple versions of the same tool are present, the latest one is returned.
        """
        paths = {}
        for name, versions in self.registry["tools"].items():
            path = list(versions.values())[0]
            paths[name] = Path(path) / MANIFEST
        return paths

    def clone(self, source: str, version: str) -> Dict[str, List[str]]:
        """
        Clone a repository.
        Returns dictionary with agent and tool names.
        Raises if the repository doesn't contain the OrchestrIA manifest.
        """
        try:
            client, path = dulwich.client.get_transport_and_path(source)
        except ValueError as exc:
            raise ValueError("Invalid URL") from exc

        target_path = self._tools_path / Path(path.replace(".git", "")) / version
        target_path.mkdir(parents=True, exist_ok=True)

        client.clone(
            path, target_path=target_path, branch=version.encode(), depth=1, mkdir=False
        )

        # Check the tool is valid.
        # We do this after cloning as it's easier to check the local files
        # rather than checking the remote repository. To check remote repositories we would need to
        # to parse the URL, check the service, know the service API to get the repo files, etc.
        # This works.
        manifest_path = target_path / MANIFEST
        if not (manifest_path).exists():
            shutil.rmtree(target_path)
            msg = f"Invalid tool repository, missing '{MANIFEST}'"
            raise ValueError(msg)

        with manifest_path.open() as p:
            manifest = yaml.safe_load(p)

        tool_configs = manifest["tools"]
        names = {"tools": [], "agents": []}
        if isinstance(tool_configs, list):
            for tool in tool_configs:
                names["tools"] = tool["name"]
                self.register_tool(tool["name"], version, target_path)
        else:
            msg = f"Invalid tool '{MANIFEST}' format"
            raise ValueError(msg)


        agent_configs = manifest["agents"]
        if isinstance(agent_configs, list):
            for agent in agent_configs:
                names["agents"] = agent["name"]
                self.register_agent(agent["name"], target_path)
        else:
            msg = f"Invalid agent '{MANIFEST}' format"
            raise ValueError(msg)

        return names

    def register_tool(self, tool_name: str, version: str, folder: str | Path):
        """
        Saves a new tool in the register for future retrieval.
        """
        registry = self.registry
        folder = str(folder)
        if tool_name not in registry["tools"]:
            registry["tools"][tool_name] = {version: folder}
        else:
            registry["tools"][tool_name][version] = folder
        self._config.write_text(json.dumps(registry))

    def register_agent(self, name: str, folder: str | Path):
        """
        Saves a new agent in the register.
        """
        registry = self.registry
        registry["agents"][name] = str(folder)
        self._config.write_text(json.dumps(registry))

    def delete_agent(self, name: str):
        """
        Deletes an agent from the registry.
        """
        if name not in self.registry["agents"]:
            return

        registry = self.registry
        agent = Path(registry["agents"].pop(name))
        self._config.write_text(json.dumps(registry))
        agent.unlink(missing_ok=True)

    def delete_tool(self, name: str, version: str):
        """
        Deletes a tool from the registry.
        """
        if name not in self.registry["tools"]:
            return
        if version not in self.registry["tools"][name]:
            return

        registry = self.registry
        tool_path = Path(registry["tools"][name].pop(version))
        if len(registry["tools"][name]) == 0:
            registry["tools"].pop(name)
        self._config.write_text(json.dumps(registry))
        # NOTE: We're delete the whole folder here, though there could be other tools that share the same folder.
        # We should find a better way to handle this. Let's keep it simple for now.
        shutil.rmtree(tool_path, ignore_errors=True)


# Dirty and ugly but does the job for the time being
# TODO: Handle this in a better way
SETTINGS = _Settings(Path.home() / ".orchestria")
