# SPDX-FileCopyrightText: 2024-present Silvano Cerza <silvanocerza@gmail.com>
#
# SPDX-License-Identifier: BSD-3-Clause
import json
from pathlib import Path
from typing import Any, Dict, List

import jinja2
from rich.console import Console

from orchestria.settings import SETTINGS
from orchestria.tool import Tool

from .config import Config


class Agent:
    def __init__(
        self,
        name: str,
        description: str | None,
        model: str,
        provider: str,
        system_prompt: str | None,
        supported_tools: Dict[str, str] | List[str] | str | None,
        generation_arguments: Dict[str, Any],
    ):
        self._name = name
        self._description = description
        self._model = model
        self._provider = provider
        self._system_prompt = system_prompt or ""
        self._generation_kwargs = generation_arguments

        if supported_tools == "*":
            # TODO: Load all tools
            self._supported_tools = []
        elif isinstance(supported_tools, dict):
            self._supported_tools = [
                Tool.load(source=source, version=version)
                for source, version in supported_tools.items()
            ]
        elif isinstance(supported_tools, list):
            # TODO: This can't work as of now since we rely on the tool version to find its path.
            # We need to change it a bit.
            raise NotImplementedError
            # self._supported_tools = [
            #     SETTINGS.load_tool(source=tool) for tool in supported_tools
            # ]
        else:
            self._supported_tools = []

        if provider == "ollama":
            from ollama import AsyncClient

            self._client = AsyncClient()
        else:
            raise NotImplementedError("Only Ollama is supported")

    @classmethod
    def from_config(cls, config: Config) -> "Agent":
        return cls(
            name=config.name,
            description=config.description,
            model=config.model,
            provider=config.provider,
            system_prompt=config.system_prompt,
            supported_tools=config.supported_tools,
            generation_arguments=config.generation_arguments,
        )

    @classmethod
    def load(cls, name: str) -> "Agent":
        agent_path = SETTINGS.registry["agents"].get(name)

        if not agent_path:
            raise ValueError(f"Agent {name} not found")
        else:
            agent_path = Path(agent_path)

        agent_config = json.loads(agent_path.read_text(encoding="utf-8"))
        return cls.from_config(Config(**agent_config))

    async def start_chat(self):
        console = Console()
        messages = []
        if self._system_prompt:
            rendered = jinja2.Template(self._system_prompt).render(
                tools=self._supported_tools
            )
            messages.append({"role": "system", "content": rendered})
        while True:
            user_prompt = console.input(prompt="[red bold]>>>[/] ")
            with console.status("", spinner="point") as status:
                status.start()
                messages.append({"role": "user", "content": user_prompt})
                assistant_response = {"role": "assistant", "content": ""}
                async for part in await self._client.chat(
                    model=self._model, messages=messages, stream=True
                ):
                    status.stop()
                    console.print(part["message"]["content"], end="")
                    assistant_response["content"] += part["message"]["content"]
                messages.append(assistant_response)

            console.print()
