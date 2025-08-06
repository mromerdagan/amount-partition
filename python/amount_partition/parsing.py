import pathlib
from collections import OrderedDict
from datetime import datetime
from .models import Target, PeriodicDeposit

def extract_lines(raw: str) -> list[str]:
    """Extracts non-empty, non-comment lines from a raw string."""
    lines = raw.split('\n')
    lines = [l.split('#')[0] for l in lines]  # remove comments
    lines = [l.strip() for l in lines]
    lines = [l for l in lines if l]  # remove empty lines
    return lines

def parse_balance_line(line: str) -> tuple[str, int]:
    """Parse a line from the partition file into (boxname, amount)."""
    boxname, size = line.split()
    return boxname, int(size)

def parse_balances_file(partition_path: pathlib.Path) -> dict[str, int]:
    """Parse a balances file into a dictionary of boxname to amount."""
    raw = partition_path.read_text()
    lines = extract_lines(raw)
    balances = OrderedDict()
    for line in lines:
        boxname, amount = parse_balance_line(line)
        balances[boxname] = amount
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
        boxname, monthly, target = parts
    elif len(parts) == 2:
        boxname, monthly = parts
        target = 0
    else:
        raise ValueError(f"Malformed line in periodic file: '{line}'. Expected format: '<boxname> <amount> <target>' or '<boxname> <amount>'")
    return boxname, PeriodicDeposit(int(monthly), int(target))

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