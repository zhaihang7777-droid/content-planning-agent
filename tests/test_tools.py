import tempfile
import unittest
from pathlib import Path
from content_agent.tools import Tools
from content_agent.state import ExecutionState, Step

ROOT = Path(__file__).resolve().parents[1]


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tools = Tools(ROOT, Path(self.tmp.name) / 'plans.db')

    def tearDown(self):
        self.tools.close()
        self.tmp.cleanup()

    def test_estimates(self):
        for mode, total in [('standard', 12), ('economy', 8)]:
            result = self.tools.estimate_plan(['search_materials', 'generate_script_' + mode, 'save_plan'])
            self.assertEqual(result.data['total_cost'], total)
        self.assertEqual(self.tools.estimate_plan(['save_plan'], 7).data['total_cost'], 8)

    def test_material_sources(self):
        self.assertEqual(len(self.tools.search_materials('字幕').data['materials']), 2)
        self.assertEqual(self.tools.search_materials('不存在').data['materials'], [])
        self.assertFalse(self.tools.generate_script(['unknown']).ok)
        self.assertTrue(all(s['source_id'] == 'M01' for s in self.tools.generate_script(['M01']).data['scenes']))

    def test_save_persistence_duplicate_and_conflict(self):
        self.assertTrue(self.tools.save_plan('r1', {'script': 'a'}).ok)
        self.tools.close()
        self.tools = Tools(ROOT, Path(self.tmp.name) / 'plans.db')
        duplicate = self.tools.save_plan('r1', {'script': 'a'})
        self.assertTrue(duplicate.reused)
        self.assertEqual(duplicate.cost, 0)
        self.assertEqual(self.tools.save_plan('r1', {'script': 'b'}).error, 'request_id_conflict')

    def test_save_failure_no_record(self):
        self.tools.fail_once.add('save_plan')
        self.assertFalse(self.tools.save_plan('r1', {'x': 1}).ok)
        self.assertFalse(self.tools.save_plan('r1', {'x': 1}).reused)

    def test_dependency_failure_and_resume(self):
        state = ExecutionState({'search': Step('search'), 'script': Step('script', ['search'])})
        with self.assertRaises(ValueError):
            state.start('script')
        state.start('search')
        state.finish('search', self.tools.search_materials('字幕'))
        self.tools.fail_once.add('generate_script_standard')
        state.start('script')
        state.finish('script', self.tools.generate_script(['M01']))
        self.assertEqual(state.steps['search'].status, 'succeeded')
        self.assertEqual(state.steps['script'].status, 'failed')
        state.start('script')
        state.finish('script', self.tools.generate_script(['M01']))
        self.assertEqual(state.spent_cost, 11)
        with self.assertRaises(ValueError):
            state.finish('script', self.tools.generate_script(['M01']))
