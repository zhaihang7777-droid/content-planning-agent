"""Local synthetic tools. Costs and durations are simulated, not real services."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from pathlib import Path
import hashlib
import json
import sqlite3


@dataclass
class ToolResult:
    ok: bool
    data: dict = field(default_factory=dict)
    error: str | None = None
    cost: int = 0
    duration_seconds: int = 0
    reused: bool = False

    def to_dict(self):
        return asdict(self)


class Tools:
    def __init__(self, root: Path, database: Path, fail_once=()):
        self.materials = json.loads((root / 'data/materials.json').read_text())
        self.catalog = json.loads((root / 'data/tool-catalog.json').read_text())['tools']
        self.fail_once = set(fail_once)
        database.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(database, isolation_level=None)
        self.db.execute('CREATE TABLE IF NOT EXISTS plans (request_id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        self.db.commit()

    def close(self):
        self.db.close()

    def _result(self, name, data):
        if name in self.fail_once:
            self.fail_once.remove(name)
            return ToolResult(False, error=f'injected_failure:{name}')
        return ToolResult(True, data, **self.catalog[name])

    def search_materials(self, query):
        if not isinstance(query, str) or not query.strip():
            return ToolResult(False, error='query_required')
        found = [m for m in self.materials if query.casefold() in json.dumps(m, ensure_ascii=False).casefold()]
        return self._result('search_materials', {'materials': found})

    def generate_script(self, material_ids, mode='standard'):
        if mode not in ('standard', 'economy'):
            return ToolResult(False, error='unknown_mode')
        selected = [m for m in self.materials if m['id'] in material_ids]
        if not selected or {m['id'] for m in selected} != set(material_ids):
            return ToolResult(False, error='unknown_or_missing_materials')
        # Explicit offline fixture: later model integration replaces this authoring path.
        scenes = [{'source_id': m['id'], 'text': fact} for m in selected for fact in m['facts']]
        return self._result('generate_script_' + mode, {'mode': mode, 'scenes': scenes, 'synthetic': True})

    def estimate_plan(self, operations, spent_cost=0):
        if type(spent_cost) is not int or spent_cost < 0 or any(op not in self.catalog for op in operations):
            return ToolResult(False, error='invalid_estimate_input')
        return self._result('estimate_plan', {
            'remaining_cost': sum(self.catalog[op]['cost'] for op in operations),
            'total_cost': spent_cost + sum(self.catalog[op]['cost'] for op in operations),
            'remaining_duration_seconds': sum(self.catalog[op]['duration_seconds'] for op in operations),
        })

    def save_plan(self, request_id, plan):
        if not isinstance(request_id, str) or not request_id.strip() or not isinstance(plan, dict) or not plan:
            return ToolResult(False, error='invalid_save_input')
        try:
            payload = json.dumps(plan, ensure_ascii=False, sort_keys=True, allow_nan=False)
            plan_id = hashlib.sha256(request_id.encode()).hexdigest()[:16]
            row = self.db.execute('SELECT payload FROM plans WHERE request_id=?', (request_id,)).fetchone()
            if row:
                if row[0] != payload:
                    return ToolResult(False, error='request_id_conflict')
                return ToolResult(True, {'plan_id': plan_id, 'plan': plan}, reused=True)
            result = self._result('save_plan', {'plan_id': plan_id, 'plan': plan})
            if result.ok:
                self.db.execute('INSERT INTO plans VALUES (?, ?)', (request_id, payload))
                # Agent owns the transaction; standalone calls may commit explicitly.
            return result
        except (sqlite3.Error, TypeError, ValueError) as exc:
            return ToolResult(False, error=f'save_failed:{type(exc).__name__}')
