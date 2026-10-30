"""DeepSeek Chat Completions decision adapter."""
import json
import os
from pathlib import Path
import urllib.request
from urllib.parse import urlparse
from .agent import SYSTEM


class DeepSeekModel:
    kind = 'deepseek_api'

    def __init__(self):
        path = Path(os.environ.get('DEEPSEEK_CONFIG_FILE', str(Path.home()/'.config/content-planning-agent/deepseek.json')))
        config = json.loads(path.read_text()) if path.exists() else {}
        self.base = os.environ.get('DEEPSEEK_BASE_URL', config.get('base_url', 'https://api.deepseek.com')).rstrip('/')
        self.model = os.environ.get('DEEPSEEK_MODEL', config.get('model', 'deepseek-flash'))
        self.key = os.environ.get('DEEPSEEK_API_KEY', config.get('api_key', ''))
        if not self.key or urlparse(self.base).scheme != 'https':
            raise ValueError('Configure DEEPSEEK_API_KEY and HTTPS base URL locally')

    def decide(self, context):
        body = {'model': self.model, 'messages': [{'role':'system','content':SYSTEM},
                {'role':'user','content':json.dumps(context,ensure_ascii=False)}],
                'response_format': {'type':'json_object'}, 'stream':False}
        request = urllib.request.Request(self.base+'/chat/completions', data=json.dumps(body).encode(),
            headers={'Authorization':'Bearer '+self.key,'Content-Type':'application/json','User-Agent':'content-planning-agent/0.1'})
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.load(response)
        choice = payload['choices'][0]
        if choice.get('finish_reason') != 'stop':
            raise ValueError('DeepSeek response incomplete')
        decision = json.loads(choice['message']['content'])
        if not isinstance(decision, dict):
            raise ValueError('Decision must be an object')
        return decision
