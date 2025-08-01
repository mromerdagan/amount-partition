import unittest
import tempfile
import shutil
import os
from pathlib import Path
from amount_partition.api import BudgetManagerApi

class TestListBalances(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.db = BudgetManagerApi(self.tempdir)
        self.db.deposit(100)
        self.db.new_box('testbox')
        self.db.add_to_balance('testbox', 50)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_list_balances(self):
        balances = self.db.list_balances()
        self.assertIn('free', balances)
        self.assertIn('testbox', balances)
        self.assertIn('credit-spent', balances)
        self.assertEqual(len(balances), 3)  # 'free' and 'testbox'

class TestDeposit(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.db = BudgetManagerApi(self.tempdir)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_deposit_increases_free(self):
        initial = self.db.balances['free']
        self.db.deposit(100)
        self.assertEqual(self.db.balances['free'], initial + 100)

    def test_deposit_merges_credit(self):
        self.db.balances['credit-spent'] = 50
        self.db.deposit(100, merge_with_credit=True)
        self.assertEqual(self.db.balances['free'], 150)
        self.assertEqual(self.db.balances['credit-spent'], 0)

class TestWithdraw(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.db = BudgetManagerApi(self.tempdir)
        self.db.deposit(200)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_withdraw_amount(self):
        self.db.withdraw(50)
        self.assertEqual(self.db.balances['free'], 150)

    def test_withdraw_all(self):
        self.db.withdraw()
        self.assertEqual(self.db.balances['free'], 0)

class TestSpend(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.db = BudgetManagerApi(self.tempdir)
        self.db.deposit(200)
        self.db.new_box('test')
        self.db.add_to_balance('test', 100)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_spend_amount(self):
        self.db.spend('test', 40)
        self.assertEqual(self.db.balances['test'], 60)

    def test_spend_all(self):
        self.db.spend('test')
        self.assertEqual(self.db.balances['test'], 0)

    def test_spend_with_credit(self):
        self.db.spend('test', 20, use_credit=True)
        self.assertEqual(self.db.balances['test'], 80)
        self.assertEqual(self.db.balances['credit-spent'], 20)

class TestAddToBalance(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.db = BudgetManagerApi(self.tempdir)
        self.db.deposit(200)
        self.db.new_box('test')

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_add_to_balance(self):
        self.db.add_to_balance('test', 50)
        self.assertEqual(self.db.balances['test'], 50)
        self.assertEqual(self.db.balances['free'], 150)

class TestTransferBetweenBalances(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.db = BudgetManagerApi(self.tempdir)
        self.db.deposit(200)
        self.db.new_box('a')
        self.db.new_box('b')
        self.db.add_to_balance('a', 100)
        self.db.add_to_balance('b', 50)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_transfer(self):
        self.db.transfer_between_balances('a', 'b', 30)
        self.assertEqual(self.db.balances['a'], 70)
        self.assertEqual(self.db.balances['b'], 80)

class TestNewBoxRemoveBox(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.db = BudgetManagerApi(self.tempdir)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_new_box(self):
        self.db.new_box('newbox')
        self.assertIn('newbox', self.db.balances)

    def test_remove_box(self):
        self.db.new_box('toremove')
        self.db.deposit(100)
        self.db.add_to_balance('toremove', 10)
        self.db.remove_box('toremove')
        self.assertNotIn('toremove', self.db.balances)

class TestNewLoan(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.db = BudgetManagerApi(self.tempdir)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_new_loan(self):
        self.db.new_loan(100, '2030-01')
        self.assertIn('self-loan', self.db.balances)
        self.assertEqual(self.db.balances['self-loan'], -100)
        self.assertEqual(self.db.balances['free'], 100)
        self.assertIn('self-loan', self.db.targets)

class TestSetTarget(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.db = BudgetManagerApi(self.tempdir)
        self.db.new_box('goalbox')

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_set_target(self):
        self.db.set_target('goalbox', 500, '2030-01')
        self.assertIn('goalbox', self.db.targets)
        self.assertEqual(self.db.targets['goalbox'].goal, 500)
        self.assertEqual(self.db.targets['goalbox'].due.strftime('%Y-%m'), '2030-01')

class TestSuggestDepositsApplySuggestion(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.db = BudgetManagerApi(self.tempdir)
        self.db.deposit(1000)
        self.db.new_box('box1')
        self.db.set_target('box1', 600, '2030-01')
        self.db.new_box('box2')
        self.db.set_target('box2', 300, '2030-01')

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_suggest_deposits(self):
        suggestion = self.db.suggest_deposits()
        self.assertIn('box1', suggestion)
        self.assertIn('box2', suggestion)
        self.assertTrue(suggestion['box1'] > 0)
        self.assertTrue(suggestion['box2'] > 0)

    def test_apply_suggestion(self):
        suggestion = self.db.suggest_deposits()
        self.db.apply_suggestion(suggestion)
        # After applying, balances should increase by suggested amount
        self.assertEqual(self.db.balances['box1'], suggestion['box1'])
        self.assertEqual(self.db.balances['box2'], suggestion['box2'])
        # 'free' should decrease by the sum
        self.assertEqual(self.db.balances['free'], 1000 - suggestion['box1'] - suggestion['box2'])


class TestToJson(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.db = BudgetManagerApi(self.tempdir)
        self.db.deposit(500)
        self.db.new_box('box1')
        self.db.add_to_balance('box1', 200)
        self.db.set_target('box1', 300, '2030-01')
        self.db.set_recurring('box1', 50, 400)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_to_json_structure(self):
        data = self.db.to_json()
        self.assertIn('partition', data)
        self.assertIn('goals', data)
        self.assertIn('periodic', data)
        self.assertEqual(data['partition']['box1'], 200)
        self.assertEqual(data['goals']['box1']['goal'], 300)
        self.assertEqual(data['goals']['box1']['due'], '2030-01')
        self.assertEqual(data['periodic']['box1']['amount'], 50)
        self.assertEqual(data['periodic']['box1']['target'], 400)


class TestFromJson(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.data = {
            'partition': {'free': 100, 'box2': 50},
            'goals': {'box2': {'goal': 200, 'due': '2031-05'}},
            'periodic': {'box2': {'amount': 20, 'target': 100}}
        }

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_from_json_creates_correct_state(self):
        db = BudgetManagerApi.from_json(self.tempdir, self.data)
        self.assertEqual(db.balances['free'], 100)
        self.assertEqual(db.balances['box2'], 50)
        self.assertIn('box2', db.targets)
        self.assertEqual(db.targets['box2'].goal, 200)
        self.assertEqual(db.targets['box2'].due.strftime('%Y-%m'), '2031-05')
        self.assertIn('box2', db.recurring)
        self.assertEqual(db.recurring['box2'].amount, 20)
        self.assertEqual(db.recurring['box2'].target, 100)
        
    
    def test_from_json_overrides_existing_db(self):
        # First, create a db with different data
        db1 = BudgetManagerApi(self.tempdir)
        db1.deposit(999)
        db1.new_box('oldbox')
        db1.add_to_balance('oldbox', 888)
        # Now, use from_json to overwrite
        db2 = BudgetManagerApi.from_json(self.tempdir, self.data)
        # Should match the new data, not the old
        self.assertEqual(db2.balances['free'], 100)
        self.assertEqual(db2.balances['box2'], 50)
        self.assertNotIn('oldbox', db2.balances)
        self.assertIn('box2', db2.targets)
        self.assertEqual(db2.targets['box2'].goal, 200)
        self.assertEqual(db2.targets['box2'].due.strftime('%Y-%m'), '2031-05')
        self.assertIn('box2', db2.recurring)
        self.assertEqual(db2.recurring['box2'].amount, 20)
        self.assertEqual(db2.recurring['box2'].target, 100)


if __name__ == '__main__':
    unittest.main()
