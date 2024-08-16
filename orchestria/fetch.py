# SPDX-FileCopyrightText: 2024-present Silvano Cerza <silvanocerza@gmail.com>
#
# SPDX-License-Identifier: BSD-3-Clause
import click
import rich
from orchestria.settings import SETTINGS

@click.command()
@click.option(
    "--source",
    required=True,
    prompt="Git URL",
    help="Git repository URL to fetch, this can be a local or remote URL",
)
@click.option(
    "--version",
    required=True,
    prompt="Version",
    help="Version of the repo to fetch, can be a commit hash, tag, or branch.",
)
def fetch(source: str, version: str):
    """
    Fetches a Git repository and stores it locally.
    The repository must contain a valid `.orchestria.yml` file, all the agents
    and tools defined in the file will be available locally.
    """
    # TODO: We need to handle name and versions conflicts when calling this command.
    # Probably not here but in other parts of the code.
    # Though we should ask the user if they want to overwrite the existing version.
    try:
        names = SETTINGS.clone(source, version)
    except ValueError as exc:
        rich.print(
            f"[bold red]Error[/] while fetching tool: [bold red]{exc}[/]",
        )
        return

    if names["agents"]:
        rich.print("The following agents have been cloned locally:")
        for name in names["agents"]:
            rich.print(f"[`bold]- {name}[/]")

    if names["tools"]:
        rich.print("The following tools have been cloned locally:")
        for name in names["tools"]:
            rich.print(f"[`bold]- {name}[/]")
