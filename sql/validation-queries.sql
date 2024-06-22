-- Database checks. Table definitions are in app/bank.py.
-- Amounts are stored in paise, so 25000.00 is 2500000.
-- Run: sqlite3 -header .data/bank.db < sql/validation-queries.sql
-- Tested on SQLite only. The queries use plain joins, CASE and GROUP BY;
-- MySQL has not been checked.


-- Q1  Balance vs credits minus debits (TC-DB-01). No rows means they match.
SELECT a.account_no,
       a.balance_paise AS balance,
       COALESCE(SUM(CASE WHEN t.txn_type = 'CREDIT' THEN t.amount_paise ELSE -t.amount_paise END), 0) AS ledger
FROM accounts a
LEFT JOIN transactions t ON t.account_id = a.id
GROUP BY a.id, a.account_no, a.balance_paise
HAVING a.balance_paise <> COALESCE(SUM(CASE WHEN t.txn_type = 'CREDIT' THEN t.amount_paise ELSE -t.amount_paise END), 0);


-- Q2  Transfers missing a debit or credit, or having extra rows (TC-DB-02).
-- Should return no rows: each transfer needs exactly one of each.
SELECT tr.reference,
       SUM(CASE WHEN t.txn_type = 'DEBIT' THEN 1 ELSE 0 END)  AS debit_rows,
       SUM(CASE WHEN t.txn_type = 'CREDIT' THEN 1 ELSE 0 END) AS credit_rows
FROM transfers tr
LEFT JOIN transactions t ON t.reference = tr.reference
GROUP BY tr.reference
HAVING SUM(CASE WHEN t.txn_type = 'DEBIT' THEN 1 ELSE 0 END) <> 1
    OR SUM(CASE WHEN t.txn_type = 'CREDIT' THEN 1 ELSE 0 END) <> 1;


-- Q3  Negative balances or savings below 500.00 (TC-DB-03). Expect no rows.
SELECT account_no, account_type, balance_paise
FROM accounts
WHERE balance_paise < 0
   OR (account_type = 'SAVINGS' AND balance_paise < 50000);


-- Q4  Compare these balances with the account summary screen (TC-DB-04).
SELECT u.username, a.account_no, a.account_type, a.balance_paise / 100.0 AS balance
FROM accounts a
JOIN users u ON u.id = a.user_id
ORDER BY a.id;


-- Q5  Last ten entries for one account. Change the account number as needed.
SELECT t.id, t.created_at, t.txn_type, t.amount_paise, t.balance_after_paise, t.description, t.reference
FROM transactions t
JOIN accounts a ON a.id = t.account_id
WHERE a.account_no = '5010000101'
ORDER BY t.id DESC
LIMIT 10;
