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

    agent_file = SETTINGS.get_agent_path(name)
    if not agent_file:
        rich.print(f"Agent [red bold]{name}[/] not found.")
        return

    rich.print(f"Starting agent [green bold]{name}[/]")

    async def _start():
        _agent = Agent.from_file(agent_file, name=name)
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
        # TODO: Rework this to prompt for tools in a nicer way.
        # We can either show the available local tools and let them choose those or
        # let them input the source and version manually.
        # It's important that we don't save the sources in the agent config, but names and versions,
        # so we need to clone the tools when creating the agent.
        # This might be a bit annoying.
        supported_tools = rich.prompt.Prompt.ask("Supported tools (comma separated)")
        supported_tools = supported_tools.split(",") if supported_tools else []
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


@click.option("--version")
@click.option("--name")
@click.command("delete")
def delete_agent(name: str = "", version: str = ""):
    while not name:
        agents = list(SETTINGS.registry["agents"].keys())
        name = rich.prompt.Prompt.ask("Agent to delete", choices=agents)
    while not version:
        versions = list(SETTINGS.registry["agents"][name].keys())
        version = rich.prompt.Prompt.ask("Version to delete", choices=versions)

    SETTINGS.delete_agent(name, version)
    rich.print(
        f"Agent [bold green]{name}[/] version [bold green]{version}[/] deleted successfully!"
    )


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
