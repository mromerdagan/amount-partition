import unittest
import tempfile
import shutil
import os
from pathlib import Path
from amount_partition.api import BudgetManagerApi

class TestInstatiateBudgetManagerApi(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        
    def tearDown(self):
        shutil.rmtree(self.tempdir)
    
    def test_create_db_manager(self):
        db_path = Path(self.tempdir) / "test_db"
        if db_path.exists():
            shutil.rmtree(db_path)
        self.assertFalse(db_path.exists())
        
        # Create the database
        BudgetManagerApi.create_db(str(db_path))

        # Make sure BudgetManagerApi can be instantiated
        manager = BudgetManagerApi.from_storage(str(db_path))
        self.assertIsInstance(manager, BudgetManagerApi)
    
    def test_new_db_manager_contains_default_boxes(self):
        db_path = Path(self.tempdir) / "test_db"
        if db_path.exists():
            shutil.rmtree(db_path)
        
        # Create the database
        BudgetManagerApi.create_db(str(db_path))

        # Instantiate the manager
        manager = BudgetManagerApi.from_storage(str(db_path))
        
        # Check default balances
        self.assertIn('free', manager.balances)
        self.assertIn('credit-spent', manager.balances)
        self.assertEqual(manager.balances['free'], 0)
        self.assertEqual(manager.balances['credit-spent'], 0)

class TestListBalances(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        BudgetManagerApi.create_db(self.tempdir)
        self.db = BudgetManagerApi.from_storage(self.tempdir)
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
        BudgetManagerApi.create_db(self.tempdir)
        self.db = BudgetManagerApi.from_storage(self.tempdir)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_deposit_increases_free(self):
        initial = self.db._balances['free']
        self.db.deposit(100)
        self.assertEqual(self.db._balances['free'], initial + 100)

    def test_deposit_merges_credit(self):
        self.db._balances['credit-spent'] = 50
        self.db.deposit(100, merge_with_credit=True)
        self.assertEqual(self.db._balances['free'], 150)
        self.assertEqual(self.db._balances['credit-spent'], 0)

class TestWithdraw(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        BudgetManagerApi.create_db(self.tempdir)
        self.db = BudgetManagerApi.from_storage(self.tempdir)
        self.db.deposit(200)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_withdraw_amount(self):
        self.db.withdraw(50)
        self.assertEqual(self.db._balances['free'], 150)

    def test_withdraw_all(self):
        self.db.withdraw()
        self.assertEqual(self.db._balances['free'], 0)

class TestSpend(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        BudgetManagerApi.create_db(self.tempdir)
        self.db = BudgetManagerApi.from_storage(self.tempdir)
        self.db.deposit(200)
        self.db.new_box('test')
        self.db.add_to_balance('test', 100)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_spend_amount(self):
        self.db.spend('test', 40)
        self.assertEqual(self.db._balances['test'], 60)

    def test_spend_all(self):
        self.db.spend('test')
        self.assertEqual(self.db._balances['test'], 0)

    def test_spend_with_credit(self):
        self.db.spend('test', 20, use_credit=True)
        self.assertEqual(self.db._balances['test'], 80)
        self.assertEqual(self.db._balances['credit-spent'], 20)

class TestAddToBalance(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        BudgetManagerApi.create_db(self.tempdir)
        self.db = BudgetManagerApi.from_storage(self.tempdir)
        self.db.deposit(200)
        self.db.new_box('test')

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_add_to_balance(self):
        self.db.add_to_balance('test', 50)
        self.assertEqual(self.db._balances['test'], 50)
        self.assertEqual(self.db._balances['free'], 150)

class TestTransferBetweenBalances(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        BudgetManagerApi.create_db(self.tempdir)
        self.db = BudgetManagerApi.from_storage(self.tempdir)
        self.db.deposit(200)
        self.db.new_box('a')
        self.db.new_box('b')
        self.db.add_to_balance('a', 100)
        self.db.add_to_balance('b', 50)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_transfer(self):
        self.db.transfer_between_balances('a', 'b', 30)
        self.assertEqual(self.db._balances['a'], 70)
        self.assertEqual(self.db._balances['b'], 80)

class TestNewBoxRemoveBox(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        BudgetManagerApi.create_db(self.tempdir)
        self.db = BudgetManagerApi.from_storage(self.tempdir)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_new_box(self):
        self.db.new_box('newbox')
        self.assertIn('newbox', self.db._balances)

    def test_remove_box(self):
        self.db.new_box('toremove')
        self.db.deposit(100)
        self.db.add_to_balance('toremove', 10)
        self.db.remove_box('toremove')
        self.assertNotIn('toremove', self.db._balances)

class TestNewLoan(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        BudgetManagerApi.create_db(self.tempdir)
        self.db = BudgetManagerApi.from_storage(self.tempdir)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_new_loan(self):
        self.db.new_loan(100, '2030-01')
        self.assertIn('self-loan', self.db._balances)
        self.assertEqual(self.db._balances['self-loan'], -100)
        self.assertEqual(self.db._balances['free'], 100)
        self.assertIn('self-loan', self.db._targets)

class TestSetTarget(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        BudgetManagerApi.create_db(self.tempdir)
        self.db = BudgetManagerApi.from_storage(self.tempdir)
        self.db.new_box('goalbox')

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_set_target(self):
        self.db.set_target('goalbox', 500, '2030-01')
        self.assertIn('goalbox', self.db._targets)
        self.assertEqual(self.db._targets['goalbox'].goal, 500)
        self.assertEqual(self.db._targets['goalbox'].due.strftime('%Y-%m'), '2030-01')

class TestSuggestDepositsApplySuggestion(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        BudgetManagerApi.create_db(self.tempdir)
        self.db = BudgetManagerApi.from_storage(self.tempdir)
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
        self.assertEqual(self.db._balances['box1'], suggestion['box1'])
        self.assertEqual(self.db._balances['box2'], suggestion['box2'])
        # 'free' should decrease by the sum
        self.assertEqual(self.db._balances['free'], 1000 - suggestion['box1'] - suggestion['box2'])


class TestToJson(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        BudgetManagerApi.create_db(self.tempdir)
        self.db = BudgetManagerApi.from_storage(self.tempdir)
        self.db.deposit(500)
        # Create separate boxes for target and recurring to avoid conflict
        self.db.new_box('target_box')
        self.db.add_to_balance('target_box', 200)
        self.db.set_target('target_box', 300, '2030-01')
        self.db.new_box('recurring_box')
        self.db.add_to_balance('recurring_box', 100)
        self.db.set_recurring('recurring_box', 50, 400)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_to_json_structure(self):
        data = self.db.to_json()
        self.assertIn('partition', data)
        self.assertIn('goals', data)
        self.assertIn('periodic', data)
        self.assertEqual(data['partition']['target_box'], 200)
        self.assertEqual(data['partition']['recurring_box'], 100)
        self.assertEqual(data['goals']['target_box']['goal'], 300)
        self.assertEqual(data['goals']['target_box']['due'], '2030-01')
        self.assertEqual(data['periodic']['recurring_box']['amount'], 50)
        self.assertEqual(data['periodic']['recurring_box']['target'], 400)


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
        db = BudgetManagerApi.from_json(self.data)
        self.assertEqual(db.balances['free'], 100)
        self.assertEqual(db.balances['box2'], 50)
        self.assertIn('box2', db._targets)
        self.assertEqual(db._targets['box2'].goal, 200)
        self.assertEqual(db._targets['box2'].due.strftime('%Y-%m'), '2031-05')
        self.assertIn('box2', db._recurring)
        self.assertEqual(db._recurring['box2'].amount, 20)
        self.assertEqual(db._recurring['box2'].target, 100)

class TestLinearScaling(unittest.TestCase):
    
    def test_scale_exact_total_and_nonnegative(self):
        s = {"a": 60, "b": 40}
        out = BudgetManagerApi._scale_suggestion_to_total(s, 75)
        assert sum(out.values()) == 75
        assert all(v >= 0 for v in out.values())
    
    def test_scale_up_preserves_proportions(self):
        s = {"x": 1, "y": 1, "z": 1}
        out = BudgetManagerApi._scale_suggestion_to_total(s, 5)  # from 3 to 5
        assert sum(out.values()) == 5
        # expect 2,2,1 in some order
        assert sorted(out.values(), reverse=True) == [2,2,1] 

    def test_zero_target_total_results_in_all_zeros(self):
        s = {"a": 2, "b": 3}
        out = BudgetManagerApi._scale_suggestion_to_total(s, 0)
        assert out == {"a": 0, "b": 0}


if __name__ == '__main__':
    unittest.main()
