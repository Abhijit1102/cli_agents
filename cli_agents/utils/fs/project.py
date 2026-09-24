import os
from pathlib import Path
from openai import AsyncOpenAI
from .ignore import should_ignore
from .tree import build_tree

async def generate_project_description(
    project_root: Path,
    client: AsyncOpenAI,
    model: str,
) -> Path:
    output_dir = project_root / ".cli_agents"
    output_path = output_dir / "PROJECT_DESCRIPTION.md"
    output_dir.mkdir(parents=True, exist_ok=True)

    file_chunks: list[str] = []
    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if not should_ignore(d, is_dir=True)]
        for fname in sorted(files):
            if should_ignore(fname, is_dir=False):
                continue
            abs_path = Path(root) / fname
            rel_path = abs_path.relative_to(project_root)
            try:
                content = abs_path.read_text(encoding="utf-8", errors="replace")
            except (OSError, PermissionError):
                continue
            if len(content) > 200_000:
                file_chunks.append(f"### {rel_path}\n*(file too large – skipped)*\n")
                continue
            file_chunks.append(f"### {rel_path}\n```\n{content}\n```\n")

    tree_lines = build_tree(project_root, include_summaries=True)
    tree_str = project_root.name + "/"
    if tree_lines:
        tree_str += "\n" + "\n".join(tree_lines)

    user_message = (
        f"Project tree (with symbols):\n```\n{tree_str}\n```\n\n"
        "File contents:\n\n" + "\n".join(file_chunks) + "\n\n---\n"
        "Write a thorough PROJECT_DESCRIPTION.md for this codebase.\n"
        "Cover: purpose, architecture, module breakdown, key classes/functions,\n"
        "data-flow, configuration, and how to run / extend the project."
    )

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a senior software engineer. Output only valid Markdown."},
            {"role": "user", "content": user_message},
        ],
        max_tokens=4096,
    )
    description_md = response.choices[0].message.content.strip()
    output_path.write_text(description_md, encoding="utf-8")
    return output_path
