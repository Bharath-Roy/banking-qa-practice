# Defect log

Seven defects in build 1.0. All are closed after retesting on 1.1. The full regression also passed; see `test-summary.md`. BANK-1 to BANK-7 are local defect ids. The CSV has not been imported into Jira.

| ID | Summary | Severity | Priority | Found by | Status |
| --- | --- | --- | --- | --- | --- |
| BANK-1 | Failed login count is not cleared after a successful login | Major | High | TC-LGN-06 | Closed (verified on 1.1) |
| BANK-2 | Amount with 3 decimals is accepted and silently cut to 2 | Major | Medium | TC-TRF-09 | Closed (verified on 1.1) |
| BANK-3 | Savings transfer that leaves exactly 500.00 is rejected | Minor | Low | TC-TRF-16 | Closed (verified on 1.1) |
| BANK-4 | Transfer fails with a 500 when the remark has an apostrophe | Major | Medium | TC-TRF-19 | Closed (verified on 1.1) |
| BANK-5 | Transfer between own accounts has no credit entry in the history | Major | High | TC-TRF-20, TC-DB-01, TC-DB-02 | Closed (verified on 1.1) |
| BANK-6 | Transaction history is oldest first | Major | Medium | TC-HIS-01 | Closed (verified on 1.1) |
| BANK-7 | Any logged in customer can read another customer's transaction history | Critical | High | TC-HIS-05 | Closed (verified on 1.1) |

## BANK-1 Failed login count is not cleared after a successful login

Steps
1. Reset data.
2. Login as ravi with a wrong password, twice.
3. Login as ravi with the correct password. It works.
4. Login with a wrong password once more.
5. Login with the correct password.

Expected: step 5 returns 200. There has only been 1 wrong attempt since the successful login.
Actual: 423 ACCOUNT_LOCKED. The wrong attempts are counted together (2 + 1 = 3) even though a good login happened in between.

This locks the customer out even though the wrong attempts were not consecutive.

## BANK-2 Amount with 3 decimals is accepted and cut to 2

Steps
1. Login as asha.
2. Transfer 100.999 from 5010000101 to 5010000201.

Expected: 400 INVALID_AMOUNT, no money moves.
Actual: 201 SUCCESS. It debits 100.99 instead of rejecting 100.999; the balance goes from 25000.00 to 24899.01.

## BANK-3 Savings transfer leaving exactly 500.00 is rejected

Steps
1. Login as ravi (savings balance 10000.00).
2. Transfer 9500.00 to 5010000101.

Expected: 201 with 500.00 left, which is allowed by the minimum balance rule.
Actual: 400 MIN_BALANCE, balance stays 10000.00.

Boundary value case. 9500.01 is correctly rejected, so only the boundary itself is wrong.

## BANK-4 Transfer fails with a 500 when the remark has an apostrophe

Steps
1. Login as asha.
2. Transfer 10 from 5010000101 to 5010000201 with remark `Ravi's rent & deposit`.

Expected: 201.
Actual: 500 {"error": "Internal server error"}. Balances and the transaction table are unchanged afterwards (checked in the database), so no money was lost, but the transfer cannot be made.

The apostrophe appears to break the SQL statement. Nothing beyond this remark was tried, so this test does not establish whether other input could exploit it.

## BANK-5 Transfer between own accounts has no credit entry

Steps
1. Login as asha.
2. Transfer 2000 from savings 5010000101 to current 5010000102. It succeeds.
3. Open the history of 5010000102 (or call `GET /api/accounts/5010000102/transactions?type=CREDIT`).

Expected: a credit entry "Transfer from 5010000101" for 2000.00.
Actual: no entry. The balance of the current account did go up by 2000, so the balance and the history no longer agree.

Database check after a few transfers on 1.0:
- Q1 returned both of asha's accounts, e.g. 5010000101 balance 2255025 paise but ledger 2180025.
- Q2 returned the transfers with 1 debit row and 0 credit rows.

Transfers to a different customer are fine, only own-account transfers are affected.

## BANK-6 Transaction history is oldest first

Steps
1. Login as asha and transfer 100 to ravi.
2. In Transaction history choose 5010000101 and click Show.

Expected: the 100.00 transfer is on top, opening balance at the bottom.
Actual: "Opening balance" is the first row and the new transfer is at the bottom.

It gets worse with the limit. The screen asks for 20 rows, so once an account has more than 20 entries the newest ones are never shown at all.

## BANK-7 Another customer's transaction history can be read

Steps
1. Login as ravi and keep the token.
2. `GET /api/accounts/5010000101/transactions` with ravi's token (5010000101 is asha's account).

Expected: 404, the same as an account that does not exist.
Actual: 200 with asha's transactions (amounts, balances, descriptions).

Account summary and transfer are protected (TC-ACC-02, TC-TRF-13). Only the history endpoint was missing the owner check.
