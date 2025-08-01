import unittest
from unittest.mock import patch, Mock
from amount_partition.client.remote_budget_client import RemoteBudgetManagerClient

class TestRemoteBudgetManagerClient(unittest.TestCase):

    def setUp(self):
        self.client = RemoteBudgetManagerClient("http://fake-api", db_path="/tmp/budget")

    @patch("amount_partition.client.remote_budget_client.requests.get")
    def test_get_balances(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {"free": 100, "vacation": 50}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = self.client.get_balances()
        self.assertEqual(result["free"], 100)
        self.assertEqual(result["vacation"], 50)
        mock_get.assert_called_once_with("http://fake-api/balances", params={"db_dir": "/tmp/budget"})

    @patch("amount_partition.client.remote_budget_client.requests.post")
    def test_deposit(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {"free": 200}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = self.client.deposit(100, merge_with_credit=True)
        self.assertEqual(result["free"], 200)
        mock_post.assert_called_once_with(
            "http://fake-api/deposit",
            json={"amount": 100, "merge_with_credit": True},
            params={"db_dir": "/tmp/budget"}
        )

    @patch("amount_partition.client.remote_budget_client.requests.get")
    def test_list_balances(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = ["free", "vacation"]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = self.client.list_balances()
        self.assertEqual(result, ["free", "vacation"])
        mock_get.assert_called_once_with("http://fake-api/list_balances", params={"db_dir": "/tmp/budget"})

    @patch("amount_partition.client.remote_budget_client.requests.get")
    def test_get_targets(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = [{"name": "vacation", "goal": 500, "due": "2030-01"}]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = self.client.get_targets()
        self.assertEqual(result[0]["name"], "vacation")
        self.assertEqual(result[0]["goal"], 500)
        self.assertEqual(result[0]["due"], "2030-01")
        mock_get.assert_called_once_with("http://fake-api/targets", params={"db_dir": "/tmp/budget"})

    @patch("amount_partition.client.remote_budget_client.requests.post")
    def test_set_target(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {"status": "ok"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = self.client.set_target("vacation", 500, "2030-01")
        self.assertEqual(result["status"], "ok")
        mock_post.assert_called_once_with(
            "http://fake-api/set_target",
            json={"boxname": "vacation", "goal": 500, "due": "2030-01"},
            params={"db_dir": "/tmp/budget"}
        )

    @patch("amount_partition.client.remote_budget_client.requests.post")
    def test_withdraw(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {"free": 0}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = self.client.withdraw(50)
        self.assertEqual(result["free"], 0)
        mock_post.assert_called_once_with(
            "http://fake-api/withdraw",
            json={"amount": 50},
            params={"db_dir": "/tmp/budget"}
        )
    
    @patch("amount_partition.client.remote_budget_client.requests.post")
    def test_add_to_balance(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {"balance": 100, "free": 900}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = self.client.add_to_balance("vacation", 100)
        self.assertEqual(result["balance"], 100)
        mock_post.assert_called_once_with(
            "http://fake-api/add_to_balance",
            json={"boxname": "vacation", "amount": 100},
            params={"db_dir": "/tmp/budget"}
        )

    @patch("amount_partition.client.remote_budget_client.requests.post")
    def test_new_box(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {"status": "ok"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = self.client.new_box("newbox")
        self.assertEqual(result["status"], "ok")
        mock_post.assert_called_once_with(
            "http://fake-api/new_box",
            json={"boxname": "newbox"},
            params={"db_dir": "/tmp/budget"}
        )

    @patch("amount_partition.client.remote_budget_client.requests.post")
    def test_remove_box(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {"status": "ok"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = self.client.remove_box("oldbox")
        self.assertEqual(result["status"], "ok")
        mock_post.assert_called_once_with(
            "http://fake-api/remove_box",
            json={"boxname": "oldbox"},
            params={"db_dir": "/tmp/budget"}
        )

    @patch("amount_partition.client.remote_budget_client.requests.post")
    def test_new_loan(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {"status": "ok"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = self.client.new_loan(500, "2030-01")
        self.assertEqual(result["status"], "ok")
        mock_post.assert_called_once_with(
            "http://fake-api/new_loan",
            json={"amount": 500, "due": "2030-01"},
            params={"db_dir": "/tmp/budget"}
        )

    @patch("amount_partition.client.remote_budget_client.requests.post")
    def test_create_db(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {"status": "created", "location": "/tmp/db"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = self.client.create_db("/tmp/db")
        self.assertEqual(result["status"], "created")
        mock_post.assert_called_once_with(
            "http://fake-api/create_db",
            json={"location": "/tmp/db"}
        )

    @patch("amount_partition.client.remote_budget_client.requests.post")
    def test_spend(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {"balance": 0, "credit-spent": 0}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = self.client.spend("vacation", 50, use_credit=True)
        self.assertEqual(result["balance"], 0)
        mock_post.assert_called_once_with(
            "http://fake-api/spend",
            json={"boxname": "vacation", "amount": 50, "use_credit": True},
            params={"db_dir": "/tmp/budget"}
        )


if __name__ == "__main__":
    unittest.main()
