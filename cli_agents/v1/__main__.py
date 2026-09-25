import os
from pathlib import Path
import anyio
import typer

from openai import AsyncOpenAI
from cli_agents.v1.config.loader import load_config
from cli_agents.config.global_config import set_config
from cli_agents.core import generate_system_prompt
from cli_agents.memory import ConversationMemory
from cli_agents.ui import render_error, trust_folder_ui
from cli_agents.v1.ui.app import V1App
from cli_agents.v1.core.v1_controller import V1AIController

app = typer.Typer()

@app.command()
def start(
    path: Path = typer.Argument(
        default=None,
        help="Project root directory (defaults to current directory)",
    ),
):
    project_root = (path or Path(os.getcwd())).resolve()
    trust_folder_ui()

    try:
        v1_config = load_config()
        set_config(v1_config.config)

        # Main System 2 Client
        system2_client = AsyncOpenAI(
            api_key=v1_config.config.openai_api_key,
            base_url=v1_config.config.openai_base_url,
        )

        memory = ConversationMemory(system_prompt=generate_system_prompt(v1_config.config))
        
        # Use the Unified V1AIController
        agent = V1AIController(system2_client, v1_config.config, memory)
        
        # Use the new V1App for orchestration and rendering
        v1_app = V1App(agent)

        anyio.run(v1_app.run)
    except KeyboardInterrupt:
        render_error(KeyboardInterrupt(), context="User Interrupt")
        raise typer.Exit(code=0)
    except Exception as error:
        render_error(error, context="Startup")
        raise typer.Exit(code=1) from None

def main():
    app()

if __name__ == "__main__":
    main()
