# SPDX-FileCopyrightText: 2024-present Silvano Cerza <silvanocerza@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
from dataclasses import asdict, dataclass
from typing import Any, Dict, List

import yaml

from orchestria.settings import MANIFEST, SETTINGS


@dataclass
class Config:
    # Name of the agent
    name: str
    # Description of the agent, usually what it can do or how it works
    description: str
    # The model the agent uses
    model: str
    # The provider of the model. e.g ollama, transformers, etc
    # Basically how the model is loaded.
    provider: str
    # The system prompt for the model, if any.
    # This can be a Jinja template.
    system_prompt: str | None = None
    # The tools the Agent supports
    # The list can contain::
    # * A Dict with the name of the tool and its version
    # * The name of a tool to support the latest version
    # * The string "*" to support all tools
    # If the list is empty or None, the agent doesn't support any tool
    supported_tools: List[Dict[str, str] | str] | None = None
    # The arguments to pass to the model when generating text
    generation_arguments: Dict[str, Any] | None = None
    # Secrets necessary for the agent to work, usually API keys
    secrets: List[str] | Dict[str, str] | None = None

    def store(self):
        """
        Stores an agent in the settings folder.
        """
        agent_path = SETTINGS._repos_path / "local" / self.name
        agent_path.mkdir(parents=True, exist_ok=True)
        manifest_path = agent_path / MANIFEST

        with manifest_path.open("w") as f:
            yaml.dump({"agents": [asdict(self)]}, f)

        SETTINGS.register_agent(self.name, "local", str(agent_path))
