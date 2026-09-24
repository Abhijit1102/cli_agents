from pathlib import Path
from cli_agents.config.settings import AppConfig
from cli_agents.core.prompt import generate_system_prompt

def test_generate_system_prompt():
    # Setup a mock config
    config = AppConfig(
        openai_api_key="test-key",
        openai_base_url=None,
        model="gpt-4o",
        project_root=Path.cwd(),
        project_instructions="This is a test project for prompt generation.",
        mcp_config_path=None,
        image_model=None
    )
    
    print("--- Generating System Prompt ---")
    prompt = generate_system_prompt(config)
    print(prompt)
    print("--- End of System Prompt ---")
    
    # Basic assertions
    assert "You are a CLI coding agent" in prompt
    assert "This is a test project for prompt generation." in prompt
    print("\n✅ Prompt generated successfully and contains expected sections.")

if __name__ == "__main__":
    test_generate_system_prompt()
