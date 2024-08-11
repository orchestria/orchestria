# SPDX-FileCopyrightText: 2024-present Silvano Cerza <silvanocerza@gmail.com>
#
# SPDX-License-Identifier: BSD-3-Clause
import json
import re
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

        # TODO: This should be part of the Agent manifest maybe, otherwise it's not very flexible
        # to use different system prompts
        self._action_regex = re.compile(r"^Action: (.*)\[(.*)\]$", re.MULTILINE)
        self._final_answer_regex = re.compile(r"^Final Answer: (.*)$", re.MULTILINE)

        if supported_tools == ["*"]:
            self._supported_tools = []
            for k in SETTINGS.registry["tools"].keys():
                source, version = k.rsplit("_", 1)
                self._supported_tools.append(Tool.load(source=source, version=version))
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
            from ollama import AsyncClient, Options

            self._client = AsyncClient()
            # TODO: This should probably be gnerator kwargs
            self._options = Options(stop=["Question: ", "Observation: "])
        else:
            raise NotImplementedError("{provider} is not supported as of now")

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
    def from_file(cls, path: Path) -> "Agent":
        agent_config = json.loads(path.read_text(encoding="utf-8"))
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
            with console.status("", spinner="point") as status:
                status.stop()
                if (
                    messages
                    and messages[-1]["role"] == "assistant"
                    and not self._final_answer_regex.search(messages[-1]["content"])
                ):
                    if matches := list(
                        self._action_regex.finditer(messages[-1]["content"])
                    ):
                        tool_name, tool_inputs = matches[-1].groups()
                        tool = [
                            t for t in self._supported_tools if t.name == tool_name
                        ][0]
                        try:
                            tool_outputs = tool.run(tool_inputs)
                            message = {
                                "role": "assistant",
                                "content": f"Observation: {tool_outputs}",
                            }
                        except Exception as exc:
                            # TODO: Find a nice way to handle exceptions
                            # message = {
                            #     "role": "assistant",
                            #     "content": f"Something went wrong calling the tool: {exc.with_traceback()}",
                            # }
                            raise exc
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
