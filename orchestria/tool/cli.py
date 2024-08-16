# SPDX-FileCopyrightText: 2024-present Silvano Cerza <silvanocerza@gmail.com>
#
# SPDX-License-Identifier: BSD-3-Clause
import click
import rich
import rich.prompt

from orchestria.settings import SETTINGS


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
    # TODO: We need to handle versions conflicts when calling this command.
    # Probably not here but in other parts of the code.
    # Though we should ask the user if they want to overwrite the existing version.
    try:
        tools = SETTINGS.clone(source, version)
    except ValueError as exc:
        rich.print(
            f"[bold red]Error[/] while fetching tool: [bold red]{exc}[/]",
        )
        return

    rich.print("The following tools have been cloned locally:")
    for name in tools:
        rich.print(f"[bold]- {name}[/]")


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


tool.add_command(fetch)
tool.add_command(delete_tool)
tool.add_command(list_tools)
