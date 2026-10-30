"""Execution state; dependencies and charges come from actual tool results."""
from __future__ import annotations
from dataclasses import dataclass, field
from .tools import ToolResult


@dataclass
class Step:
    id: str
    dependencies: list[str] = field(default_factory=list)
    status: str = 'pending'
    result: dict | None = None


@dataclass
class ExecutionState:
    steps: dict[str, Step] = field(default_factory=dict)
    spent_cost: int = 0
    simulated_elapsed_seconds: int = 0
    trace: list[dict] = field(default_factory=list)

    def start(self, step_id):
        step = self.steps[step_id]
        if step.status not in ('pending', 'failed'):
            raise ValueError('step_cannot_start')
        if any(self.steps[d].status != 'succeeded' for d in step.dependencies):
            raise ValueError('dependencies_not_satisfied')
        step.status = 'running'

    def finish(self, step_id, result: ToolResult):
        step = self.steps[step_id]
        if step.status != 'running':
            raise ValueError('step_not_running')
        step.status = 'succeeded' if result.ok else 'failed'
        step.result = result.to_dict()
        self.spent_cost += result.cost
        self.simulated_elapsed_seconds += result.duration_seconds
