import json
import typer
from amount_partition.api import BudgetManagerApi

def print_balances(balances, total):
    print('Balances:')
    print('=========')
    for name, amount in balances.items():
        print(f'{name:<20} {amount}')
    print(f'\nTotal: {total}\n')

def print_targets(targets):
    print('Targets:')
    print('========')
    for name, target in targets.items():
        print(f'{name:<20} {target.goal:<10} {target.due.strftime("%Y-%m"):<15}')
    print()

def print_recurring(recurring):
    print('Recurring deposits:')
    print('===================')
    for name, periodic in recurring.items():
        print(f'{name:<20} {periodic.amount:<10} {periodic.target:<15}')
    print()

def print_summary(balances, targets, recurring, total):
    print_balances(balances, total)
    print_targets(targets)
    print_recurring(recurring)

app = typer.Typer()

@app.command()
def summary(db_dir: str = typer.Option('.', '--db-dir', help="Path to the database directory")):
    """Show a summary of balances, targets, and recurring deposits."""
    manager = BudgetManagerApi.from_storage(db_dir)
    print_summary(
        balances=manager.balances,
        targets=manager._targets,
        recurring=manager._recurring,
        total=manager.total.amount
    )


@app.command()
def deposit(
    amount: int = typer.Argument(..., help="Amount to deposit into 'free' balance"),
    db_dir: str = typer.Option('.', '--db-dir', help="Path to the database directory"),
    monthly: bool = typer.Option(True, help="Merge 'credit-spent' into 'free' on deposit")
):
    """Deposit an amount into the 'free' balance. Optionally merge 'credit-spent'."""
    manager = BudgetManagerApi.from_storage(db_dir)
    manager.deposit(amount, monthly=monthly)
    manager.dump_data(db_dir)
    typer.echo(f"Deposited {amount} into 'free'. New 'free' balance: {manager.balances['free'].amount}")
    if monthly:
        typer.echo(f"'credit-spent' merged into 'free'.")


@app.command()
def withdraw(
    amount: int = typer.Argument(0, help="Amount to withdraw from 'free' balance (0 empties 'free')"),
    db_dir: str = typer.Option('.', '--db-dir', help="Path to the database directory")
):
    """Withdraw an amount from 'free'. If amount is 0, empty 'free'."""
    manager = BudgetManagerApi.from_storage(db_dir)
    manager.withdraw(amount)
    manager.dump_data(db_dir)
    typer.echo(f"Withdrew {amount} from 'free'. New 'free' balance: {manager.balances['free'].amount}")


@app.command()
def spend(
    boxname: str = typer.Argument(..., help="Box to spend from"),
    amount: int = typer.Argument(0, help="Amount to spend (0 empties box)"),
    use_cash: bool = typer.Option(False, help="Don't add to credit-spent"),
    db_dir: str = typer.Option('.', '--db-dir', help="Path to the database directory")
):
    """Spend an amount from a balance. By default adds to credit-spent."""
    manager = BudgetManagerApi.from_storage(db_dir)
    manager.spend(boxname, amount, use_credit=(not use_cash))
    manager.dump_data(db_dir)
    typer.echo(f"Spent {amount} from '{boxname}'. New balance: {manager.balances[boxname].amount}")
    if not use_cash:
        typer.echo(f"Credit-spent balance: {manager.balances['credit-spent'].amount}")


@app.command()
def add_to_balance(
    boxname: str = typer.Argument(..., help="Balance to add to"),
    amount: int = typer.Argument(..., help="Amount to add"),
    db_dir: str = typer.Option('.', '--db-dir', help="Path to the database directory")
):
    """Increase a balance by amount, decreasing 'free' by the same amount."""
    manager = BudgetManagerApi.from_storage(db_dir)
    manager.add_to_balance(boxname, amount)
    manager.dump_data(db_dir)
    typer.echo(f"Added {amount} to '{boxname}'. New balance: {manager.balances[boxname].amount}")


@app.command()
def transfer_between_balances(
    from_box: str = typer.Argument(..., help="Source balance"),
    to_box: str = typer.Argument(..., help="Destination balance"),
    amount: int = typer.Argument(..., help="Amount to transfer"),
    db_dir: str = typer.Option('.', '--db-dir', help="Path to the database directory")
):
    """Transfer amount from one balance to another."""
    manager = BudgetManagerApi.from_storage(db_dir)
    manager.transfer_between_balances(from_box, to_box, amount)
    manager.dump_data(db_dir)
    typer.echo(f"Transferred {amount} from '{from_box}' to '{to_box}'.")


@app.command()
def new_box(
    boxname: str = typer.Argument(..., help="Name of new balance"),
    db_dir: str = typer.Option('.', '--db-dir', help="Path to the database directory")
):
    """Create a new balance with the given name and zero value."""
    manager = BudgetManagerApi.from_storage(db_dir)
    manager.new_box(boxname)
    manager.dump_data(db_dir)
    typer.echo(f"Created new balance '{boxname}'.")


@app.command()
def remove_box(
    boxname: str = typer.Argument(..., help="Name of balance to remove"),
    db_dir: str = typer.Option('.', '--db-dir', help="Path to the database directory")
):
    """Remove a balance and transfer its amount to 'free'. Also remove related targets and recurring entries."""
    manager = BudgetManagerApi.from_storage(db_dir)
    manager.remove_box(boxname)
    manager.dump_data(db_dir)
    typer.echo(f"Removed balance '{boxname}'.")


@app.command()
def new_loan(
    amount: int = typer.Argument(..., help="Loan amount (negative in self-loan)"),
    due: str = typer.Argument(..., help="Due date (YYYY-MM)"),
    db_dir: str = typer.Option('.', '--db-dir', help="Path to the database directory")
):
    """Create a self-loan balance with a negative amount and a target to repay by due date."""
    manager = BudgetManagerApi.from_storage(db_dir)
    manager.new_loan(amount, due)
    manager.dump_data(db_dir)
    typer.echo(f"Created self-loan of {amount} due {due}.")


@app.command()
def set_target(
    boxname: str = typer.Argument(..., help="Balance to set target for"),
    goal: int = typer.Argument(..., help="Target amount"),
    due: str = typer.Argument(..., help="Due date (YYYY-MM)"),
    db_dir: str = typer.Option('.', '--db-dir', help="Path to the database directory")
):
    """Set a target amount and due date for a balance."""
    manager = BudgetManagerApi.from_storage(db_dir)
    manager.set_target(boxname, goal, due)
    manager.dump_data(db_dir)
    typer.echo(f"Set target for '{boxname}': {goal} by {due}.")


@app.command()
def remove_target(
    boxname: str = typer.Argument(..., help="Balance to remove target from"),
    db_dir: str = typer.Option('.', '--db-dir', help="Path to the database directory")
):
    """Remove a target for the given balance."""
    manager = BudgetManagerApi.from_storage(db_dir)
    manager.remove_target(boxname)
    manager.dump_data(db_dir)
    typer.echo(f"Removed target for '{boxname}'.")


@app.command()
def set_recurring(
    boxname: str = typer.Argument(..., help="Balance to set recurring deposit for"),
    periodic_amount: int = typer.Argument(..., help="Amount for periodic deposit"),
    target: int = typer.Argument(0, help="Target amount (0 for unlimited)"),
    db_dir: str = typer.Option('.', '--db-dir', help="Path to the database directory")
):
    """Set a recurring deposit for a balance, with an optional target amount."""
    manager = BudgetManagerApi.from_storage(db_dir)
    manager.set_recurring(boxname, periodic_amount, target)
    manager.dump_data(db_dir)
    typer.echo(f"Set recurring deposit for '{boxname}': {periodic_amount} (target: {target}).")


@app.command()
def remove_recurring(
    boxname: str = typer.Argument(..., help="Balance to remove recurring deposit from"),
    db_dir: str = typer.Option('.', '--db-dir', help="Path to the database directory")
):
    """Remove a recurring deposit for the given balance."""
    manager = BudgetManagerApi.from_storage(db_dir)
    manager.remove_recurring(boxname)
    manager.dump_data(db_dir)
    typer.echo(f"Removed recurring deposit for '{boxname}'.")


@app.command()
def plan_deposits(
    skip: str = typer.Option('', '--skip', help="Comma-separated balance names to skip"),
    is_monthly: bool = typer.Option(True, '--is-monthly/--not-monthly', help="True for regular monthly deposit, False for additional deposits"),
    amount_to_use: int = typer.Option(0, '--amount', help="Amount to scale deposits plan to (0 for no normalization)"),
    db_dir: str = typer.Option('.', '--db-dir', help="Path to the database directory")
):
    """Suggest deposit amounts for each balance to meet targets and recurring deposits."""
    manager = BudgetManagerApi.from_storage(db_dir)
    deposits_plan = manager.plan_deposits(skip=skip, is_monthly=is_monthly, amount_to_use=amount_to_use)
    
    if not deposits_plan:
        typer.echo("No deposits plan available.")
        return
    
    typer.echo("Deposits plan:")
    typer.echo("===================")
    total = 0
    for boxname, amount in deposits_plan.items():
        typer.echo(f"{boxname:<20} {amount}")
        total += amount
    typer.echo(f"\nTotal planned: {total}")


@app.command()
def plan_and_apply(
    skip: str = typer.Option('', '--skip', help="Comma-separated balance names to skip"),
    is_monthly: bool = typer.Option(True, '--is-monthly/--not-monthly', help="True for regular monthly deposit, False for additional deposits"),
    amount_to_use: int = typer.Option(0, '--amount', help="Amount to scale deposits plan to (0 for no normalization)"),
    db_dir: str = typer.Option('.', '--db-dir', help="Path to the database directory")
):
    """Generate and apply deposits plan to the balances."""
    manager = BudgetManagerApi.from_storage(db_dir)
    deposits_plan = manager.plan_and_apply(skip, is_monthly, amount_to_use)

    total_applied = sum(deposits_plan.values())
    typer.echo(f"Applied deposits plan. Total: {total_applied}")
    typer.echo("Applied amounts:")
    for boxname, amount in deposits_plan.items():
        typer.echo(f"  {boxname}: +{amount}")


@app.command()
def reserved_amount(
    days_to_lock: int = typer.Argument(..., help="Number of days to consider for locking funds"),
    db_dir: str = typer.Option('.', '--db-dir', help="Path to the database directory")
):
    """Calculate reserved funds for future targets with due dates at least X days in the future."""
    manager = BudgetManagerApi.from_storage(db_dir)
    reserved = manager.reserved_amount(days_to_lock)
    typer.echo(f"Reserved amount (targets due in {days_to_lock}+ days): {reserved}")


@app.command()
def create_db(
    db_dir: str = typer.Argument(..., help="Path to the new database directory")
):
    """Create a new database at the given location."""
    try:
        BudgetManagerApi.create_db(db_dir)
        typer.echo(f"Database created at {db_dir}.")
    except Exception as e:
        typer.echo(f"Failed to create database: {e}", err=True)


@app.command()
def to_json(
    db_dir: str = typer.Option('.', '--db-dir', help="Path to the database directory"),
    output: str = typer.Option('-', '--output', help="Output file (default: stdout)")
):
    """Export the database to JSON."""
    manager = BudgetManagerApi.from_storage(db_dir)
    data = manager.to_json()
    json_str = json.dumps(data, indent=2)
    if output == '-' or not output:
        typer.echo(json_str)
    else:
        with open(output, 'w') as f:
            f.write(json_str)
        typer.echo(f"Exported database to {output}.")


@app.command()
def from_json(
    input_file: str = typer.Argument(..., help="Input JSON file"),
    db_dir: str = typer.Option('.', '--db-dir', help="Path to the database directory to import into")
):
    """Import database from a JSON file, overwriting any existing data."""
    manager = BudgetManagerApi.from_json(input_file)
    manager.dump_data(db_dir)
    typer.echo(f"Imported database from {input_file} into {db_dir}.")

if __name__ == "__main__":
    app()
