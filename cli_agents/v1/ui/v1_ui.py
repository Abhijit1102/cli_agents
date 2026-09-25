from cli_agents.ui.app import ChatUI
from rich.text import Text
from rich.panel import Panel
from rich import box
from rich.table import Table
from rich.markdown import Markdown
from cli_agents.ui.theme import P
from cli_agents.ui.app import animated_timestamp
from cli_agents.v1.ui.system_renderers import SystemPathRenderer

class V1ChatUI(ChatUI):
    """
    Custom UI for V1 that supports rendering Rich objects 
    and dynamic system labeling using marker strings.
    """
    def __init__(self, agent):
        super().__init__(agent)
        self.current_system = "ASSISTANT"

    def _render_assistant(self, message: any) -> None:
        """
        Overridden render method to handle marker strings, Rich panels, 
        and dynamic system labeling.
        """
        # 1. Handle System Path Markers
        if isinstance(message, str) and message.startswith("\x00SYSTEM_PATH:"):
            path = message.split(":")[1]
            if path == "SIMPLE":
                self.current_system = "SYSTEM 1 ASSISTANT"
                self.console.print(SystemPathRenderer.render_system1())
            elif path == "COMPLEX":
                self.current_system = "SYSTEM 2 ASSISTANT"
                self.console.print(SystemPathRenderer.render_system2())
            return

        # 2. Handle Rich objects (fallback)
        if hasattr(message, "__rich__"):
            self.console.print(message)
            return

        # 3. Handle standard text responses
        # Sync with ChatUI: Use Markdown for content to support code blocks and formatting
        
        # Create the header row (Label | Timestamp)
        header = Table.grid(expand=True)
        header.add_column(ratio=1)
        header.add_column(justify="right")
        header.add_row(
            Text(self.current_system, style=f"bold {P()}"), 
            animated_timestamp()
        )
        
        # Create the body with Markdown
        body = Table.grid()
        body.add_column()
        body.add_row(
            Markdown(str(message), code_theme="monokai", inline_code_lexer="python")
        )
        
        # Combine header and body into a single grid
        combined = Table.grid(expand=True)
        combined.add_column()
        combined.add_row(header)
        combined.add_row(body)
        
        # Print the final panel
        self.console.print(Panel(
            combined,
            border_style=P(),
            box=box.ROUNDED,
            padding=(0, 1)
        ))
