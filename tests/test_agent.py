import tempfile
import unittest
from pathlib import Path
from content_agent.agent import Agent, MockModel
from content_agent.tools import Tools

ROOT = Path(__file__).resolve().parents[1]

class AgentTests(unittest.TestCase):
    def test_paths(self):
        for budget, expected, mode in [(20, 'completed', 'standard'), (10, 'completed', 'economy'), (2, 'incomplete', None)]:
            with tempfile.TemporaryDirectory() as directory:
                tools = Tools(ROOT, Path(directory) / 'plans.db')
                try:
                    result = Agent(tools, MockModel()).run({'request_id': 'r1', 'theme': '字幕', 'budget': budget, 'deadline': '2030-01-01T00:00:00+00:00'})
                    self.assertEqual(result['status'], expected)
                    if mode:
                        generated = [x['decision']['arguments']['mode'] for x in result['trace'] if x['decision']['action'] == 'generate_script']
                        self.assertEqual(generated, [mode])
                finally:
                    tools.close()

    def test_failure_preserves_success(self):
        with tempfile.TemporaryDirectory() as directory:
            tools = Tools(ROOT, Path(directory) / 'plans.db', ['generate_script_standard'])
            try:
                result = Agent(tools, MockModel()).run({'request_id': 'r1', 'theme': '字幕', 'budget': 20, 'deadline': '2030-01-01T00:00:00+00:00'})
                self.assertEqual(result['status'], 'incomplete')
                self.assertEqual(result['steps']['1']['status'], 'succeeded')
                self.assertEqual(result['steps']['3']['status'], 'failed')
            finally:
                tools.close()

class GuardTests(unittest.TestCase):
    def test_validation_duplicate_resume_and_deadline(self):
        from datetime import datetime, timezone
        with tempfile.TemporaryDirectory() as directory:
            tools = Tools(ROOT, Path(directory) / 'plans.db', ['generate_script_standard'])
            try:
                agent = Agent(tools, MockModel(), clock=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc))
                request = {'request_id': 'r1', 'theme': '字幕', 'budget': 20, 'deadline': '2030-01-01T00:00:00+00:00'}
                self.assertEqual(agent.run({})['status'], 'needs_input')
                first = agent.run(request)
                self.assertEqual(first['status'], 'incomplete')
                self.assertTrue(agent.run(request)['reused'])
                resumed = agent.run(request, resume=True)
                self.assertEqual(resumed['status'], 'completed')
                self.assertEqual(resumed['spent_cost'], 12)
                self.assertTrue(agent.run(request)['reused'])
                self.assertEqual(agent.run(dict(request, budget=99))['reason'], 'request_id_conflict')
                late = agent.run(dict(request, request_id='late', deadline='2025-01-01T00:00:00+00:00'))
                self.assertEqual(late['status'], 'incomplete')
                self.assertEqual(late['spent_cost'], 0)
                limited = Agent(tools, MockModel(), max_calls=1).run(dict(request, request_id='limited'))
                self.assertEqual(limited['status'], 'incomplete')
            finally:
                tools.close()

class AdversarialTests(unittest.TestCase):
    def test_untrusted_decisions_are_blocked(self):
        class Scripted:
            kind = 'test_fixture'
            def __init__(self, action, arguments):
                self.action, self.arguments = action, arguments
            def decide(self, context):
                return {'action': self.action, 'arguments': self.arguments, 'reason': 'test'}
        for action, args, budget in [
            ('finish', {'status': 'completed', 'reason': 'claim'}, 20),
            ('generate_script', {'material_ids': ['M01']}, 20),
            ('save_plan', {'request_id': 'r', 'plan': {'invented': True}}, 20),
            ('search_materials', {'query': '字幕'}, 0)]:
            with tempfile.TemporaryDirectory() as directory:
                tools = Tools(ROOT, Path(directory) / 'db')
                try:
                    result = Agent(tools, Scripted(action, args), max_calls=2).run({'request_id': 'r', 'theme': '字幕', 'budget': budget, 'deadline': '2030-01-01T00:00:00+00:00'})
                    self.assertNotEqual(result['status'], 'completed')
                    self.assertEqual(result['spent_cost'], 0)
                    self.assertEqual(tools.db.execute('SELECT COUNT(*) FROM plans').fetchone()[0], 0)
                finally:
                    tools.close()

class RecoveryTests(unittest.TestCase):
    def test_multiple_resumes_retain_charges(self):
        with tempfile.TemporaryDirectory() as directory:
            tools = Tools(ROOT, Path(directory)/'db', ['generate_script_standard'])
            try:
                agent = Agent(tools, MockModel())
                request = {'request_id':'repeat', 'theme':'字幕', 'budget':20, 'deadline':'2030-01-01T00:00:00+00:00'}
                self.assertEqual(agent.run(request)['spent_cost'], 1)
                tools.fail_once.add('generate_script_standard')
                self.assertEqual(agent.run(request, resume=True)['spent_cost'], 1)
                result = agent.run(request, resume=True)
                self.assertEqual(result['status'], 'completed')
                self.assertEqual(result['spent_cost'], 12)
            finally:
                tools.close()

    def test_interrupted_transaction_rolls_back(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory)/'db'
            tools = Tools(ROOT, database)
            agent = Agent(tools, MockModel())
            request = {'request_id':'interrupt', 'theme':'字幕', 'budget':20, 'deadline':'2030-01-01T00:00:00+00:00'}
            original = tools.save_plan
            def interrupt(**kwargs):
                original(**kwargs)
                raise KeyboardInterrupt()
            try:
                with patch.object(tools, 'save_plan', side_effect=interrupt):
                    with self.assertRaises(KeyboardInterrupt):
                        agent.run(request)
            finally:
                tools.close()
            tools = Tools(ROOT, database)
            try:
                self.assertEqual(tools.db.execute('SELECT COUNT(*) FROM plans').fetchone()[0], 0)
                self.assertEqual(Agent(tools, MockModel()).run(request)['status'], 'completed')
            finally:
                tools.close()
