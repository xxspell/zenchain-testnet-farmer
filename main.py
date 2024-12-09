import asyncio
import os
import sys

from core.jobs import main_loop
from core.services.account_create import create_accounts, print_account_creation_report
from core.utils.art import ascii_art


def welcome_message():
    ascii_art()
    print("Welcome to the farming zenchain testnet")
    print("Select an option from the menu below:")
    print("1. Add accounts to database")
    print("2. Start farming")
    print("3. Export to CSV")
    print("4. View statistic")
    print("5. Exit")


def create_accounts_interactive(account_data_file: str = None, proxy_file: str = None):
    account_data_file = input("Enter path to accounts data file (CSV): ")
    proxy_file = input("Enter path to proxy file: ")

    if not os.path.exists(account_data_file):
        print(f"Error: Account data file {account_data_file} does not exist.")
        return

    if not os.path.exists(proxy_file):
        print(f"Error: Proxy file {proxy_file} does not exist.")
        return

    result = asyncio.run(create_accounts(account_data_file, proxy_file))
    print_account_creation_report(result)



def start_farming():
    try:
        asyncio.run(main_loop())
    except Exception as e:
        print(f"An error occurred during export: {str(e)}")
        return False
    return True



def export_to_csv():
    try:
        print("Soon")
    except Exception as e:
        print(f"An error occurred during export: {str(e)}")
        return False
    return True



def view_statistics():
    try:
        print("Soon")
    except Exception as e:
        print(f"An error occurred during export: {str(e)}")
        return False
    return True


def exit_cli():
    print("Exiting...")
    sys.exit()




def display_menu():
    welcome_message()
    choice = input("Enter the number of your choice: ")
    if choice == "1":
        create_accounts_interactive()
    elif choice == "2":
        start_farming()
    elif choice == "3":
        export_to_csv()
    elif choice == "4":
        view_statistics()
    elif choice == "5":
        exit_cli()
    else:
        print("Invalid option. Please try again.")
        display_menu()


def main():
    display_menu()

if __name__ == "__main__":
    if sys.platform.lower() == "win32" or os.name.lower() == "nt":
        from asyncio import set_event_loop_policy, WindowsSelectorEventLoopPolicy

        set_event_loop_policy(WindowsSelectorEventLoopPolicy())
    main()
