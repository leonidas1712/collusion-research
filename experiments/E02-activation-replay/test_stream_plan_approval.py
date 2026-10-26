"""Offline checks for capture-plan compatibility and local progress reporting."""
import ast
import contextlib
import io
import json
from pathlib import Path
import unittest

from stream_plan_approval import approved_stream_plan, CAPTURE_SPEC, BUDGET_APPROVAL

ROOT = Path(__file__).resolve().parents[2]


class PlanApprovalTests(unittest.TestCase):
    def test_original_plan_is_immutable(self):
        raw = (ROOT / 'runs/20261026-0659-e02-gpt-oss-stream-plan/plan.json').read_bytes()
        self.assertTrue(approved_stream_plan(raw))
        self.assertFalse(approved_stream_plan(raw + b'\n'))

    def test_descriptive_markers(self):
        plan = dict(capture_spec=CAPTURE_SPEC, budget_approval=BUDGET_APPROVAL)
        self.assertTrue(approved_stream_plan(json.dumps(plan).encode()))
        plan['budget_approval'] = 'unapproved'
        self.assertFalse(approved_stream_plan(json.dumps(plan).encode()))
        self.assertFalse(approved_stream_plan(b'{}'))

    def test_confirmation_progress_is_local(self):
        source = (Path(__file__).parent / 'run_stream_confirmation.py').read_text()
        tree = ast.parse(source)
        fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'say')
        namespace = {}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), '<progress>', 'exec'), namespace)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            namespace['say']('capture finished')
        self.assertEqual(output.getvalue(), 'capture finished\n')
        self.assertNotIn("'aboard'", source)


if __name__ == '__main__':
    unittest.main()
