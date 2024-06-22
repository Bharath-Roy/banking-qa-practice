# API testing notes

Base URL: `http://127.0.0.1:5050`. Requests and responses use JSON. Accounts, transfers and history need `Authorization: Bearer <token>`. Login, health and the test-data reset do not need a token.

| Method | Path | Success | What it does |
| --- | --- | --- | --- |
| POST | /api/login | 200 | returns a token and the user's name |
| GET | /api/accounts | 200 | accounts and balances of the logged in customer |
| GET | /api/accounts/{no}/transactions?type=&limit= | 200 | history, newest first |
| POST | /api/transfers | 201 | moves money, returns the reference |
| POST | /api/dev/reset | 200 | resets the test data |
| GET | /api/health | 200 | status and build number |

Validation and login errors return `{"error": "text", "code": "SOMETHING"}`. Tests check the code and sometimes the message. An unexpected server error returns 500 with just `{"error": "Internal server error"}`.

| Status | When |
| --- | --- |
| 400 | bad or missing input (INVALID_AMOUNT, AMOUNT_TOO_LOW, AMOUNT_TOO_HIGH, MISSING_FIELDS, BAD_JSON, REMARK_TOO_LONG, SAME_ACCOUNT, INSUFFICIENT_FUNDS, MIN_BALANCE, INVALID_LIMIT, INVALID_TYPE) |
| 401 | no token, bad token, wrong username or password |
| 403 | transfer from an account that is not yours |
| 404 | account does not exist, or (history) is not yours |
| 423 | account locked |

Amounts go in as a string like `"1500.00"` and come back as strings with 2 decimals.

## Running the collection in Postman

1. Start the app (`python3 app/bank.py`).
2. Import `postman/practice-bank.postman_collection.json` and `postman/practice-bank-local.postman_environment.json`.
3. Select the environment "Practice Bank local" and run the collection (Runner, run all, in order).

Run all folders in order. Setup resets the data once and saves the login tokens. Later requests use the balances left by earlier transfers, so running one request on its own can give a different result. The four transfer requests for known defects are last in that folder, after the other balance checks.

Without Postman: `npx newman run postman/practice-bank.postman_collection.json -e postman/practice-bank-local.postman_environment.json`

## What each request checks

All 58 requests check the status code. Most error requests also check `code`. The other checks cover user details, account balances, references (`TXN` and 8 hex characters), amounts with 2 decimals, and history order, filters and limits. There are 106 assertions in total.

## Results on each build

Start one build at a time. Stop it before starting the other on the same port.

```sh
python3 app/bank.py                  # build 1.0
BANK_BUILD=1.1 python3 app/bank.py   # build 1.1
```

On 1.0, 10 assertions fail, in the requests for TC-LGN-06, TC-TRF-09, 16, 19, 20, TC-HIS-01 and TC-HIS-05. On 1.1 they all pass.
