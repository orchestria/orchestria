# SPDX-FileCopyrightText: 2024-present Silvano Cerza <silvanocerza@gmail.com>
#
# SPDX-License-Identifier: BSD-3-Clause
import asyncio
from typing import Any, Dict, List

import click
import rich
import rich.prompt

from orchestria.settings import SETTINGS

from .agent import Agent
from .config import Config


@click.group
def agent():
    pass


@click.command
@click.argument("name")
def start(name):
    rich.print(f"Starting agent [green bold]{name}[/]")

    async def _start():
        _agent = Agent.load(name)
        await _agent.start_chat()

    asyncio.run(_start())


@click.option("--generation-arguments")
@click.option("--supported-tools")
@click.option("--system-prompt")
@click.option("--provider")
@click.option("--model")
@click.option("--description")
@click.option("--name")
@click.command
def create(
    name: str = "",
    description: str = "",
    model: str = "",
    provider: str = "",
    system_prompt: str = "",
    supported_tools: Dict[str, str] | List[str] | str | None = None,
    generation_arguments: Dict[str, Any] | None = None,
):
    if not name:
        name = rich.prompt.Prompt.ask("Name")
    if not description:
        description = rich.prompt.Prompt.ask("Description")
    if not model:
        model = rich.prompt.Prompt.ask("Model")
    if not provider:
        provider = rich.prompt.Prompt.ask("Model provider", choices=["ollama"])
    if not system_prompt:
        system_prompt = rich.prompt.Prompt.ask("")

    agent_config = Config(
        name=name,
        description=description,
        model=model,
        provider=provider,
        system_prompt=system_prompt,
        supported_tools=supported_tools,
        generation_arguments=generation_arguments or {},
    )

    SETTINGS.store_agent(agent_config)

    rich.print(f"Agent [bold green]{name}[/] created successfully!")


@click.command("list")
def list_agents():
    agents = SETTINGS.registry["agents"]
    if not agents:
        rich.print("No agents registered yet.")
        return
    rich.print_json(data=agents)


agent.add_command(start)
agent.add_command(create)
agent.add_command(list_agents)
