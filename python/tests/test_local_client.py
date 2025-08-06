import unittest
import tempfile
import shutil
import os
import json
from amount_partition.client.local_budget_client import LocalBudgetManagerClient

class TestLocalBudgetManagerClient(unittest.TestCase):
    def setUp(self):
        self.basedir = tempfile.mkdtemp()
        self.db_path1 = os.path.join(self.basedir, "partition-db1")
        self.db_path2 = os.path.join(self.basedir, "partition-db2")

    def tearDown(self):
        shutil.rmtree(self.basedir)

    def test_export_import_consistency(self):
        # Create new DB and add data
        client1 = LocalBudgetManagerClient(self.db_path1)
        client1.create_db(self.db_path1)
        client1.new_box("vacation")
        client1.deposit(1000)
        client1.add_to_balance("vacation", 500)
        client1.set_target("vacation", 1500, "2026-02")
        client1.set_recurring("vacation", 100, 1500)

        # Export to JSON
        data = client1.export_json()

        # Create new DB and import
        client2 = LocalBudgetManagerClient(self.db_path2)
        client2.import_json(data)

        # Validate balances
        balances1 = client1.get_balances()
        balances2 = client2.get_balances()
        self.assertEqual(dict(balances1), dict(balances2))

        # Validate targets
        targets1 = client1.get_targets()
        targets2 = client2.get_targets()
        self.assertEqual(targets1, targets2)

        # Validate recurring
        recurring1 = client1.get_recurring()
        recurring2 = client2.get_recurring()
        self.assertEqual(recurring1, recurring2)

if __name__ == "__main__":
    unittest.main()
