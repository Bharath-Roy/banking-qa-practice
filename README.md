# Banking application testing (practice project)

This project covers login, account summary, fund transfer and transaction history in a small net banking app. The tests include screen checks, API requests in Postman and SQL queries.

The app was built for practice. Build 1.0 has seven defects left in on purpose; build 1.1 fixes them. The test cases record the first run, retesting and regression. This is not a real bank or client work.

## Run the app

Needs Python 3 (tried on 3.14), nothing to install.

```sh
python3 app/bank.py                  # build 1.0, with the defects
BANK_BUILD=1.1 python3 app/bank.py   # build 1.1, defects fixed
```

Open http://127.0.0.1:5050. Logins:

| Username | Password |
| --- | --- |
| asha | Asha@1234 |
| ravi | Ravi@1234 |
| kiran | Kiran@1234 |

The data is in `.data/bank.db`. `POST /api/dev/reset` or deleting the file gets back to the starting data. Port can be changed with `PORT=5051`.

## Test files

Start with `docs/requirements.md` and `docs/test-scenarios.md` for the rules and coverage. `docs/test-cases.csv` has the 48 cases and results for both builds.

The seven defects are in `docs/defect-log.md`, with a CSV prepared for Jira import in `docs/jira-import.csv`. Results and gaps are in `docs/test-summary.md`.

`docs/api-testing.md` explains the endpoints and how to run the collection in `postman/`. The database queries are in `sql/validation-queries.sql`.

## Quick run

```sh
python3 app/bank.py &
npx newman run postman/practice-bank.postman_collection.json -e postman/practice-bank-local.postman_environment.json
sqlite3 -header .data/bank.db < sql/validation-queries.sql
```

On build 1.0, newman shows 10 failed assertions and the SQL file returns rows for Q1 and Q2 (once some transfers have been made). On 1.1 nothing fails and Q1 to Q3 return no rows.

## Results

48 cases. Build 1.0: 39 passed, 9 failed (7 defects, 1 critical, 5 major, 1 minor). Build 1.1: 48 passed. More in `docs/test-summary.md`.

## Limits

- The SQL was run on SQLite. It is plain SQL and should work on MySQL, but that is untested.
- Jira: the defects are in `docs/jira-import.csv` but have not been imported anywhere.
- No concurrency, load or browser compatibility testing.
