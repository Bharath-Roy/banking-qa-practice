# Requirements

The test cases use these four stories and rules.

## US-1 Login

As a customer I want to log in with my username and password so that I can see my accounts.

- Valid username and password opens the account summary.
- Wrong username or wrong password gives the same message, "Invalid username or password".
- Both fields are required.
- Passwords are case sensitive.
- 3 wrong passwords in a row lock the account. A locked account cannot log in even with the right password.
- A successful login clears the count of wrong attempts.

## US-2 Account summary

As a customer I want to see my accounts and balances.

- Shows every account of the logged in customer, with account number, type and balance.
- Never shows another customer's account.
- Balance has 2 decimals.
- Balance is up to date after a transfer.

## US-3 Fund transfer

As a customer I want to move money from my account to another account.

- Amount is between 1.00 and 50000.00, both included, with at most 2 decimals.
- Source account must be one of my own accounts.
- Destination must exist and must not be the same as the source.
- Amount cannot be more than the balance.
- A savings account must keep at least 500.00 after the transfer. Exactly 500.00 is fine. Current accounts can go to zero.
- Remark is optional, up to 50 characters, and can contain any character.
- On success the source is debited, the destination is credited, and both accounts get a transaction entry with the same reference number.
- On failure no balance changes and nothing is saved.

## US-4 Transaction history

As a customer I want to see what happened in my account.

- Newest transaction first.
- Each entry shows date, description, type (CREDIT or DEBIT), amount and the balance after it.
- Default 10 entries. The limit can be 1 to 50.
- Can be filtered by type.
- Only my own accounts can be viewed.

## Not covered

No real payments, no other banks, no OTP, no beneficiary list, no password reset, no daily limit. Session timeout is not implemented either, so it is not tested.

## Test data

| Username | Password | Accounts |
| --- | --- | --- |
| asha | Asha@1234 | 5010000101 savings 25000.00, 5010000102 current 80000.00 |
| ravi | Ravi@1234 | 5010000201 savings 10000.00 |
| kiran | Kiran@1234 | 5010000301 savings 5000.00 (used for the lockout test) |

`POST /api/dev/reset` restores these users and opening balances.
