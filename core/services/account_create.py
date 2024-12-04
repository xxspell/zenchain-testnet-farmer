import csv
import asyncio
import os
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError

from core.database.connect import AsyncSessionLocal
from core.database.models import Account
from core.utils.log import xlogger
from core.utils.w3.address import get_address_from_private_key


class AccountCreationResult:
    def __init__(self):
        self.total_accounts = 0
        self.added_accounts = 0
        self.skipped_accounts = 0
        self.duplicates = 0
        self.errors = []
        self.skipped_details = []


async def create_accounts(account_data_file: str, proxy_file: str) -> AccountCreationResult:
    result = AccountCreationResult()

    try:
        proxies = []
        if proxy_file and os.path.exists(proxy_file):
            with open(proxy_file, 'r') as f:
                proxies = [line.strip() for line in f if line.strip()]

        async with AsyncSessionLocal() as session:
            proxy_index = 0


            with open(account_data_file, 'r') as csvfile:
                reader = csv.reader(csvfile, delimiter='|')

                for row in reader:

                    result.total_accounts += 1
                    xlogger.log_prefix_var.set(f"Add account {result.total_accounts} | ")

                    if len(row) < 2:
                        result.skipped_accounts += 1
                        result.skipped_details.append(f"Invalid row format: {row}")
                        continue


                    email, private_key = row[0].strip(), row[1].strip()

                    if email == "email" and private_key == "privatekey":
                        result.total_accounts -= 1
                        continue

                    try:

                        address = get_address_from_private_key(private_key)

                        if not address:
                            result.skipped_accounts += 1
                            result.skipped_details.append(f"Invalid private key for {email}")
                            continue


                        existing_account = await session.execute(
                            select(Account).filter(
                                (Account.email == email) |
                                (Account.private_key == private_key) |
                                (Account.address == address)
                            )
                        )
                        existing_account = existing_account.scalar_one_or_none()

                        if existing_account:

                            if existing_account.email == email and existing_account.private_key != private_key:
                                result.duplicates += 1
                                result.skipped_details.append(
                                    f"Duplicate email {email}. Existing private key differs."
                                )
                                result.skipped_accounts += 1
                                continue

                            if existing_account.private_key == private_key:

                                result.duplicates += 1
                                result.skipped_details.append(
                                    f"Account {email} already exists."
                                )
                                result.skipped_accounts += 1
                                continue

                        proxy = proxies[proxy_index] if proxies and proxy_index < len(proxies) else None

                        new_account = Account(
                            email=email,
                            private_key=private_key,
                            proxy=proxy,
                            active=True,
                            address=address
                        )

                        session.add(new_account)

                        proxy_index = (proxy_index + 1) % len(proxies) if proxies else 0

                        result.added_accounts += 1

                    except Exception as account_error:
                        result.errors.append(f"Error processing {email}: {str(account_error)}")
                        result.skipped_accounts += 1

                await session.commit()

    except FileNotFoundError:
        result.errors.append(f"File not found: {account_data_file} or {proxy_file}")
    except Exception as e:
        result.errors.append(f"Unexpected error: {str(e)}")

    return result


def print_account_creation_report(result: AccountCreationResult):
    print("\n--- Account Creation Report ---")
    print(f"Total accounts processed: {result.total_accounts}")
    print(f"Successfully added: {result.added_accounts}")
    print(f"Skipped accounts: {result.skipped_accounts}")
    print(f"Duplicate accounts: {result.duplicates}")

    if result.skipped_details:
        print("\nSkipped Account Details:")
        for detail in result.skipped_details:
            print(f"  - {detail}")

    if result.errors:
        print("\nErrors:")
        for error in result.errors:
            print(f"  - {error}")