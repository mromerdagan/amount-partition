from datetime import datetime
from .models import Target, PeriodicDeposit

def extract_lines(raw: str) -> list[str]:
    """Extracts non-empty, non-comment lines from a raw string."""
    lines = raw.split('\n')
    lines = [l.split('#')[0] for l in lines]  # remove comments
    lines = [l.strip() for l in lines]
    lines = [l for l in lines if l]  # remove empty lines
    return lines


def parse_target_line(line: str) -> tuple[str, Target]:
    """Parse a line from the goals file into (boxname, Target)."""
    boxname, goal, due = line.split()
    goal = int(goal)
    due = datetime.strptime(due, '%Y-%m')
    return boxname, Target(goal=goal, due=due)


def parse_periodic_line(line: str) -> tuple[str, PeriodicDeposit]:
    """Parse a line from the periodic file into (boxname, PeriodicDeposit)."""
    parts = line.split()
    if len(parts) == 3:
        boxname, p, target = parts
    elif len(parts) == 2:
        boxname, p = parts
        target = 0
    else:
        raise ValueError(f"Malformed line in periodic file: '{line}'. Expected format: '<boxname> <amount> <target>' or '<boxname> <amount>'")
    return boxname, PeriodicDeposit(int(p), int(target))


def parse_balance_line(line: str) -> tuple[str, int]:
    """Parse a line from the partition file into (boxname, amount)."""
    boxname, size = line.split()
    return boxname, int(size)
