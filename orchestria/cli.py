# SPDX-FileCopyrightText: 2024-present Silvano Cerza <silvanocerza@gmail.com>
#
# SPDX-License-Identifier: BSD-3-Clause

import click

from orchestria.agent.cli import agent
from orchestria.tool.cli import tool


@click.group
def main():
    pass


main.add_command(agent)
main.add_command(tool)
