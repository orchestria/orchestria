# SPDX-FileCopyrightText: 2024-present Silvano Cerza <silvanocerza@gmail.com>
#
# SPDX-License-Identifier: BSD-3-Clause
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List

from orchestria.settings import SETTINGS


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
    system_prompt: str | None
    # The tools the Agent supports
    # This can be:
    # * Dict with the source of the tool and its version
    # * A List of strings with the tools sources, uses latest version
    # * A List of strings with the tools names, must have a version in the registry already, uses latest version
    # * A string with a * to support all tools in the registry
    # * None if the agent doesn't support any tool
    supported_tools: Dict[str, str] | List[str] | str | None
    # The arguments to pass to the model when generating text
    generation_arguments: Dict[str, Any]

    def store(self):
        """
        Stores an agent in the settings folder.
        """
        agent_path = SETTINGS._agents_path / f"{self.name}.json"
        agent_path.write_text(json.dumps(asdict(self)))

        SETTINGS.register_agent(self.name, str(agent_path))
