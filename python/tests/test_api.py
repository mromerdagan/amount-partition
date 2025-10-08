import unittest
import tempfile
import shutil
import os
from pathlib import Path
from amount_partition.api import BudgetManagerApi
from amount_partition.models import InstalmentBalance

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
        self.assertEqual(manager.balances['free'].amount, 0)
        self.assertEqual(manager.balances['credit-spent'].amount, 0)

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
        initial = self.db._balances['free'].amount
        self.db.deposit(100)
        self.assertEqual(self.db._balances['free'].amount, initial + 100)

    def test_deposit_merges_credit(self):
        self.db._balances['credit-spent'].amount = 50
        self.db.deposit(100, monthly=True)
        self.assertEqual(self.db._balances['free'].amount, 150)
        self.assertEqual(self.db._balances['credit-spent'].amount, 0)

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
        self.assertEqual(self.db._balances['free'].amount, 150)

    def test_withdraw_all(self):
        self.db.withdraw()
        self.assertEqual(self.db._balances['free'].amount, 0)

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
        self.assertEqual(self.db._balances['test'].amount, 60)

    def test_spend_all(self):
        self.db.spend('test')
        self.assertEqual(self.db._balances['test'].amount, 0)

    def test_spend_with_credit(self):
        self.db.spend('test', 20, use_credit=True)
        self.assertEqual(self.db._balances['test'].amount, 80)
        self.assertEqual(self.db._balances['credit-spent'].amount, 20)

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
        self.assertEqual(self.db._balances['test'].amount, 50)
        self.assertEqual(self.db._balances['free'].amount, 150)

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
        self.assertEqual(self.db._balances['a'].amount, 70)
        self.assertEqual(self.db._balances['b'].amount, 80)

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
        self.assertEqual(self.db._balances['self-loan'].amount, -100)
        self.assertEqual(self.db._balances['free'].amount, 100)
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

    def test_plan_deposits(self):
        deposits_plan = self.db.plan_deposits()
        self.assertIn('box1', deposits_plan)
        self.assertIn('box2', deposits_plan)
        self.assertTrue(deposits_plan['box1'] > 0)
        self.assertTrue(deposits_plan['box2'] > 0)

    def test_apply_deposit_plan(self):
        deposits_plan = self.db.plan_deposits()
        self.db._apply_deposit_plan(deposits_plan)
        # After applying, balances should increase by suggested amount
        self.assertEqual(self.db._balances['box1'].amount, deposits_plan['box1'])
        self.assertEqual(self.db._balances['box2'].amount, deposits_plan['box2'])
        # 'free' should decrease by the sum
        self.assertEqual(self.db._balances['free'].amount, 
                        1000 - deposits_plan['box1'] - deposits_plan['box2'])


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
        self.assertEqual(data['partition']['target_box']["amount"], 
                        self.db._balances['target_box'].amount)
        self.assertEqual(data['partition']['recurring_box']["amount"], 
                        self.db._balances['recurring_box'].amount)
        self.assertEqual(data['goals']['target_box']['goal'], 300)
        self.assertEqual(data['goals']['target_box']['due'], '2030-01')
        self.assertEqual(data['periodic']['recurring_box']['amount'], 50)
        self.assertEqual(data['periodic']['recurring_box']['target'], 400)


class TestFromJson(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.data = {
            'partition': {'free': {'amount': 100, "type": "free"}, 'box2': {'amount': 50, "type": "regular"}},
            'goals': {'box2': {'goal': 200, 'due': '2031-05'}},
            'periodic': {'box2': {'amount': 20, 'target': 100}}
        }

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_from_json_creates_correct_state(self):
        db = BudgetManagerApi.from_json(self.data)
        self.assertEqual(db.balances['free'].amount, 100)
        self.assertEqual(db.balances['box2'].amount, 50)
        self.assertIn('box2', db._targets)
        self.assertEqual(db._targets['box2'].goal, 200)
        self.assertEqual(db._targets['box2'].due.strftime('%Y-%m'), '2031-05')
        self.assertIn('box2', db._recurring)
        self.assertEqual(db._recurring['box2'].amount, 20)
        self.assertEqual(db._recurring['box2'].target, 100)

class TestLinearScaling(unittest.TestCase):
    
    def test_scale_exact_total_and_nonnegative(self):
        s = {"a": 60, "b": 40}
        out = BudgetManagerApi._scale_deposit_plan(s, 75)
        assert sum(out.values()) == 75
        assert all(v >= 0 for v in out.values())
    
    def test_scale_up_preserves_proportions(self):
        s = {"x": 1, "y": 1, "z": 1}
        out = BudgetManagerApi._scale_deposit_plan(s, 5)  # from 3 to 5
        assert sum(out.values()) == 5
        # expect 2,2,1 in some order
        assert sorted(out.values(), reverse=True) == [2,2,1] 

    def test_zero_target_amount_results_in_all_zeros(self):
        s = {"a": 2, "b": 3}
        out = BudgetManagerApi._scale_deposit_plan(s, 0)
        assert out == {"a": 0, "b": 0}

    def test_zero_target_amount_results_in_all_zeros(self):
        s = {"a": 2, "b": 3}
        out = BudgetManagerApi._scale_deposit_plan(s, 0)
        assert out == {"a": 0, "b": 0}

class TestInstalment(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        BudgetManagerApi.create_db(self.tempdir)
        self.db = BudgetManagerApi.from_storage(self.tempdir)
        # Create a balance with some money for testing
        self.db.deposit(1000)
        self.db.new_box('source_box')
        self.db.add_to_balance('source_box', 500)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_missing_from_balance_raises(self):
        with self.assertRaises(KeyError) as context:
            self.db.new_instalment('test_inst', 'nonexistent_box', 5, 100)
        self.assertIn("missing from database", str(context.exception))

    def test_existing_instalment_name_raises(self):
        self.db.new_box('existing_box')
        with self.assertRaises(KeyError) as context:
            self.db.new_instalment('existing_box', 'source_box', 5, 100)
        self.assertIn("already exists", str(context.exception))

    def test_invalid_num_instalments_raises(self):
        with self.assertRaises(ValueError) as context:
            self.db.new_instalment('test_inst', 'source_box', 0, 100)
        self.assertIn("num_instalments must be at least 1", str(context.exception))

        with self.assertRaises(ValueError) as context:
            self.db.new_instalment('test_inst', 'source_box', -1, 100)
        self.assertIn("num_instalments must be at least 1", str(context.exception))

    def test_invalid_monthly_payment_raises(self):
        with self.assertRaises(ValueError) as context:
            self.db.new_instalment('test_inst', 'source_box', 5, 0)
        self.assertIn("monthly_payment must be positive", str(context.exception))

        with self.assertRaises(ValueError) as context:
            self.db.new_instalment('test_inst', 'source_box', 5, -100)
        self.assertIn("monthly_payment must be positive", str(context.exception))

    def test_insufficient_funds_raises(self):
        # Try to create instalment requiring 600 total (5 * 120) when balance has 500
        with self.assertRaises(ValueError) as context:
            self.db.new_instalment('test_inst', 'source_box', 5, 120)
        self.assertIn("Insufficient funds", str(context.exception))

    def test_successful_instalment_creation(self):
        # Create instalment: 5 payments of 80 each = 400 total
        self.db.new_instalment('test_inst', 'source_box', 5, 80)

        # Check source balance was reduced
        self.assertEqual(self.db._balances['source_box'].amount, 100)  # 500 - 400

        # Check instalment box was created with correct properties
        self.assertIn('test_inst', self.db._balances)
        instalment_box = self.db._balances['test_inst']
        self.assertTrue(isinstance(instalment_box, InstalmentBalance))
        self.assertEqual(instalment_box.amount, 400)  # total amount
        self.assertEqual(instalment_box.monthly_payment, 80)

    def test_single_instalment(self):
        """Test boundary case where num_instalments = 1"""
        self.db.new_instalment('single_inst', 'source_box', 1, 100)
        
        # Total amount should equal monthly payment
        instalment_box = self.db._balances['single_inst']
        self.assertTrue(isinstance(instalment_box, InstalmentBalance))
        self.assertEqual(instalment_box.amount, 100)
        self.assertEqual(instalment_box.monthly_payment, 100)
        self.assertEqual(self.db._balances['source_box'].amount, 400)  # 500 - 100

    def test_exact_balance_match(self):
        """Test when total amount exactly matches source balance"""
        # Create instalment that uses entire source balance (5 * 100 = 500)
        self.db.new_instalment('exact_inst', 'source_box', 5, 100)
        
        # Source balance should be zero
        self.assertEqual(self.db._balances['source_box'].amount, 0)
        
        # Instalment should have correct properties
        instalment_box = self.db._balances['exact_inst']
        self.assertTrue(isinstance(instalment_box, InstalmentBalance))
        self.assertEqual(instalment_box.amount, 500)
        self.assertEqual(instalment_box.monthly_payment, 100)

    def test_state_immutability_on_failure(self):
        """Test that _balances remains unchanged when operations fail"""
        original_balances = self.db._balances.copy()
        original_amount = self.db._balances['source_box'].amount
        
        # Test insufficient funds case
        try:
            self.db.new_instalment('test_inst', 'source_box', 10, 100)  # 1000 total > 500 available
        except ValueError:
            # Verify source balance is unchanged
            self.assertEqual(self.db._balances['source_box'].amount, original_amount)
            # Verify no new balance was added
            self.assertEqual(set(self.db._balances.keys()), set(original_balances.keys()))
        
        # Test invalid monthly payment
        try:
            self.db.new_instalment('test_inst', 'source_box', 5, -100)
        except ValueError:
            # Verify source balance is unchanged
            self.assertEqual(self.db._balances['source_box'].amount, original_amount)
            # Verify no new balance was added
            self.assertEqual(set(self.db._balances.keys()), set(original_balances.keys()))

    def test_multiple_instalments_from_same_source(self):
        """Test creating multiple instalments from the same source balance"""
        # Create first instalment: 3 payments of 50 each = 150 total
        self.db.new_instalment('inst1', 'source_box', 3, 50)
        
        # Verify first instalment
        inst1 = self.db._balances['inst1']
        self.assertTrue(isinstance(inst1, InstalmentBalance))
        self.assertEqual(inst1.amount, 150)
        self.assertEqual(inst1.monthly_payment, 50)
        
        # Source should have 350 remaining (500 - 150)
        self.assertEqual(self.db._balances['source_box'].amount, 350)
        
        # Create second instalment: 2 payments of 100 each = 200 total
        self.db.new_instalment('inst2', 'source_box', 2, 100)
        
        # Verify second instalment
        inst2 = self.db._balances['inst2']
        self.assertTrue(isinstance(inst2, InstalmentBalance))
        self.assertEqual(inst2.amount, 200)
        self.assertEqual(inst2.monthly_payment, 100)
        
        # Source should have 150 remaining (350 - 200)
        self.assertEqual(self.db._balances['source_box'].amount, 150)
        
        # Verify first instalment remains unchanged
        self.assertEqual(self.db._balances['inst1'].amount, 150)
        self.assertEqual(self.db._balances['inst1'].monthly_payment, 50)

class TestDepositWithInstallments(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        BudgetManagerApi.create_db(self.tempdir)
        self.db = BudgetManagerApi.from_storage(self.tempdir)
        # Set initial free balance
        self.db._balances['free'].amount = 1000
        
    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_deposit_with_active_instalment(self):
        """Test deposit behavior with credit spending and active instalment"""
        # Setup initial state
        self.db._balances['credit-spent'].amount = 200
        self.db._balances['plan1'] = InstalmentBalance(3000, 1000)  # 3 payments of 1000
        initial_free = self.db._balances['free'].amount

        # Make deposit
        self.db.deposit(1000, monthly=True)

        # Verify free balance increased by deposit + credit + instalment
        expected_free = initial_free + 1000 + 200 + 1000
        self.assertEqual(self.db._balances['free'].amount, expected_free)
        
        # Verify credit-spent was reset
        self.assertEqual(self.db._balances['credit-spent'].amount, 0)
        
        # Verify instalment was reduced
        self.assertEqual(self.db._balances['plan1'].amount, 2000)

    def test_sequential_instalment_payments(self):
        """Test instalment payments over multiple deposits"""
        # Setup instalment plan
        self.db._balances['plan1'] = InstalmentBalance(3000, 1000)  # 3 payments of 1000
        
        # First deposit
        self.db.deposit(100, monthly=True)
        self.assertEqual(self.db._balances['plan1'].amount, 2000)
        self.assertFalse(self.db._balances['plan1'].exhausted)
        
        # Second deposit
        self.db.deposit(100, monthly=True)
        self.assertEqual(self.db._balances['plan1'].amount, 1000)
        self.assertFalse(self.db._balances['plan1'].exhausted)
        
        # Third deposit
        self.db.deposit(100, monthly=True)
        self.assertEqual(self.db._balances['plan1'].amount, 0)
        self.assertTrue(self.db._balances['plan1'].exhausted)

    def test_exhausted_instalment_skipped(self):
        """Test that exhausted instalments are skipped during deposit"""
        # Setup exhausted instalment
        self.db._balances['plan1'] = InstalmentBalance(0, 1000)  # Start with 0 amount
        initial_free = self.db._balances['free'].amount
        
        # Make deposit
        deposit_amount = 500
        self.db.deposit(deposit_amount, monthly=True)
        
        # Verify instalment wasn't modified
        self.assertEqual(self.db._balances['plan1'].amount, 0)
        self.assertTrue(self.db._balances['plan1'].exhausted)
        
        # Verify free only increased by deposit amount (no instalment payment)
        self.assertEqual(self.db._balances['free'].amount, initial_free + deposit_amount)

    def test_multiple_active_instalments(self):
        """Test deposit with multiple active instalments"""
        # Setup two instalments
        self.db._balances['plan1'] = InstalmentBalance(2000, 500)  # 4 payments of 500
        self.db._balances['plan2'] = InstalmentBalance(3000, 1000)  # 3 payments of 1000
        initial_free = self.db._balances['free'].amount
        
        # Make deposit
        deposit_amount = 200
        self.db.deposit(deposit_amount, monthly=True)
        
        # Verify both instalments released their payments
        self.assertEqual(self.db._balances['plan1'].amount, 1500)  # 2000 - 500
        self.assertEqual(self.db._balances['plan2'].amount, 2000)  # 3000 - 1000
        
        # Verify free increased by deposit + both instalment payments
        expected_free = initial_free + deposit_amount + 500 + 1000
        self.assertEqual(self.db._balances['free'].amount, expected_free)

    def test_deposit_without_instalments(self):
        """Test deposit behavior with no instalments present"""
        # Setup credit spending
        self.db._balances['credit-spent'].amount = 300
        initial_free = self.db._balances['free'].amount
        
        # Make deposit
        deposit_amount = 500
        self.db.deposit(deposit_amount, monthly=True)
        
        # Verify free increased by deposit + credit merge only
        expected_free = initial_free + deposit_amount + 300
        self.assertEqual(self.db._balances['free'].amount, expected_free)
        self.assertEqual(self.db._balances['credit-spent'].amount, 0)

if __name__ == '__main__':
    unittest.main()
