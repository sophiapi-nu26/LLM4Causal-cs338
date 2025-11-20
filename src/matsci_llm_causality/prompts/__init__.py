"""
Utility functions for loading prompts from text files.
"""

from pathlib import Path
from typing import Dict, Optional


def load_prompt(filename: str, **kwargs) -> str:
    """
    Load a prompt from a text file and optionally format it with parameters.
    
    Args:
        filename: Name of the prompt file (e.g., "text_relation_extraction.txt")
        **kwargs: Optional parameters for string formatting (e.g., text="...", entity_list="...")
        
    Returns:
        The prompt string, optionally formatted with the provided parameters
        
    Raises:
        FileNotFoundError: If the prompt file doesn't exist
    """
    # Get the directory where this file is located
    prompts_dir = Path(__file__).parent
    
    # Construct the full path to the prompt file
    prompt_path = prompts_dir / filename
    
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    
    # Read the prompt file
    with open(prompt_path, 'r', encoding='utf-8') as f:
        prompt = f.read()
    
    # Escape all braces, then re-enable placeholders for known keys.
    prompt = prompt.replace('{', '{{').replace('}', '}}')
    for key in kwargs:
        placeholder = '{{' + key + '}}'
        prompt = prompt.replace(placeholder, '{' + key + '}')

    if kwargs:
        try:
            prompt = prompt.format(**kwargs)
        except (KeyError, ValueError) as e:
            raise ValueError(
                f"Error formatting prompt '{filename}': {e}. "
                f"Make sure all placeholders in the prompt file match the provided parameters."
            ) from e
    
    return prompt

