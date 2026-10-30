import io
import json
import os
import unittest
from unittest.mock import patch
from content_agent.agent import JsonModel

class ResponsesTests(unittest.TestCase):
    def test_request_and_response_contract(self):
        decision = {'action': 'finish', 'arguments': {'status': 'incomplete', 'reason': 'test'}, 'reason': 'test'}
        payload = {'status': 'completed', 'output': [{'type': 'reasoning'}, {'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(decision)}]}]}
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-only', 'OPENAI_MODEL': 'test-model'}):
            with patch('urllib.request.urlopen', return_value=io.BytesIO(json.dumps(payload).encode())) as call:
                self.assertEqual(JsonModel().decide({'request': {}}), decision)
                req = call.call_args.args[0]
                self.assertEqual(req.full_url, 'https://api.openai.com/v1/responses')
                body = json.loads(req.data)
                self.assertFalse(body['store'])
                self.assertEqual(body['model'], 'test-model')
                self.assertNotIn('test-only', req.data.decode())

    def test_missing_config(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                JsonModel()

class GeminiTests(unittest.TestCase):
    def test_gateway_response_and_incomplete(self):
        from content_agent.gemini_model import GeminiModel
        env = {'GEMINI_BASE_URL': 'https://example.invalid/v1beta', 'GEMINI_API_KEY': 'test-only'}
        with patch.dict(os.environ, env):
            model = GeminiModel()
            response = {'candidates':[{'finishReason':'STOP', 'content':{'parts':[{'text':'```json\n{"action":"finish"}\n```'}]}}]}
            with patch('urllib.request.urlopen', return_value=io.BytesIO(json.dumps(response).encode())) as call:
                self.assertEqual(model.decide({})['action'], 'finish')
                self.assertEqual(call.call_args.args[0].get_header('User-agent'), 'content-planning-agent/0.1')
            with patch('urllib.request.urlopen', return_value=io.BytesIO(b'{"candidates":[{"finishReason":"MAX_TOKENS"}]}')):
                with self.assertRaises(ValueError):
                    model.decide({})

class DeepSeekTests(unittest.TestCase):
    def test_contract(self):
        from content_agent.deepseek_model import DeepSeekModel
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY':'test-only'}):
            response={'choices':[{'finish_reason':'stop','message':{'content':'{"action":"finish"}'}}]}
            with patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(response).encode())) as call:
                self.assertEqual(DeepSeekModel().decide({})['action'], 'finish')
                self.assertTrue(call.call_args.args[0].full_url.endswith('/chat/completions'))
