# SPDX-FileCopyrightText: 2024-present Silvano Cerza <silvanocerza@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import os
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
        generation_arguments: Dict[str, Any] | None,
        secrets: List[str] | Dict[str, str] | None = None,
    ):
        self._name = name
        self._description = description
        self._model = model
        self._provider = provider
        self._system_prompt = system_prompt or ""
        self._generation_kwargs = generation_arguments or {}

        if secrets is None:
            secrets = {}
        elif isinstance(secrets, list):
            secrets = {s: os.environ[s] for s in secrets}
        self._secrets = secrets

        # TODO: This should be part of the Agent manifest maybe, otherwise it's not very flexible
        # to use different system prompts tailored for a specific model
        self._tool_regex = re.compile(r"([a-zA-Z0-9_-]*)\[(.*)\]$", re.MULTILINE)

        self._supported_tools: List[Tool] = []
        if supported_tools:
            self._load_tools(supported_tools)

        if provider == "ollama":
            from ollama import AsyncClient, Options

            self._client = AsyncClient()
            # TODO: This should probably be gnerator kwargs
            self._options = Options()
        elif provider == "anthropic":
            from anthropic import AsyncAnthropic

            self._client = AsyncAnthropic(api_key=self._secrets["ANTHROPIC_API_KEY"])
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
            secrets=config.secrets,
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
        if self._provider == "ollama":
            return await self._start_ollama_chat_with_tools()
        elif self._provider == "anthropic":
            return await self._start_anthropic_chat()
        else:
            raise NotImplementedError(f"{self._provider} is not supported as of now")

    async def _start_ollama_chat_with_tools(self):
        console = Console()
        messages = []
        if self._system_prompt:
            rendered = jinja2.Template(self._system_prompt).render(
                tools=self._supported_tools
            )
            messages.append({"role": "system", "content": rendered})
        tools = []
        for tool in self._supported_tools:
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.inputs_schema,
                    },
                }
            )
        while True:
            with console.status("", spinner="point") as status:
                status.stop()

                if not messages or messages[-1]["role"] not in ["user", "tool"]:
                    # The user wasn't the last to write, we need to prompt the user.
                    # We need this check in case there's at least a tool call, if there's been that
                    # counts as the user writing.
                    user_prompt = console.input(prompt="[red bold]>>>[/] ")
                    messages.append({"role": "user", "content": user_prompt})

                status.start()
                args = {
                    "messages": messages,
                    "model": self._model,
                    "tools": tools,
                    # "stream": True,
                    "options": self._options,
                }
                res = await self._client.chat(**args)
                console.print(res)
                # async for part in await self._client.chat(**args):
                #     status.stop()
                # if text := part.get("message", {}).get("content", ""):
                #     console.print(text, end="")
                # else:
                #     console.print(part)

                # if part.get("done", False):
                #     break

                assert False
                # async with self._client.chat(**args) as stream:
                #     text = None
                #     tool_uses = []
                #     async for event in stream:
                #         if event.type == "text":
                #             status.stop()
                #             # We just print the token received
                #             console.print(event.text, end="")

                #         if event.type == "content_block_stop":
                #             if isinstance(event.content_block, TextBlock):
                #                 # This is the full text of the message.
                #                 # This can be present even if we have tool uses, as it shows the model chain of thought
                #                 text = event.content_block.text
                #             elif isinstance(event.content_block, ToolUseBlock):
                #                 # We can have multiple tool calls in a single message
                #                 tool_uses.append(event.content_block)
                #     if text:
                #         # If there was some text let's print a new line to keep the conversation clean
                #         console.print()

                #     if text and not tool_uses:
                #         # We only have text, not tool to call, keep the payload small
                #         messages.append({"role": "assistant", "content": text})
                #     elif tool_uses:
                #         status.start()
                #         # We have tools to call, we need to build a more complex message
                #         message = {
                #             "role": "assistant",
                #             "content": [],
                #         }

                #         if text:
                #             # We have some text too, probably the chain of thought
                #             message["content"].append({"type": "text", "text": text})

                #         for tool in tool_uses:
                #             # This is the definition of the tool call
                #             message["content"].append(
                #                 {
                #                     "type": tool.type,
                #                     "id": tool.id,
                #                     "name": tool.name,
                #                     "input": tool.input,
                #                 }
                #             )
                #         messages.append(message)

                #     if tool_uses:
                #         status.stop()
                #         message = {"role": "user", "content": []}
                #         # Now we call the tools that we need to call
                #         for tool_use in tool_uses:
                #             tool = [
                #                 t
                #                 for t in self._supported_tools
                #                 if t.name == tool_use.name
                #             ][0]
                #             tool_result = {
                #                 "type": "tool_result",
                #                 "tool_use_id": tool_use.id,
                #             }
                #             try:
                #                 # Calling the tool
                #                 tool_outputs = await tool.run(tool_use.input)
                #                 tool_result["content"] = json.dumps(tool_outputs)
                #             except Exception as exc:
                #                 # Ouch, we failed to call the tool
                #                 tool_result["content"] = f"Something went wrong: {exc}"
                #                 tool_result["is_error"] = True
                #             message["content"].append(tool_result)
                #         messages.append(message)

    async def _start_ollama_chat(self):
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
                    if matches := self._tool_regex.match(messages[-1]["content"]):
                        tool_name, tool_inputs = matches.groups()
                        tool_name = tool_name.strip()
                        tool_inputs = tool_inputs.strip()
                        tool = [
                            t for t in self._supported_tools if t.name == tool_name
                        ][0]
                        try:
                            tool_outputs = await tool.run(json.loads(tool_inputs))
                            message = {
                                "role": "tool",
                                "content": f"{tool_outputs}",
                            }
                        except Exception as exc:
                            message = {
                                "role": "tool",
                                "content": f"Something went wrong: {exc}",
                            }
                        messages.append(message)
                        if message["role"] != "system":
                            # Tools already print their output, no need to print it again
                            console.print(message["content"], end="\n")
                    else:
                        user_prompt = console.input(prompt="[red bold]>>>[/] ")
                        messages.append({"role": "user", "content": user_prompt})
                else:
                    user_prompt = console.input(prompt="[red bold]>>>[/] ")
                    messages.append({"role": "user", "content": user_prompt})

                status.start()

                assistant_response = {"role": "assistant", "content": ""}
                async for part in await self._client.chat(
                    model=self._model,
                    messages=messages,
                    stream=True,
                    options=self._options,
                ):  # type: ignore
                    status.stop()
                    if part["message"]["content"]:
                        console.print(part["message"]["content"], end="")
                    assistant_response["content"] += part["message"]["content"]
                messages.append(assistant_response)

            console.print()

    async def _start_anthropic_chat(self):
        from anthropic.types import TextBlock, ToolUseBlock

        console = Console()
        messages = []
        tools = []
        for tool in self._supported_tools:
            tools.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputs_schema,
                }
            )
        while True:
            with console.status("", spinner="point") as status:
                status.stop()

                if not messages or messages[-1]["role"] != "user":
                    # The user wasn't the last to write, we need to prompt the user.
                    # We need this check in case there's at least a tool call, if there's been that
                    # counts as the user writing.
                    user_prompt = console.input(prompt="[red bold]>>>[/] ")
                    messages.append({"role": "user", "content": user_prompt})

                status.start()
                args = {
                    "system": self._system_prompt,
                    "messages": messages,
                    "model": self._model,
                    "tools": tools,
                    "max_tokens": 1024,
                    **self._generation_kwargs,
                }
                async with self._client.messages.stream(**args) as stream:
                    text = None
                    tool_uses = []
                    async for event in stream:
                        if event.type == "text":
                            status.stop()
                            # We just print the token received
                            console.print(event.text, end="")

                        if event.type == "content_block_stop":
                            if isinstance(event.content_block, TextBlock):
                                # This is the full text of the message.
                                # This can be present even if we have tool uses, as it shows the model chain of thought
                                text = event.content_block.text
                            elif isinstance(event.content_block, ToolUseBlock):
                                # We can have multiple tool calls in a single message
                                tool_uses.append(event.content_block)
                    if text:
                        # If there was some text let's print a new line to keep the conversation clean
                        console.print()

                    if text and not tool_uses:
                        # We only have text, not tool to call, keep the payload small
                        messages.append({"role": "assistant", "content": text})
                    elif tool_uses:
                        status.start()
                        # We have tools to call, we need to build a more complex message
                        message = {
                            "role": "assistant",
                            "content": [],
                        }

                        if text:
                            # We have some text too, probably the chain of thought
                            message["content"].append({"type": "text", "text": text})

                        for tool in tool_uses:
                            # This is the definition of the tool call
                            message["content"].append(
                                {
                                    "type": tool.type,
                                    "id": tool.id,
                                    "name": tool.name,
                                    "input": tool.input,
                                }
                            )
                        messages.append(message)

                    if tool_uses:
                        status.stop()
                        message = {"role": "user", "content": []}
                        # Now we call the tools that we need to call
                        for tool_use in tool_uses:
                            tool = [
                                t
                                for t in self._supported_tools
                                if t.name == tool_use.name
                            ][0]
                            tool_result = {
                                "type": "tool_result",
                                "tool_use_id": tool_use.id,
                            }
                            try:
                                # Calling the tool
                                tool_outputs = await tool.run(tool_use.input)
                                tool_result["content"] = json.dumps(tool_outputs)
                            except Exception as exc:
                                # Ouch, we failed to call the tool
                                tool_result["content"] = f"Something went wrong: {exc}"
                                tool_result["is_error"] = True
                            message["content"].append(tool_result)
                        messages.append(message)
