# OrchestrIA 🎻

---

Experimental Agents orchestrator from the command line.

> [!important]
> This project is in alpha, and is not even tested.
> Sweeping changes can come at any moment, don't rely on it.

## Installation

```console
pip install git+https://github.com/orchestria/orchestria.git
```

## Usage

### Agent creation

There are two different ways to get a new agent.

Either with the command line or with a properly configured git repo.

#### Command Line

A minimal agent can be created like so:

```bash
$ orchestria agent create \
  --name "My Agent" \
  --description "This is a general purpose Agent that doesn't support any tool" \
  --model "llama3.1" \
  --provider "ollama"
```

The `orchestria agent create` command accepts the following mandatory arguments:

- `--name`, agent name.
- `--description`, brief description of the agent. In the future this could also be used by agents to communicate with each other.
- `--model`, the model id to use, this depends on the provider.
- `--provider`, how to load the model. As of now only [`ollama`](https://ollama.com/) is supported.

The following are optional instead:

- `--system-prompt`, initial system prompt that will always be used when starting this agent.
- `--supported-tools`, list of tools supported by this agent. A tool can be specified in multiple ways:
  - Tool name, will use the latest version of the tool found locally
  - Tool git source, will fetch the latest version of the tool
  - `*` means it supports all tools that can be found locally
- `--generation-arguments`, additional generation arguments. Must be a JSON object.

#### Git repo

The root of the repository must contain a file named `.orchestria.yml`.
That file will tell OrchestrIA the available agents and its tools.

Read the [OrchestrIA config file](#orchestria-config-file) section for more details.

To get those configs just run `orchestria fetch`.

### Agent chatting

Starting a chat with an agent is simple:

```bash
$ orchestria agent start Smith
```

This will start the agent called `Smith` and you'll be able to chat with it.
To stop chatting just press Control+C.

Chat history is not saved as of now. I plan to add it in the future to restart previously interrupted discussions.

### Agent deletion

If you need to delete an existing local agent you can call:

```bash
$ orchestria agent delete Brown
```

This will completely delete agent `Brown` with no way of recovering.
If no agent name is provided it will list you all the local agents.

> [!note]
> As of now if the agent was fetched from a git repo together with other agents or tools
> they're going to be deleted too. Though they will still appear in the list of
> available tools.

## Tools

As of now only tools written in Python are supported. I plan to add support for Docker too.

Tools can't be created locally can only be fetched from a git repo with `orchestria fetch`.

An example of well defined tools can be found in [this repo](https://github.com/orchestria/filesystem/tree/main).

All Tools must be runnable as command line tools and expect a JSON string as input and must always return a JSON object if successful.

**Tools can prompt the user if necessary**.

> [!note]
> As of now if the tool was fetched from a git repo together with other tools or agents
> they're going to be deleted too. Though they will still appear in the list of
> available tools.

## OrchestrIA config file

The `.orchestria.yml` file can contain two fields:

- `agents`, a list of Agents definitions
- `tools`, a list of Tools defintions

Both fields are optional, it's ok for a config to define only Agents or only Tools.

An Agent definition is as follow:

- `name`, name of this Agent, this will be used to start chatting. I recommend not to use spaces
- `description`, brief description of this Agent, what it can or cannot do. The Agent doesn't receive this information
- `model`, id of model, this depends on the provider used
- `provider`, provider of the model, as of now only Ollama and Anthropic are supported
- `system_prompt`, system prompt that will be used for every chat with the model
- `generation-arguments`, extra generation arguments like `temperature` and similar, depends on the `provider` used
- `supported_tools`, list of names of supported Tools. Use `["*"]` to let the Agent use all locally available Tools

A good Agent definition could look like this:

```yaml
- name: Bond
  description: This Agent acts like James Bond
  model: llama3.1
  provider: ollama
  system_prompt: You are James Bond, talk like he would
  supported_tools: []
```

A Tool definition is as follow:

- `name`, Tool name, this used to let the Agent know which tools are available. I recommend not using spaces, some model providers limit the tool's name.
- `description`, detailed description of this Tool, this is extremely for the Agent to know what this Tool can be used for
- `language`, language of this Tool, as of now only `python` is supported.
- `entrypoint`, the entrypoint of this tool, usually the main file. This is used by OrchestrIA to run the Tool when necessary.
- `inputs_schema`, schema of the inputs for this tools

A good Tool definition could look like this:

```yml
- name: Remove
  description: Remove files
  language: python
  entrypoint: remove_files.py
  inputs_schema:
    type: object
    properties:
      files:
        description: File paths to delete
        type: array
        items:
          type: string
    required:
      - path
```

## License

`orchestria` is distributed under the terms of the [AGPL-3.0-or-later](https://spdx.org/licenses/AGPL-3.0-or-later.html) license.
