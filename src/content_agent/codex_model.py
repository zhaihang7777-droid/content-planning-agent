"""Decision provider using the officially installed Codex CLI and its login."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from .agent import SYSTEM


class CodexModel:
    kind = 'codex_subscription'

    def __init__(self):
        self.binary = shutil.which('codex')
        if not self.binary:
            raise ValueError('Install Codex CLI and run codex login first')

    def decide(self, context):
        with tempfile.TemporaryDirectory(prefix='content-agent-codex-') as directory:
            output = Path(directory) / 'decision.json'
            command = [self.binary, 'exec', '--ignore-user-config', '--ephemeral',
                       '--skip-git-repo-check', '--sandbox', 'read-only',
                       '--color', 'never', '--output-last-message', str(output), '-']
            if os.environ.get('CODEX_MODEL'):
                command[2:2] = ['--model', os.environ['CODEX_MODEL']]
            prompt = SYSTEM + '\nDo not use shell or other tools. Only return the requested JSON decision.\nContext:\n' + json.dumps(context, ensure_ascii=False)
            completed = subprocess.run(command, input=prompt, text=True, capture_output=True,
                                       cwd=directory, timeout=120)
            if completed.returncode != 0 or not output.exists():
                raise RuntimeError('Codex CLI failed; check codex login status and account availability')
            decision = json.loads(output.read_text())
            if not isinstance(decision, dict):
                raise ValueError('Codex decision must be an object')
            return decision
