# SPDX-FileCopyrightText: 2024-present Silvano Cerza <silvanocerza@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
import re
from pathlib import Path
from typing import Any, Dict, List

import jinja2
import yaml
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
        supported_tools: List[Dict[str, str] | str] | None,
        generation_arguments: Dict[str, Any],
    ):
        self._name = name
        self._description = description
        self._model = model
        self._provider = provider
        self._system_prompt = system_prompt or ""
        self._generation_kwargs = generation_arguments

        # TODO: This should be part of the Agent manifest maybe, otherwise it's not very flexible
        # to use different system prompts tailored for a specific model
        self._tool_regex = re.compile(r"^(.*?)\[(.*)\]$", re.MULTILINE)

        self._supported_tools = []
        if supported_tools:
            self._load_tools(supported_tools)

        if provider == "ollama":
            from ollama import AsyncClient, Options

            self._client = AsyncClient()
            # TODO: This should probably be gnerator kwargs
            self._options = Options()
        else:
            raise NotImplementedError("{provider} is not supported as of now")

    def _load_tools(self, supported_tools: List[Dict[str, str] | str]):
        if "*" in supported_tools:
            # LOAD ALL THE TOOLS
            for name, path in SETTINGS.get_all_tools_path().items():
                self._supported_tools.append(Tool.from_file(Path(path), name=name))
            return

        for tool_data in supported_tools:
            if isinstance(tool_data, str):
                tool_path = SETTINGS.get_tool_path(tool_data)
                if not tool_path:
                    # At this point we should have already cloned the tool but it doesn't hurt to check
                    msg = f"Tool '{tool_data}' not found"
                    raise ValueError(msg)
                tool = Tool.from_file(Path(tool_path), name=tool_data)
            elif isinstance(tool_data, dict):
                name, version = list(tool_data.items())[0]
                tool_path = SETTINGS.get_tool_path(name, version)
                if not tool_path:
                    # At this point we should have already cloned the tool but it doesn't hurt to check
                    msg = f"Tool '{name}' not found"
                    raise ValueError(msg)
                tool = Tool.from_file(Path(tool_path))
            else:
                msg = "supported_tools must be a list of strings or a list of dictionaries"
                raise ValueError(msg)

            self._supported_tools.append(tool)

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
    def from_file(cls, path: Path, name: str = "") -> "Agent":
        """
        Load an agent from a yaml file.
        If there are multiple agents in the file and the name is not provided it will raise.
        """
        configs = yaml.safe_load(path.read_text(encoding="utf-8"))
        # This must be a dict
        assert isinstance(configs, dict)

        if "agents" not in configs:
            msg = f"No agents found in file '{path}'"
            raise ValueError(msg)

        configs = configs["agents"]

        if not isinstance(configs, list):
            msg = "Agents must be a list"
            raise ValueError(msg)

        if len(configs) > 1 and not name:
            msg = "Multiple agents in file, name must be provided"
            raise ValueError(msg)

        for c in configs:
            if c["name"] == name:
                return cls.from_config(Config(**c))

        msg = f"Agent '{name}' not found in file '{path}'"
        raise ValueError(msg)

    async def start_chat(self):
        console = Console()
        messages = []
        if self._system_prompt:
            rendered = jinja2.Template(self._system_prompt).render(
                tools=self._supported_tools
            )
            messages.append({"role": "system", "content": rendered})
        while True:
            with console.status("", spinner="point") as status:
                status.stop()
                if messages and messages[-1]["role"] == "assistant":
                    if matches := self._tool_regex.fullmatch(messages[-1]["content"]):
                        tool_name, tool_inputs = matches.groups()
                        tool = [
                            t for t in self._supported_tools if t.name == tool_name
                        ][0]
                        try:
                            tool_outputs = await tool.run(tool_inputs)
                            message = {
                                "role": "user",
                                "content": f"{tool_outputs}",
                            }
                        except Exception as exc:
                            # TODO: Find a nice way to handle exceptions
                            raise exc
                            message = {
                                "role": "assistant",
                                "content": f"Something went wrong: {exc}",
                            }
                        messages.append(message)
                        console.print(message["content"], end="\n")
                    else:
                        user_prompt = console.input(prompt="[red bold]>>>[/] ")
                        messages.append({"role": "user", "content": user_prompt})
                else:
                    user_prompt = console.input(prompt="[red bold]>>>[/] ")
                    messages.append({"role": "user", "content": user_prompt})

                status.start()

                assistant_response = {"role": "assistant", "content": ""}
                async for part in await self._chat(messages):  # type: ignore
                    status.stop()
                    if part["message"]["content"]:
                        console.print(part["message"]["content"], end="")
                    assistant_response["content"] += part["message"]["content"]
                messages.append(assistant_response)

            console.print()

    async def _chat(self, messages: List[Dict[str, str]]):
        if self._provider == "ollama":
            return self._chat_ollama(messages)
        else:
            raise NotImplementedError(f"{self._provider} is not supported as of now")

    async def _chat_ollama(self, messages: List[Dict[str, str]]):
        async for part in await self._client.chat(
            model=self._model,
            messages=messages,
            stream=True,
            options=self._options,
        ):
            yield part
