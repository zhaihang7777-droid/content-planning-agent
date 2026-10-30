"""Reproduce offline evidence; uses a fixed clock and temporary databases."""
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from content_agent.agent import Agent, MockModel
from content_agent.tools import Tools

ROOT = Path(__file__).resolve().parents[1]

def main():
    summary = []
    cases = [('normal', 20, None), ('over_budget', 10, None), ('no_feasible_plan', 2, None),
             ('missing_budget', None, None), ('missing_deadline', 20, None),
             ('tool_failure', 20, 'generate_script_standard'), ('save_failure', 20, 'save_plan'),
             ('deadline', 20, None), ('call_limit', 20, None), ('duplicate', 20, None),
             ('resume', 20, 'generate_script_standard')]
    for name, budget, failure in cases:
        request = {'request_id': name, 'theme': '字幕', 'budget': budget, 'deadline': '2026-01-02T00:00:00+00:00'}
        if name == 'missing_deadline':
            del request['deadline']
        if name == 'deadline':
            request['deadline'] = '2025-12-31T00:00:00+00:00'
        with tempfile.TemporaryDirectory() as directory:
            tools = Tools(ROOT, Path(directory) / 'plans.db', [failure] if failure else [])
            try:
                agent = Agent(tools, MockModel(), max_calls=1 if name == 'call_limit' else 12,
                              clock=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc))
                outputs = [agent.run(request)]
                if name in ('duplicate', 'resume'):
                    outputs.append(agent.run(request, resume=name == 'resume'))
                count = tools.db.execute('SELECT COUNT(*) FROM plans').fetchone()[0]
                evidence = {'provider': 'offline_mock', 'clock': '2026-01-01T00:00:00+00:00',
                            'input': request, 'fail_once': failure, 'outputs': outputs, 'saved_plan_count': count}
                (ROOT / 'examples' / (name + '.json')).write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
                expected = 'completed' if name in ('normal', 'over_budget', 'duplicate', 'resume') else 'needs_input' if name.startswith('missing') else 'incomplete'
                assert outputs[-1]['status'] == expected, name
                assert count == (1 if expected == 'completed' else 0), name
                if name == 'duplicate':
                    assert outputs[-1]['reused']
                if name == 'resume':
                    assert outputs[-1]['spent_cost'] == 12
                summary.append({'case': name, 'expected': expected, 'actual': outputs[-1]['status'], 'passed': True})
            finally:
                tools.close()
    (ROOT / 'examples/summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(f'{len(summary)} offline scenarios passed')

if __name__ == '__main__':
    main()
