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
