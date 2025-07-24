import typer
from amount_partition.api import BudgetManager
from amount_partition.presentation import print_summary



app = typer.Typer()


@app.command()
def summary(db_dir: str = typer.Option('.', '--db-dir', help="Path to the database directory")):
    """Show a summary of balances, targets, and recurring deposits."""
    manager = BudgetManager(db_dir)
    print_summary(
        balances=manager.balances,
        targets=manager.targets,
        recurring=manager.recurring,
        total=manager.get_total()
    )



@app.command()
def deposit(
    amount: int = typer.Argument(..., help="Amount to deposit into 'free' balance"),
    db_dir: str = typer.Option('.', '--db-dir', help="Path to the database directory"),
    merge_with_credit: bool = typer.Option(True, help="Merge 'credit-spent' into 'free' on deposit")
):
    """Deposit an amount into the 'free' balance. Optionally merge 'credit-spent'."""
    manager = BudgetManager(db_dir)
    manager.deposit(amount, merge_with_credit=merge_with_credit)
    manager.dump_data()
    typer.echo(f"Deposited {amount} into 'free'. New 'free' balance: {manager.balances['free']}")
    if merge_with_credit:
        typer.echo(f"'credit-spent' merged into 'free'.")


@app.command()
def withdraw(
    amount: int = typer.Argument(0, help="Amount to withdraw from 'free' balance (0 empties 'free')"),
    db_dir: str = typer.Option('.', '--db-dir', help="Path to the database directory")
):
    """Withdraw an amount from 'free'. If amount is 0, empty 'free'."""
    manager = BudgetManager(db_dir)
    manager.withdraw(amount)
    manager.dump_data()
    typer.echo(f"Withdrew {amount} from 'free'. New 'free' balance: {manager.balances['free']}")


@app.command()
def spend(
    boxname: str = typer.Argument(..., help="Balance to spend from"),
    amount: int = typer.Argument(0, help="Amount to spend (0 spends all)"),
    use_credit: bool = typer.Option(False, help="Add spent amount to 'credit-spent'"),
    db_dir: str = typer.Option('.', '--db-dir', help="Path to the database directory")
):
    """Spend an amount from a balance. Optionally add to 'credit-spent'."""
    manager = BudgetManager(db_dir)
    manager.spend(boxname, amount, use_credit)
    manager.dump_data()
    typer.echo(f"Spent {amount} from '{boxname}'. New balance: {manager.balances.get(boxname, 0)}")
    if use_credit:
        typer.echo(f"Added {amount} to 'credit-spent'.")


@app.command()
def add_to_balance(
    boxname: str = typer.Argument(..., help="Balance to add to"),
    amount: int = typer.Argument(..., help="Amount to add"),
    db_dir: str = typer.Option('.', '--db-dir', help="Path to the database directory")
):
    """Increase a balance by amount, decreasing 'free' by the same amount."""
    manager = BudgetManager(db_dir)
    manager.add_to_balance(boxname, amount)
    manager.dump_data()
    typer.echo(f"Added {amount} to '{boxname}'. New balance: {manager.balances[boxname]}")


@app.command()
def transfer_between_balances(
    from_box: str = typer.Argument(..., help="Source balance"),
    to_box: str = typer.Argument(..., help="Destination balance"),
    amount: int = typer.Argument(..., help="Amount to transfer"),
    db_dir: str = typer.Option('.', '--db-dir', help="Path to the database directory")
):
    """Transfer amount from one balance to another."""
    manager = BudgetManager(db_dir)
    manager.transfer_between_balances(from_box, to_box, amount)
    manager.dump_data()
    typer.echo(f"Transferred {amount} from '{from_box}' to '{to_box}'.")


@app.command()
def new_box(
    boxname: str = typer.Argument(..., help="Name of new balance"),
    db_dir: str = typer.Option('.', '--db-dir', help="Path to the database directory")
):
    """Create a new balance with the given name and zero value."""
    manager = BudgetManager(db_dir)
    manager.new_box(boxname)
    manager.dump_data()
    typer.echo(f"Created new balance '{boxname}'.")


@app.command()
def remove_box(
    boxname: str = typer.Argument(..., help="Name of balance to remove"),
    db_dir: str = typer.Option('.', '--db-dir', help="Path to the database directory")
):
    """Remove a balance and transfer its amount to 'free'. Also remove related targets and recurring entries."""
    manager = BudgetManager(db_dir)
    manager.remove_box(boxname)
    manager.dump_data()
    typer.echo(f"Removed balance '{boxname}'.")


@app.command()
def new_loan(
    amount: int = typer.Argument(..., help="Loan amount (negative in self-loan)"),
    due: str = typer.Argument(..., help="Due date (YYYY-MM)"),
    db_dir: str = typer.Option('.', '--db-dir', help="Path to the database directory")
):
    """Create a self-loan balance with a negative amount and a target to repay by due date."""
    manager = BudgetManager(db_dir)
    manager.new_loan(amount, due)
    manager.dump_data()
    typer.echo(f"Created self-loan of {amount} due {due}.")


@app.command()
def set_target(
    boxname: str = typer.Argument(..., help="Balance to set target for"),
    goal: int = typer.Argument(..., help="Target amount"),
    due: str = typer.Argument(..., help="Due date (YYYY-MM)"),
    db_dir: str = typer.Option('.', '--db-dir', help="Path to the database directory")
):
    """Set a target amount and due date for a balance."""
    manager = BudgetManager(db_dir)
    manager.set_target(boxname, goal, due)
    manager.dump_data()
    typer.echo(f"Set target for '{boxname}': {goal} by {due}.")

if __name__ == "__main__":
    app()
