import pathlib
from collections import OrderedDict
from datetime import datetime
from .models import Balance, BalanceFactory, Target, PeriodicDeposit

def extract_lines(raw: str) -> list[str]:
    """Extracts non-empty, non-comment lines from a raw string."""
    lines = raw.split('\n')
    lines = [l.split('#')[0] for l in lines]  # remove comments
    lines = [l.strip() for l in lines]
    lines = [l for l in lines if l]  # remove empty lines
    return lines

def parse_balance_line(line: str) -> tuple[str, Balance]:
    """
    Parse a line from the partition file into (boxname, Balance).

    - If the line has two columns, assume type_ is 'regular'.
    - Otherwise, take type_ from the third column and validate.
    """
    allowed_types = {"credit", "free", "virtual", "instalment", "regular"}

    parts = line.split()
    num_parts = len(parts)
    if num_parts < 2:
        raise ValueError(f"Malformed line in partition file: '{line}'. Expected at least 2 columns.")

    if num_parts == 2:  # Support legacy format without type_
        boxname, amount = parts
        if boxname == "free":
            type_ = "free"
        elif boxname == "credit-spent":
            type_ = "credit"
        else:
            type_ = "regular"
        extra_args = []
        
    else:  # num_parts >= 3
        boxname, amount, type_, *extra_args = parts
        if type_ not in allowed_types:
            raise ValueError(
                f"Invalid type '{type_}' in line {line!r}. "
                f"Allowed types: {', '.join(sorted(allowed_types))}"
            )
    
    balance = BalanceFactory.create_balance(int(amount), type_, *extra_args)

    return boxname, balance


def parse_balances_file(partition_path: pathlib.Path) -> dict[str, Balance]:
    """Parse a balances file into a dictionary of boxname to Balance."""
    raw = partition_path.read_text()
    lines = extract_lines(raw)
    balances = OrderedDict()
    for line in lines:
        boxname, balance = parse_balance_line(line)
        balances[boxname] = balance
    return balances

def parse_target_line(line: str) -> tuple[str, Target]:
    """Parse a line from the goals file into (boxname, Target)."""
    boxname, goal, due = line.split()
    goal = int(goal)
    due = datetime.strptime(due, '%Y-%m')
    return boxname, Target(goal=goal, due=due)

def parse_targets_file(targets_path: pathlib.Path) -> dict[str, Target]:
    if not targets_path.exists():
        return OrderedDict()
    raw = targets_path.read_text()
    lines = extract_lines(raw)
    targets = OrderedDict()
    for line in lines:
        boxname, target = parse_target_line(line)
        targets[boxname] = target
    return targets

def parse_recurring_line(line: str) -> tuple[str, PeriodicDeposit]:
    """Parse a line from the periodic file into (boxname, PeriodicDeposit)."""
    parts = line.split()
    if len(parts) == 3:
        boxname, amount, target = parts
    elif len(parts) == 2:
        boxname, amount = parts
        target = 0
    else:
        raise ValueError(f"Malformed line in periodic file: '{line}'. Expected format: '<boxname> <amount> <target>' or '<boxname> <amount>'")
    return boxname, PeriodicDeposit(int(amount), int(target))

def parse_recurring_file(recurring_path: pathlib.Path) -> dict[str, PeriodicDeposit]:
    if not recurring_path.exists():
        return OrderedDict()
    raw = recurring_path.read_text()
    lines = extract_lines(raw)
    recurring = OrderedDict()
    for line in lines:
        boxname, periodic = parse_recurring_line(line)
        recurring[boxname] = periodic
    return recurring

def dump_balances_file(partition_path: pathlib.Path, balances: dict[str, Balance]) -> None:
    """Write the balances dict to the partition file."""
    lines = [f"{balance_name:<20}" + "".join("{:<20}".format(c) for c in balance.as_list()) for
             balance_name, balance in balances.items()]
    lines = [l.strip() for l in lines]  # remove trailing spaces
    content = "\n".join(lines) + "\n"
    partition_path.write_text(content)


def dump_targets_file(targets_path: pathlib.Path, targets: dict[str, Target]) -> None:
    """Write the targets dict to the goals file."""
    lines = [
        f"{boxname:<20} {target.goal:<20} {target.due.strftime('%Y-%m')}"
        for boxname, target in targets.items()
    ]
    content = "\n".join(lines) + "\n"
    targets_path.write_text(content)


def dump_recurring_file(recurring_path: pathlib.Path, recurring: dict[str, PeriodicDeposit]) -> None:
    """Write the recurring dict to the periodic file."""
    lines = []
    for boxname, periodic in recurring.items():
        lines.append(f"{boxname:<20} {periodic.amount:<20} {periodic.target}")
    content = "\n".join(lines) + "\n"
    recurring_path.write_text(content)
