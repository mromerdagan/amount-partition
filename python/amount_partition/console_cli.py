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

if __name__ == "__main__":
    app()
