import os
from pathlib import Path

import typer
import anyio

from cli_agents.config.global_config import set_config
from cli_agents.config import load_config
from cli_agents.core import AIController, generate_system_prompt
from cli_agents.memory import ConversationMemory
from cli_agents.ui import ChatUI, trust_folder_ui

app = typer.Typer()


@app.command()
def start(
    path: Path = typer.Argument(
        default=None,
        help="Project root directory (defaults to current directory)",
    )
):
    project_root = (path or Path(os.getcwd())).resolve()
    print(">>> CWD AT START:", project_root)

    trust_folder_ui()

    print(">>> CWD AFTER TRUST:", Path(os.getcwd()).resolve())

    config = load_config(project_root=project_root)
    set_config(config)

    print(">>> CONFIG ROOT:", config.project_root)

    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=config.openai_api_key,
        base_url=config.openai_base_url,
    )
    memory = ConversationMemory(
        system_prompt=generate_system_prompt(config)
    )

    agent = AIController(client, config, memory)
    ui = ChatUI(agent)

    # agent.initialize() + agent.shutdown() are now managed inside ui.run()
    anyio.run(ui.run)


if __name__ == "__main__":
    app()