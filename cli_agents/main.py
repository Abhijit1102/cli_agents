import typer
import anyio

from cli_agents.config import load_env
from cli_agents.core import AIController, generate_system_prompt
from cli_agents.memory import ConversationMemory
from cli_agents.ui import ChatUI, trust_folder_ui

app = typer.Typer(add_completion=False, help="CLI Agent powered by OpenAI")



# ── CLI COMMAND ──────────────────────────────────────────────────────────
@app.command()
def start() -> None:
    """Start the enhanced CLI agent."""
    trust_folder_ui()
    config = load_env()

    try:
        from openai import AsyncOpenAI
    except ImportError:
        typer.echo("\n❌ Missing dependency: openai\n")
        typer.echo("👉 Install with: pip install openai\n")
        raise typer.Exit(1)

    client = AsyncOpenAI(
        api_key=config.openai_api_key,
        base_url=config.openai_base_url,
    )

    memory = ConversationMemory(system_prompt=generate_system_prompt(config.project_root))
    agent = AIController(client=client, config=config, memory=memory)
    ui = ChatUI(agent=agent)

    anyio.run(ui.run)



# ── ENTRY POINT ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    app()