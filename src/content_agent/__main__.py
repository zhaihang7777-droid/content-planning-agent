import argparse
import json
from pathlib import Path
from .agent import Agent, JsonModel, MockModel
from .tools import Tools

parser = argparse.ArgumentParser()
parser.add_argument('input', type=Path)
parser.add_argument('--provider', choices=['mock', 'model', 'codex', 'gemini', 'deepseek'], required=True)
parser.add_argument('--database', type=Path, default=Path('runtime/plans.db'))
parser.add_argument('--resume', action='store_true')
args = parser.parse_args()
tools = Tools(Path(__file__).resolve().parents[2], args.database)
try:
    if args.provider == 'deepseek':
        from .deepseek_model import DeepSeekModel
        provider = DeepSeekModel()
    elif args.provider == 'gemini':
        from .gemini_model import GeminiModel
        provider = GeminiModel()
    elif args.provider == 'codex':
        from .codex_model import CodexModel
        provider = CodexModel()
    else:
        provider = MockModel() if args.provider == 'mock' else JsonModel()
    print(json.dumps(Agent(tools, provider).run(json.loads(args.input.read_text()), resume=args.resume), ensure_ascii=False, indent=2))
finally:
    tools.close()
