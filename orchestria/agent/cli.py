# SPDX-FileCopyrightText: 2024-present Silvano Cerza <silvanocerza@gmail.com>
#
# SPDX-License-Identifier: BSD-3-Clause
import asyncio
import json
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
@click.argument("name", required=False)
def start(name: str = ""):
    while not name:
        agents = list(SETTINGS.registry["agents"].keys())
        if not agents:
            rich.print(
                "You need to create an agent with `orchestria agent create` first."
            )
            return
        if len(agents) == 1:
            # There's only one agent, no need to ask
            name = agents[0]
            break
        name = rich.prompt.Prompt.ask("Choose an agent", choices=agents)

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
    while not name:
        name = rich.prompt.Prompt.ask("Name")
    while not description:
        description = rich.prompt.Prompt.ask("Description")
    while not model:
        model = rich.prompt.Prompt.ask("Model")
    while not provider:
        provider = rich.prompt.Prompt.ask(
            "Model provider", choices=["ollama"], default="ollama"
        )
    if not system_prompt:
        system_prompt = rich.prompt.Prompt.ask("System prompt (single line)")
    if not supported_tools:
        supported_tools = rich.prompt.Prompt.ask("Supported tools (comma separated)")
        supported_tools = supported_tools.split(",")
    if not generation_arguments:
        generation_arguments = json.loads(
            rich.prompt.Prompt.ask("Generation arguments (JSON format)") or "{}"
        )

    agent_config = Config(
        name=name,
        description=description,
        model=model,
        provider=provider,
        system_prompt=system_prompt,
        supported_tools=supported_tools,
        generation_arguments=generation_arguments or {},
    )

    agent_config.store()

    rich.print(f"Agent [bold green]{name}[/] created successfully!")


@click.option("--name")
@click.command("delete")
def delete_agent(name: str = ""):
    while not name:
        agents = list(SETTINGS.registry["agents"].keys())
        name = rich.prompt.Prompt.ask("Model to delete", choices=agents)
    SETTINGS.delete_agent(name)
    rich.print(f"Agent [bold green]{name}[/] deleted successfully!")


@click.command("list")
def list_agents():
    agents = SETTINGS.registry["agents"]
    if not agents:
        rich.print("No agents registered yet.")
        return
    rich.print_json(data=agents)


agent.add_command(start)
agent.add_command(create)
agent.add_command(delete_agent)
agent.add_command(list_agents)
