import unittest
import tempfile
import shutil
from fastapi.testclient import TestClient
from amount_partition.rest_api import app
from amount_partition.api import BudgetManagerApi

client = TestClient(app)

# ---------- Base class for all REST API tests ----------

class RestApiTestCase(unittest.TestCase):
    """Base class for all REST API integration tests."""
    def setUp(self):
        self.tempdir = tempfile.mkdtemp(prefix="budget_api_test_")
        BudgetManagerApi.create_db(self.tempdir)

    def tearDown(self):
        shutil.rmtree(self.tempdir)
        
# ---------- Generic / error handling tests ----------

class TestRestApiGeneral(RestApiTestCase):
    """General-purpose REST API tests (error handling, health, etc.)"""

    def test_invalid_db_dir_returns_400(self):
        """Invalid db_dir should raise HTTP 400."""
        response = client.get("/balances", params={"db_dir": "/nonexistent/path"})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("detail", data)

# ---------- Balances retrieval ----------

class TestBalancesEndpoints(RestApiTestCase):
    """Tests for balance listing and retrieval endpoints."""

    def test_list_balances_default(self):
        """GET /list_balances returns the two default balances."""
        response = client.get("/list_balances", params={"db_dir": self.tempdir})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertIn("free", data)
        self.assertIn("credit-spent", data)
        self.assertEqual(len(data), 2)

    def test_get_balances_initial(self):
        """GET /balances returns dict with amount and type fields."""
        response = client.get("/balances", params={"db_dir": self.tempdir})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, dict)

        self.assertIn("free", data)
        self.assertEqual(data["free"]["type"], "free")
        self.assertEqual(data["free"]["amount"], 0)

        self.assertIn("credit-spent", data)
        self.assertEqual(data["credit-spent"]["type"], "credit")
        self.assertEqual(data["credit-spent"]["amount"], 0)


# ---------- Deposit and transfer operations ----------

class TestDepositAndTransfer(RestApiTestCase):
    """Tests for deposit, transfer, and money movement endpoints."""

    def test_deposit_increases_free_balance(self):
        """POST /deposit increases free balance amount."""
        response = client.post("/deposit", json={"amount": 500}, params={"db_dir": self.tempdir})
        self.assertEqual(response.status_code, 200)

        response = client.get("/balances", params={"db_dir": self.tempdir})
        balances = response.json()
        free = balances.get("free")
        self.assertIsNotNone(free)
        self.assertGreaterEqual(free["amount"], 500)
    
    def test_transfer_moves_funds_between_balances(self):
        """POST /transfer_between_balances moves funds correctly."""
        client.post("/deposit", json={"amount": 1000}, params={"db_dir": self.tempdir})
        client.post("/new_box", json={"boxname": "savings"}, params={"db_dir": self.tempdir})
        client.post("/add_to_balance", json={"boxname": "savings", "amount": 300}, params={"db_dir": self.tempdir})

        response = client.post("/transfer_between_balances", json={"from_box": "savings", "to_box": "free", "amount": 200}, params={"db_dir": self.tempdir})
        self.assertEqual(response.status_code, 200)

        response = client.get("/balances", params={"db_dir": self.tempdir})
        balances = response.json()
        self.assertEqual(balances["savings"]["amount"], 100)
        self.assertGreaterEqual(balances["free"]["amount"], 900)