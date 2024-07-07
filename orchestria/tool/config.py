# SPDX-FileCopyrightText: 2024-present Silvano Cerza <silvanocerza@gmail.com>
#
# SPDX-License-Identifier: BSD-3-Clause

from dataclasses import dataclass
from typing import Dict


@dataclass
class Config:
    # Name of the tool
    name: str
    # Description of the tool, what it does or how it works
    description: str
    # The language the tool is written in.
    # For the time being this is limited to Python
    # Ideally this would be a list of languages.
    language: str
    # The source of the tool, usually a git repository
    source: str
    # The version of the tool, usually a git commit hash or tag
    version: str
    # The schema for the inputs of the tool
    inputs_schema: Dict[str, str]
    # The schema for the outputs of the tool
    outputs_schema: Dict[str, str]
