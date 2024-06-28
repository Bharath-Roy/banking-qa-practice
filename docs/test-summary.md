# Test summary

Practice bank app, builds 1.0 and 1.1. Run on 2026-10-01.

## What was tested

Login, account summary, fund transfer and transaction history, using the four stories in `requirements.md`.

48 test cases in `test-cases.csv`: 30 negative and 18 positive. By test area, that is 7 UI cases in Chromium, 37 API cases and 4 SQL cases.

The 7 UI cases are the 5 marked UI plus TC-TRF-01 and TC-HIS-01, which were also checked through the API. TC-DB-04 compares the screen with the database.

## Environment

- Linux, Python 3.14, app started with `python3 app/bank.py` (SQLite file in `.data/`)
- Chromium for the UI cases
- Postman collection run with newman 6.2.2. 58 requests, 106 assertions
- sqlite3 for the SQL checks
- Individual cases use reset data. The Postman collection resets once at the start, then runs the requests in order with shared balances.

## Results

| Module | Cases | Build 1.0 passed | Build 1.1 passed |
| --- | --- | --- | --- |
| Login | 8 | 7 | 8 |
| Account summary | 3 | 3 | 3 |
| Fund transfer | 25 | 21 | 25 |
| Transaction history | 8 | 6 | 8 |
| Database | 4 | 2 | 4 |
| Total | 48 | 39 | 48 |

Build 1.0: 9 cases failed, which came down to 7 defects (TC-TRF-20, TC-DB-01 and TC-DB-02 are the same one).

Severity: 1 critical, 5 major and 1 minor. Steps and actual results are in `defect-log.md`.

Postman: 10 of 106 assertions failed on 1.0, all related to those seven defects. All 106 passed on 1.1.

## Regression

All 48 cases were run again on 1.1 and passed, including the 9 failures from 1.0. All 7 defects are closed after retesting.

Use the Postman collection for the API part of regression. Its requests share data, so some amounts and accounts differ from the individual CSV cases. It does not replace the screen checks or Q1 to Q5. There are no separate requests named TC-ACC-03 or TC-HIS-03; balance formatting and credit history are checked within other requests.

## Story to case

| Story | Cases |
| --- | --- |
| US-1 Login | TC-LGN-01 to 08 |
| US-2 Account summary | TC-ACC-01 to 03, TC-DB-04 |
| US-3 Fund transfer | TC-TRF-01 to 25, TC-DB-01 to 03 |
| US-4 Transaction history | TC-HIS-01 to 08 |

## Not covered

- Only Chromium, no phone or other browsers, and nothing on layout or accessibility.
- No load or performance testing.
- Security checks covered tokens and account ownership only. No wider security testing.
- The SQL checks were not run on MySQL.
- Concurrent transfers on the same account were not tested. This would be the next check to add.
- Session expiry is not part of the app.
