"""Gemini generateContent adapter, including explicitly configured gateways."""
import json
import os
from pathlib import Path
import urllib.request
from urllib.parse import urlparse, quote
from .agent import SYSTEM


class GeminiModel:
    kind = 'gemini_gateway'

    def __init__(self):
        config_path = Path(os.environ.get('GEMINI_CONFIG_FILE', str(Path.home() / '.config/content-planning-agent/gemini.json')))
        config = json.loads(config_path.read_text()) if config_path.exists() else {}
        self.base = os.environ.get('GEMINI_BASE_URL', config.get('base_url', '')).rstrip('/')
        self.key = os.environ.get('GEMINI_API_KEY', config.get('api_key', ''))
        self.model = os.environ.get('GEMINI_MODEL', config.get('model', 'gemini-2.5-flash'))
        if urlparse(self.base).scheme != 'https' or not self.key:
            raise ValueError('Configure HTTPS GEMINI_BASE_URL and GEMINI_API_KEY')

    def decide(self, context):
        body = {'systemInstruction': {'parts': [{'text': SYSTEM}]},
                'contents': [{'role': 'user', 'parts': [{'text': json.dumps(context, ensure_ascii=False)}]}],
                'generationConfig': {'responseMimeType': 'application/json', 'thinkingConfig': {'thinkingBudget': 0}}}
        req = urllib.request.Request(self.base + '/models/' + quote(self.model, safe='') + ':generateContent',
            data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', 'x-goog-api-key': self.key, 'User-Agent': 'content-planning-agent/0.1'})
        with urllib.request.urlopen(req, timeout=int(os.environ.get('GEMINI_TIMEOUT_SECONDS', '180'))) as response:
            payload = json.load(response)
        candidate = payload.get('candidates', [{}])[0]
        if candidate.get('finishReason') != 'STOP':
            raise ValueError('Gemini response incomplete or blocked')
        text = ''.join(p.get('text', '') for p in candidate.get('content', {}).get('parts', []) if not p.get('thought'))
        text = text.strip()
        if text.startswith('```') and text.endswith('```'):
            text = text.split('\n', 1)[1].rsplit('```', 1)[0].strip()
        decision = json.loads(text)
        if not isinstance(decision, dict):
            raise ValueError('Gemini decision must be an object')
        return decision
