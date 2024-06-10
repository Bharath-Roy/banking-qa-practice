# Test scenarios

Coverage notes for `test-cases.csv`. Case numbers below belong to the module shown unless a full id is given.

## Login (US-1)

Valid login is TC-LGN-01. Cases 02, 03 and 07 try a wrong password, an unknown user and the wrong password case. Case 04 leaves the fields empty.

The lockout checks are separate: 05 tries 3 wrong passwords in a row; 06 puts a successful login between wrong attempts to check that the count resets. Case 08 checks missing and invalid tokens.

## Account summary (US-2)

TC-ACC-01 and 03 check the accounts, balances and 2 decimal places. TC-ACC-02 checks that ravi cannot see asha's accounts. TC-DB-04 compares the screen balance with the database.

## Fund transfer (US-3)

This has the most cases because of the amount and balance rules:

- TC-TRF-01: transfer to another customer and check both balances.
- 02 to 05: 0.99, 1.00, 50000.00 and 50000.01, around the two amount limits.
- 06 to 10: zero, negative, text, 3 decimals and an empty amount.
- 11 to 13: same account, unknown destination and someone else's source account.
- 14 to 16: insufficient funds, below the savings minimum, and exactly 500.00 left.
- 17 to 19: remarks at 50 and 51 characters, plus special characters.
- 20: move money between asha's own accounts and look for the credit entry.
- 21: compare balances after a rejected transfer. TC-DB-03 also checks for negative balances and savings below 500.00.
- 22 to 24: no login, a missing field and broken JSON.
- 25: check the insufficient balance message on screen.

## Transaction history (US-4)

TC-HIS-01 to 04 and 07 cover the row order, entry details, type filter and limits. Cases 05 and 06 try another customer's account and an account that does not exist. Case 08 matches the receiver's credit reference with the sender's transfer.

## Data checks

Run Q1 for balance against the transaction ledger (TC-DB-01), Q2 for a debit and credit per transfer (TC-DB-02), and Q3 for negative balances or savings below 500.00 (TC-DB-03). Q4 is the screen comparison mentioned above. Q5 helps inspect the latest ten entries for an account.

## Regression

After the fixes in build 1.1 the whole list was run again, not only the cases that had failed. See `test-summary.md`.
