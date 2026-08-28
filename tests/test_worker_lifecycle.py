import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WorkerLifecycleTests(unittest.TestCase):
    def _function(self, path, name):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        return next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name)

    def test_worker_has_only_one_final_app_backup_call(self):
        run = self._function(ROOT / 'src/core/automation_worker.py', '_run')
        backup_calls = [
            node for node in ast.walk(run)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'backup_account_app_data'
        ]
        self.assertEqual(1, len(backup_calls))

    def test_scenario_actions_do_not_own_login_restore_or_backup(self):
        path = ROOT / 'src/core/scenario_executor.py'
        tree = ast.parse(path.read_text(encoding='utf-8'))
        forbidden = {'first_time_login', 'restore_account_app_data', 'backup_account_app_data'}
        for function in [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name.startswith('execute_')]:
            called = {
                node.func.attr for node in ast.walk(function)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            }
            self.assertFalse(called & forbidden, function.name)

    def test_empty_scenario_does_not_inject_default_actions(self):
        text = (ROOT / 'src/core/automation_worker.py').read_text(encoding='utf-8')
        self.assertNotIn('executor.execute_newsfeed({"time_from": 15', text)
        self.assertNotIn('executor.execute_reels({"time_from": 20', text)


if __name__ == '__main__':
    unittest.main()
