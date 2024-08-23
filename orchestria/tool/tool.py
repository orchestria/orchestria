# SPDX-FileCopyrightText: 2024-present Silvano Cerza <silvanocerza@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

from orchestria.settings import SETTINGS
from orchestria.tool.config import Config


class Tool:
    def __init__(
        self,
        name: str,
        description: str | None,
        language: str,
        entrypoint: str,
        version: str,
        inputs_schema: Dict[str, str],
        secrets: List[str] | Dict[str, str] | None = None,
    ):
        self.name = name
        self.description = description
        self._language = language
        self._entrypoint = entrypoint
        self._version = version
        self.inputs_schema = inputs_schema
        # TODO: Ugly, this should be passed as a parameter maybe.
        # Or maybe we should overhaul this SETTINGS thing cause I don't like it.
        if versions := SETTINGS.registry["tools"][name]:
            self._source_path = list(versions.values())[0]

        if isinstance(secrets, list):
            self._secrets = {}
            for s in secrets:
                try:
                    self._secrets[s] = os.environ[s]
                except KeyError as exc:
                    msg = f"Secret '{s}' needed by tool '{name}' not found"
                    raise ValueError(msg) from exc
        else:
            self._secrets = secrets

    @classmethod
    def from_config(cls, config: Config):
        return cls(
            name=config.name,
            description=config.description,
            language=config.language,
            entrypoint=config.entrypoint,
            version=config.version,
            inputs_schema=config.inputs_schema,
            secrets=config.secrets,
        )

    @classmethod
    def from_file(cls, path: Path, name: str = "") -> "Tool":
        """
        Load a tool from a yaml file.
        If there are multiple tools in the file and the name is not provided it will raise.
        """
        configs = yaml.safe_load(path.read_text(encoding="utf-8"))
        # This must be a dict
        assert isinstance(configs, dict)

        if "tools" not in configs:
            msg = f"No tools found in file '{path}'"
            raise ValueError(msg)

        configs = configs["tools"]

        if not isinstance(configs, list):
            msg = "Tools must be a list"
            raise ValueError(msg)

        if len(configs) > 1 and not name:
            msg = "Multiple tools in file, name must be provided"
            raise ValueError(msg)

        for c in configs:
            if c["name"] == name:
                # TODO: This is quite ugly, maybe we should pass the version as a parameter.
                # For the time being it's fine as Tool is always using the latest version in any case.
                return cls.from_config(Config(**c, version=""))

        msg = f"Tool '{name}' not found in file '{path}'"
        raise ValueError(msg)

    async def run(self, args: str) -> Dict[str, Any] | str:
        if self._language != "python":
            raise NotImplementedError("Only Python tools are supported as of now")

        # Some models are stupid and generate JSON with single quotes.
        args = re.sub(r"(?<!\\)'", '"', args)

        # We need to replace this or the shell will interpret them.
        args = args.replace("{", "{{").replace("}", "}}")

        # We use a custom data dir so that we don't pollute the user's environment with tons of venvs.
        # This way we can also delete the env easily when the user wants to delete a tool.
        command = ["hatch", "--data-dir", ".venv", "run", self._entrypoint, f"'{args}'"]
        return await self._run_command(command)

    async def _run_command(self, command: List[str]):
        """
        Run command asynchronously and return the JSON output as a dictionary.

        If a JSON is not returned it will raise a ValueError.

        If the command requires user input it will block until the user provides it.
        """
        secrets = self._secrets or {}
        process = await asyncio.create_subprocess_shell(
            " ".join(command),
            cwd=self._source_path,
            stdin=sys.stdin,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            shell=True,
            env={"FORCE_COLOR": "1", **subprocess.os.environ, **secrets},
        )

        queue = asyncio.queues.Queue()

        async def process_output():
            # Read 8 bytes at a time to avoid blocking.
            while text := await process.stdout.read(8):
                queue.put_nowait(text.decode("utf-8"))
            # Ugly way to signal the end of the output
            queue.put_nowait(None)

        async def print_output():
            full_output = ""
            while True:
                data = await queue.get()
                if data is None:
                    # Nothing else will be received here
                    break
                print(data, end="")
                full_output += data
                queue.task_done()
            lines = full_output.splitlines()
            return lines

        async with asyncio.taskgroups.TaskGroup() as group:
            group.create_task(process.wait())
            group.create_task(process_output())
            print_output_task = group.create_task(print_output())

        # Parse the last line backwards to find the JSON object
        last_line = (await print_output_task)[-1].strip()
        for i in range(len(last_line), -1, -1):
            chunk = last_line[i:]
            try:
                return json.loads(chunk)
            except json.JSONDecodeError:
                continue

        raise ValueError("No JSON object found in output")
