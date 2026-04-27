# CLI Agents

This project is a Python-based CLI application designed to facilitate various agent-related tasks. It includes modules for prompts, tools, utilities, and user interface interactions, making it a versatile solution for command-line interface needs.

## Features

- Modular design with separate components for easy maintenance.
- Supports customizable prompts and tools to enhance user experience.
- Utilities for common functionality that can be reused across different parts of the application.

## Initialization

Before running the application, ensure to set up the environment variables required for the OpenAI API. Create a `.env` file in the project root directory with the following content:

```
OPENAI_API_KEY=<your_openai_api_key>
OPENAI_BASE_URL=<your_openai_base_url>
```

Replace `<your_openai_api_key>` and `<your_openai_base_url>` with your actual OpenAI API key and base URL.

## Usage

To run the application, execute:

```bash
python cli_agents/main.py start
```

Once the application starts, you can input commands. The history can be reset at any time by typing `/reset`. The application utilizes asynchronous messaging and tool execution to provide a dynamic command-line interface experience.

## Contributing

Feel free to submit issues and pull requests to help improve the project.