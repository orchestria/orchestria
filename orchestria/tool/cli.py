# SPDX-FileCopyrightText: 2024-present Silvano Cerza <silvanocerza@gmail.com>
#
# SPDX-License-Identifier: BSD-3-Clause
import click
import rich

from orchestria.settings import SETTINGS

from .tool import Tool


@click.group
def tool():
    pass


@click.command
@click.option(
    "--source",
    required=True,
    prompt="Git URL",
    help="Git repository URL of the tool to fetch, this can be a local or remote URL",
)
@click.option(
    "--version",
    required=True,
    prompt="Version",
    help="Version of the tool to fetch, can be a commit hash, tag, or branch.",
)
def fetch(source: str, version: str):
    _tool = Tool.load(source, version)

    rich.print(
        f"Tool [bold red]{_tool.name}[/] fetched successfully!",
    )


@click.command("list")
def list_tools():
    tools = SETTINGS.registry["tools"]
    if not tools:
        rich.print("No tools registered yet.")
        return
    rich.print_json(data=tools)


tool.add_command(fetch)
tool.add_command(list_tools)
