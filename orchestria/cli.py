# SPDX-FileCopyrightText: 2024-present Silvano Cerza <silvanocerza@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import click

from orchestria.agent.cli import agent
from orchestria.fetch import fetch
from orchestria.tool.cli import tool


@click.group
def main():
    pass


main.add_command(agent)
main.add_command(tool)
main.add_command(fetch)
