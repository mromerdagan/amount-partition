from datetime import date, datetime, timedelta
import unittest
import tempfile
import shutil
import os
import json
from unittest.mock import patch
from amount_partition.client.local_budget_client import LocalBudgetManagerClient
from amount_partition.api import BudgetManagerApi

class TestLocalBudgetManagerClient(unittest.TestCase):
    def setUp(self):
        self.basedir = tempfile.mkdtemp()
        self.db_path1 = os.path.join(self.basedir, "partition-db1")
        self.db_path2 = os.path.join(self.basedir, "partition-db2")

    def tearDown(self):
        shutil.rmtree(self.basedir)
    
    @staticmethod
    def _two_months_ahead_str(today: date | None = None) -> str:
        """Return YYYY-MM exactly two months ahead of 'today' by month arithmetic."""
        if today is None:
            today = date.today()
        y, m = today.year, today.month
        m += 2
        y += (m - 1) // 12
        m = ((m - 1) % 12) + 1
        return f"{y:04d}-{m:02d}"

    def test_export_import_consistency(self):
        # Create new DB and add data
        client1 = LocalBudgetManagerClient(self.db_path1)
        client1.create_db(self.db_path1)
        
        # Create separate boxes for target and recurring to avoid conflict
        client1.new_box("vacation_target")
        client1.new_box("vacation_recurring")
        client1.deposit(1000)
        client1.add_to_balance("vacation_target", 300)
        client1.add_to_balance("vacation_recurring", 200)
        client1.set_target("vacation_target", 1500, "2026-02")
        client1.set_recurring("vacation_recurring", 100, 1500)

        # Export to JSON
        data = client1.export_json()

        # Create new DB and import
        client2 = LocalBudgetManagerClient(self.db_path2)
        client2.import_json(data)

        # Validate balances
        balances1 = client1.get_balances()
        balances2 = client2.get_balances()
        self.assertEqual(balances1, balances2)

        # Validate targets
        targets1 = client1.get_targets()
        targets2 = client2.get_targets()
        self.assertEqual(targets1, targets2)

        # Validate recurring
        recurring1 = client1.get_recurring()
        recurring2 = client2.get_recurring()
        self.assertEqual(recurring1, recurring2)

    def test_plan_deposits_unscaled(self):
        client = LocalBudgetManagerClient(self.db_path1)
        client.create_db(self.db_path1)
        client.new_box("vacation")
        client.new_box("new-car")
        client.deposit(1000)

        due_str = self._two_months_ahead_str(date.today())
        client.set_target("vacation", 1500, due_str)   # expect 750 this month (2 deposits left)
        client.set_recurring("new-car", 100, 1500)     # expect 100

        plan = client.plan_deposits("", True, 0)       # unscaled

        self.assertIn("vacation", plan)
        self.assertIn("new-car", plan)
        self.assertEqual(plan["vacation"], 750)
        self.assertEqual(plan["new-car"], 100)
        self.assertEqual(sum(plan.values()), 850)
    
    def test_plan_deposits_scaled(self):
        client = LocalBudgetManagerClient(self.db_path1)
        client.create_db(self.db_path1)
        client.new_box("vacation")
        client.new_box("new-car")
        client.deposit(1000)

        due_str = self._two_months_ahead_str(date.today())
        client.set_target("vacation", 1500, due_str)   # unscaled 750
        client.set_recurring("new-car", 100, 1500)     # unscaled 100

        plan = client.plan_deposits("", True, 1000)    # scale so total == 1000
        self.assertEqual(sum(plan.values()), 1000)

        # Derive exact expected allocation using the same allocator
        base = {"vacation": 750, "new-car": 100}
        expected = BudgetManagerApi._scale_deposit_plan(base, 1000)  # okay to use private in tests

        self.assertEqual(plan, expected)

if __name__ == "__main__":
    unittest.main()
