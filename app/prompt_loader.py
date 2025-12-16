import yaml
import os
from jinja2 import Template

class PromptManager:
    def __init__(self, file_path):
        self.prompts = self._load_yaml(file_path)

    def _load_yaml(self, file_path):
        base_dir = os.path.dirname(os.path.abspath(file_path))
        full_path = os.path.join(base_dir, 'prompts.yaml')
        
        with open(full_path, 'r') as f:
            return yaml.safe_load(f)

    def render(self, prompt_name, **kwargs):
        """
        Fetches the prompt string and renders it with Jinja2.
        """
        prompt_str = self.prompts.get(prompt_name)
        if not prompt_str:
            raise ValueError(f"Prompt '{prompt_name}' not found.")
            
        template = Template(prompt_str)
        return template.render(**kwargs)