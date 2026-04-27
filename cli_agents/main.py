import os
import typer
import anyio
from pathlib import Path
from dotenv import load_dotenv

from cli_agents.ui import trust_folder_ui, event_loop_async
from cli_agents.prompt import generate_system_prompt
from cli_agents.chat import ChatAgent

app = typer.Typer(add_completion=False, help="CLI Agent powered by OpenAI")

# ── CONFIG ───────────────────────────────────────────────────────────────
DEFAULT_MODEL = "openai/gpt-4o-mini"


def load_env():
    possible_paths = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]

    for path in possible_paths:
        if path.exists():
            load_dotenv(path)
            print(f"✅ Loaded .env from: {path}")
            return

    print("⚠️ No .env file found. Using system environment variables.")


# ── CLI COMMAND ──────────────────────────────────────────────────────────
@app.command()
def start():
    """Start CLI Agent"""
    trust_folder_ui()
    load_env()

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")

    if not api_key:
        typer.echo("\n❌ OPENAI_API_KEY not found.\n")
        typer.echo("👉 Fix it using ONE of these:\n")
        typer.echo("1. Create a .env file in the project root:")
        typer.echo("   OPENAI_API_KEY=your-key")
        typer.echo("2. Or set it globally on Windows CMD:")
        typer.echo("   setx OPENAI_API_KEY your-key")
        typer.echo("   restart the terminal after using setx")
        raise typer.Exit(1)

    try:
        from openai import AsyncOpenAI
    except ImportError:
        typer.echo("\n❌ Missing dependency: openai\n")
        typer.echo("👉 Install with: pip install openai\n")
        raise typer.Exit(1)

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url or None,
    )

    model = os.getenv("MODEL", DEFAULT_MODEL)

    agent = ChatAgent(
        client=client,
        system_prompt=generate_system_prompt(),
        model=model,
    )

    async def on_message(user_input: str):
        async for chunk in agent.handle_message(user_input):
            yield chunk

    anyio.run(event_loop_async, on_message, agent)


# ── ENTRY POINT ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    app()