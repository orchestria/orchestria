# SPDX-FileCopyrightText: 2024-present Silvano Cerza <silvanocerza@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
import click
import rich
import rich.prompt

from orchestria.settings import SETTINGS


@click.group
def tool():
    pass


@click.option("--version")
@click.option("--name")
@click.command("delete")
def delete_tool(name: str = "", version: str = ""):
    while not name:
        tools = list(SETTINGS.registry["tools"].keys())
        name = rich.prompt.Prompt.ask("Tool to delete", choices=tools)

    while not version:
        versions = list(SETTINGS.registry["tools"][name].keys())
        version = rich.prompt.Prompt.ask("Version to delete", choices=versions)

    SETTINGS.delete_tool(name, version)
    rich.print(
        f"Tool [bold green]{name}[/] version [bold green]{version}[/] deleted successfully!"
    )


@click.command("list")
def list_tools():
    tools = SETTINGS.registry["tools"]
    if not tools:
        rich.print("No tools registered yet.")
        return
    rich.print_json(data=tools)


tool.add_command(delete_tool)
tool.add_command(list_tools)
