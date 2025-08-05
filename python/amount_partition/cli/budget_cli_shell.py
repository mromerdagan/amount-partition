import argparse
import cmd
import sys
import re
from rich.console import Console
from rich.table import Table

from amount_partition.client.local_budget_client import LocalBudgetManagerClient
from amount_partition.client.remote_budget_client import RemoteBudgetManagerClient

console = Console()


class BudgetShell(cmd.Cmd):
    intro = "[bold green]Welcome to Budget CLI[/bold green]. Type 'help' or '?' to list commands.\n"
    prompt = "[budget] > "

    def __init__(self, client):
        super().__init__()
        self.client = client

    def do_exit(self, arg):
        "Exit the CLI"
        return True

    def do_quit(self, arg):
        "Exit the CLI (alias for exit)"
        return self.do_exit(arg)

    def do_list(self, arg):
        "List all box names"
        box_names = self.client.list_balances()
        for name in box_names:
            console.print(f"- {name}")

    def do_balances(self, arg):
        "Show current balances"
        balances = self.client.get_balances()
        table = Table(title="Balances")
        table.add_column("Box", style="cyan")
        table.add_column("Amount", style="magenta", justify="right")
        print(balances)

        for name, amount in balances.items():
            table.add_row(name, f"{amount:.2f}")

        console.print(table)
    
    def do_targets(self, arg):
        " List all targets. Usage: list_targets [--curr-month-payed]"
        parts = arg.strip().split()
        curr_month_payed = True if len(parts) > 0 and parts[0] == "--curr-month-payed" else False
                
        "List all targets. Usage: list_targets"
        table = Table(title="Targets")
        table.add_column("Box", style="cyan")
        table.add_column("Goal", style="magenta", justify="right")
        table.add_column("Due", style="green")
        table.add_column("Current Balance", style="yellow", justify="right")
        table.add_column("Months Left", style="blue", justify="right")
        table.add_column("Monthly Payment", style="magenta", justify="right")
        
        targets = self.client.get_targets()
        balances = self.client.get_balances()
        for target_name, target in targets.items():
            name = target_name
            goal = target.goal
            due = target.due.strftime("%Y-%m")
            current_balance = balances.get(target_name, 0.0)
            months_left = target.months_left(curr_month_payed)
            monthly_payment = target.monthly_payment(balance=current_balance, curr_month_payed=curr_month_payed)
            table.add_row(
                str(name), str(goal), str(due), str(current_balance), str(months_left), f"{monthly_payment:.2f}" if isinstance(monthly_payment, float) else str(monthly_payment)
            )
        console.print(table)
    
    def do_recurring(self, arg):
        "List all recurring deposits"
        table = Table(title="Recurring Deposits")
        table.add_column("Name", style="cyan")
        table.add_column("Amount", style="magenta", justify="right")
        table.add_column("Target", style="green")
        table.add_column("Current Balance", style="yellow", justify="right")
        
        recurring = self.client.get_recurring()
        balances = self.client.get_balances()
        for name, periodic in recurring.items():
            amount = periodic.amount
            target = periodic.target
            current_balance = balances.get(name, 0.0)
            table.add_row(
                str(name), f"{amount:.2f}", str(target), f"{current_balance:.2f}"
            )
        console.print(table)   
    
    def do_deposit(self, arg):
        "Deposit an amount into 'free'. Usage: deposit <amount> [--merge-with-credit]"
        parts = arg.strip().split()
        if not parts:
            console.print("[red]Usage: deposit <amount> [--merge-with-credit][/red]")
            return
        try:
            amount = int(parts[0])
        except Exception:
            console.print("[red]Usage: deposit <amount> [--merge-with-credit][/red]")
            return
        merge_with_credit = False
        if len(parts) > 1 and parts[1] == "--merge-with-credit":
            merge_with_credit = True
        result = self.client.deposit(amount, merge_with_credit=merge_with_credit)
        console.print(f"Deposited {amount}. New free balance: {result.get('free', '?')}")
        if merge_with_credit:
            console.print("'credit-spent' merged into 'free'.")

    def do_withdraw(self, arg):
        "Withdraw an amount from 'free'. Usage: withdraw <amount>"
        try:
            amount = int(arg.strip())
        except Exception:
            console.print("[red]Usage: withdraw <amount>[/red]")
            return
        result = self.client.withdraw(amount)
        console.print(f"Withdrew {amount}. New free balance: {result.get('free', '?')}")

    def do_add(self, arg):
        "Add amount to a box. Usage: add_to_balance <box> <amount>"
        parts = arg.strip().split()
        if len(parts) != 2:
            console.print("[red]Usage: add_to_balance <box> <amount>[/red]")
            return
        box, amount = parts
        try:
            amount = int(amount)
        except Exception:
            console.print("[red]Amount must be an integer.[/red]")
            return
        result = self.client.add_to_balance(box, amount)
        console.print(f"Added {amount} to {box}. New balance: {result.get('balance', '?')}")  
    
    def do_spend(self, arg):
        "Spend amount from a box. Usage: spend <box> <amount> [--use-credit]"
        parts = arg.strip().split()
        if len(parts) not in (2, 3):
            console.print("[red]Usage: spend <box> <amount> [--use-credit][/red]")
            return
        box, amount = parts[0], parts[1]
        use_credit = False
        if len(parts) == 3 and parts[2] == "--use-credit":
            use_credit = True
        try:
            amount = int(amount)
        except Exception:
            console.print("[red]Amount must be an integer.[/red]")
            return
        result = self.client.spend(box, amount, use_credit=use_credit)
        console.print(f"Spent {amount} from {box}. New balance: {result.get('balance', '?')}")

    def do_transfer(self, arg):
        "Transfer amount from one box to another. Usage: transfer <from> <to> <amount>"
        parts = arg.strip().split()
        if len(parts) != 3:
            console.print("[red]Usage: transfer <from> <to> <amount>[/red]")
            return
        from_box, to_box, amount = parts
        try:
            amount = int(amount)
        except Exception:
            console.print("[red]Amount must be an integer.[/red]")
            return
        if not hasattr(self.client, 'transfer_between_balances'):
            console.print("[red]Transfer not supported by this client.[/red]")
            return
        result = self.client.transfer_between_balances(from_box, to_box, amount)
        console.print(f"Transferred {amount} from {from_box} to {to_box}.")

    def do_new_box(self, arg):
        "Create a new box. Usage: new_box <box>"
        box = arg.strip()
        if not box:
            console.print("[red]Usage: new_box <box>[/red]")
            return
        try:
            self.client.new_box(box)   
        except Exception as e:
            console.print(f"[red]Error creating box '{box}': {e}[/red]")
            return
        # if we reach here, it means the box was created successfully
        console.print(f"Created new box '{box}'")

    def do_remove_box(self, arg):
        "Remove a box. Usage: remove_box <box>"
        box = arg.strip()
        if not box:
            console.print("[red]Usage: remove_box <box>[/red]")
            return
        try:
            self.client.remove_box(box)
        except Exception as e:
            console.print(f"[red]Error removing box '{box}': {e}[/red]")
            return
        # if we reach here, it means the box was removed successfully
        console.print(f"Removed box '{box}'")
    
    def do_set_target(self, arg):
        "Set a target for a box. Usage: set_target <box> <goal> <due> (due format: YYYY-MM)"
        parts = arg.strip().split()
        if len(parts) != 3:
            console.print("[red]Usage: set_target <box> <goal> <due>[/red]")
            return
        box, goal, due = parts
        
        # validate box exists
        if box not in self.client.list_balances():
            console.print(f"[red]Box '{box}' does not exist.[/red]")
            return
        
        # validate goal is an integer
        try:
            goal = int(goal)
        except Exception:
            console.print("[red]Goal must be an integer.[/red]")
            return
        
        # validate due format
        pattern = r"^\d{4}-\d{2}$"
        if not re.match(pattern, due):
            console.print("[red]Due date must be in YYYY-MM format.[/red]")
            return
        
        result = self.client.set_target(box, goal, due)
        console.print(f"Set target for {box}: {goal} by {due}. Result: {result}")
    
    def do_set_recurring(self, arg):
        "Set a recurring deposit for a box. Usage: set_recurring <box> <monthly> <target>"
        parts = arg.strip().split()
        if len(parts) != 3:
            console.print("[red]Usage: set_recurring <box> <monthly> <target>[/red]")
            return
        box, monthly, target = parts
        
        # validate box exists
        if box not in self.client.list_balances():
            console.print(f"[red]Box '{box}' does not exist.[/red]")
            return
        
        # validate monthly and target are integers
        try:
            monthly = int(monthly)
            target = int(target)
        except Exception:
            console.print("[red]Monthly and target must be integers.[/red]")
            return
        
        result = self.client.set_recurring(box, monthly, target)
        console.print(f"Set recurring for {box}: {monthly} monthly towards {target}")
    
    def do_remove_recurring(self, arg):
        "Remove a recurring deposit for a box. Usage: remove_recurring <box>"
        box = arg.strip()
        if not box:
            console.print("[red]Usage: remove_recurring <box>[/red]")
            return
        try:
            self.client.remove_recurring(box)
        except Exception as e:
            console.print(f"[red]Error removing recurring for box '{box}': {e}[/red]")
            return
        # if we reach here, it means the recurring was removed successfully
        console.print(f"Removed recurring for box '{box}'")

    def do_new_loan(self, arg):
        "Create a new loan. Usage: new_loan <amount> <due>"
        parts = arg.strip().split()
        if len(parts) != 2:
            console.print("[red]Usage: new_loan <amount> <due>[/red]")
            return
        amount, due = parts
        try:
            amount = int(amount)
        except Exception:
            console.print("[red]Amount must be an integer.[/red]")
            return
        result = self.client.new_loan(amount, due)
        console.print(f"Created new loan of {amount} due {due}. Result: {result}")

    def do_export_json(self, arg):
        "Export database to JSON file. Usage: export_json <dest-file>"
        dest_file = arg.strip()
        if not dest_file:
            console.print("[red]Usage: export_json <dest-file>[/red]")
            return
        if not hasattr(self.client, 'export_json'):
            # fallback: try to_json
            if hasattr(self.client, 'manager') and hasattr(self.client.manager, 'to_json'):
                data = self.client.manager.to_json()
            else:
                console.print("[red]Export not supported by this client.[/red]")
                return
        else:
            data = self.client.export_json()
        import json
        with open(dest_file, 'w') as f:
            json.dump(data, f, indent=2)
        console.print(f"Exported database to {dest_file}.")

    def do_import_json(self, arg):
        "Import database from JSON file. Usage: import_json <src-file>"
        src_file = arg.strip()
        if not src_file:
            console.print("[red]Usage: import_json <src-file>[/red]")
            return
        import json
        with open(src_file, 'r') as f:
            data = json.load(f)
        if hasattr(self.client, 'import_json'):
            result = self.client.import_json(data)
        elif hasattr(self.client, 'manager') and hasattr(self.client.manager, 'from_json'):
            # fallback for local client
            self.client.manager.from_json(self.client.manager.db_dir, data)
            result = {"status": "imported"}
        else:
            console.print("[red]Import not supported by this client.[/red]")
            return
        console.print(f"Imported database from {src_file}. Result: {result}")



def parse_args():
    parser = argparse.ArgumentParser(description="Interactive Budget CLI")
    parser.add_argument("--db-path", type=str, required=True, help="Path to database (used for both local and remote)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--local", action="store_true", help="Use local DB (direct access)")
    group.add_argument("--remote", type=str, metavar="URL", help="Use remote REST API at given URL")

    return parser.parse_args()


def main():
    args = parse_args()

    if args.local:
        client = LocalBudgetManagerClient(db_dir=args.db_path)
    elif args.remote:
        client = RemoteBudgetManagerClient(rest_api_url=args.remote, db_path=args.db_path)
    else:
        console.print("[bold red]Error:[/bold red] Either --local or --remote must be specified.")
        sys.exit(1)

    shell = BudgetShell(client)
    shell.cmdloop()



if __name__ == "__main__":
    main()
