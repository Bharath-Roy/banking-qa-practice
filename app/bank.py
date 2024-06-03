"""Tiny banking app to practise testing against.

python3 app/bank.py            build 1.0 (has known defects)
BANK_BUILD=1.1 python3 app/bank.py   build 1.1 (defects fixed)

Only listens on 127.0.0.1. Data lives in .data/bank.db, delete it to start over.
"""
import hashlib
import json
import os
import secrets
import sqlite3
import threading
from datetime import datetime
from decimal import Decimal, InvalidOperation
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BUILD = os.environ.get("BANK_BUILD", "1.0")
if BUILD not in ("1.0", "1.1"):
    raise SystemExit("BANK_BUILD must be 1.0 or 1.1")
FIXED = BUILD == "1.1"

HERE = Path(__file__).resolve().parent
DB_PATH = os.environ.get("BANK_DB") or str(HERE.parent / ".data" / "bank.db")
PORT = int(os.environ.get("PORT", "5050"))

MIN_TRANSFER = 100          # paise
MAX_TRANSFER = 5_000_000    # paise, 50,000.00
SAVINGS_MIN_BALANCE = 50_000
MAX_FAILED_LOGINS = 3

SCHEMA = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    account_no TEXT NOT NULL UNIQUE,
    account_type TEXT NOT NULL,
    balance_paise INTEGER NOT NULL
);
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    txn_type TEXT NOT NULL,
    amount_paise INTEGER NOT NULL,
    balance_after_paise INTEGER NOT NULL,
    description TEXT,
    reference TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE transfers (
    id INTEGER PRIMARY KEY,
    reference TEXT NOT NULL UNIQUE,
    from_account_id INTEGER NOT NULL REFERENCES accounts(id),
    to_account_id INTEGER NOT NULL REFERENCES accounts(id),
    amount_paise INTEGER NOT NULL,
    remark TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

# username, full name, password, [(account no, type, opening balance in paise)]
SEED = [
    ("asha", "Asha Reddy", "Asha@1234",
     [("5010000101", "SAVINGS", 2_500_000), ("5010000102", "CURRENT", 8_000_000)]),
    ("ravi", "Ravi Kumar", "Ravi@1234", [("5010000201", "SAVINGS", 1_000_000)]),
    ("kiran", "Kiran Rao", "Kiran@1234", [("5010000301", "SAVINGS", 500_000)]),
]

lock = threading.Lock()
sessions = {}


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 20000).hex()
    return f"{salt}${digest}"


def check_password(password, stored):
    salt = stored.split("$", 1)[0]
    return secrets.compare_digest(hash_password(password, salt), stored)


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def rupees(paise):
    return f"{paise // 100}.{paise % 100:02d}"


def connect():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    return conn


db = connect()


def reset_data():
    with lock:
        for table in ("transfers", "transactions", "accounts", "users"):
            db.execute(f"DROP TABLE IF EXISTS {table}")
        db.executescript(SCHEMA)
        sessions.clear()
        for username, full_name, password, accounts in SEED:
            cur = db.execute(
                "INSERT INTO users (username, full_name, password_hash) VALUES (?, ?, ?)",
                (username, full_name, hash_password(password)),
            )
            for account_no, kind, opening in accounts:
                acc = db.execute(
                    "INSERT INTO accounts (user_id, account_no, account_type, balance_paise) VALUES (?, ?, ?, ?)",
                    (cur.lastrowid, account_no, kind, opening),
                )
                db.execute(
                    "INSERT INTO transactions (account_id, txn_type, amount_paise, balance_after_paise,"
                    " description, reference, created_at) VALUES (?, 'CREDIT', ?, ?, 'Opening balance', ?, ?)",
                    (acc.lastrowid, opening, opening, f"OPEN{account_no}", "2026-01-01 09:00:00"),
                )


if not db.execute("SELECT name FROM sqlite_master WHERE name = 'users'").fetchone():
    reset_data()


class ApiError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def parse_amount(raw):
    """Turn the amount from the request into paise, or raise ApiError."""
    if isinstance(raw, bool) or raw is None or str(raw).strip() == "":
        raise ApiError(400, "INVALID_AMOUNT", "Enter a valid amount")
    try:
        value = Decimal(str(raw).strip())
    except InvalidOperation:
        raise ApiError(400, "INVALID_AMOUNT", "Enter a valid amount")
    if not value.is_finite() or value <= 0:
        raise ApiError(400, "INVALID_AMOUNT", "Enter a valid amount")
    if FIXED and value != value.quantize(Decimal("0.01")):
        raise ApiError(400, "INVALID_AMOUNT", "Amount can have at most 2 decimal places")
    paise = int(value * 100)  # build 1.0 silently drops anything after 2 decimals
    if paise < MIN_TRANSFER:
        raise ApiError(400, "AMOUNT_TOO_LOW", "Minimum transfer is 1.00")
    if paise > MAX_TRANSFER:
        raise ApiError(400, "AMOUNT_TOO_HIGH", "Maximum transfer per transaction is 50000.00")
    return paise


def login(body):
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    if not username or not password:
        raise ApiError(400, "MISSING_FIELDS", "Username and password are required")
    user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if user and user["locked"]:
        raise ApiError(423, "ACCOUNT_LOCKED", "Account is locked after too many failed attempts")
    if not user or not check_password(password, user["password_hash"]):
        if user:
            attempts = user["failed_attempts"] + 1
            db.execute("UPDATE users SET failed_attempts = ?, locked = ? WHERE id = ?",
                       (attempts, 1 if attempts >= MAX_FAILED_LOGINS else 0, user["id"]))
        raise ApiError(401, "INVALID_CREDENTIALS", "Invalid username or password")
    if FIXED:
        db.execute("UPDATE users SET failed_attempts = 0 WHERE id = ?", (user["id"],))
    token = secrets.token_hex(16)
    sessions[token] = user["id"]
    return 200, {"token": token, "user": {"username": user["username"], "full_name": user["full_name"]}}


def list_accounts(user_id):
    rows = db.execute("SELECT account_no, account_type, balance_paise FROM accounts WHERE user_id = ? ORDER BY id",
                      (user_id,)).fetchall()
    return 200, {"accounts": [
        {"account_no": r["account_no"], "account_type": r["account_type"], "balance": rupees(r["balance_paise"])}
        for r in rows]}


def history(user_id, account_no, query):
    acc = db.execute("SELECT * FROM accounts WHERE account_no = ?", (account_no,)).fetchone()
    if not acc:
        raise ApiError(404, "ACCOUNT_NOT_FOUND", "Account not found")
    if FIXED and acc["user_id"] != user_id:
        raise ApiError(404, "ACCOUNT_NOT_FOUND", "Account not found")
    raw_limit = query.get("limit", ["10"])[0]
    if not raw_limit.isdigit() or not 1 <= int(raw_limit) <= 50:
        raise ApiError(400, "INVALID_LIMIT", "limit must be between 1 and 50")
    sql = "SELECT * FROM transactions WHERE account_id = ?"
    args = [acc["id"]]
    kind = query.get("type", [None])[0]
    if kind:
        if kind not in ("CREDIT", "DEBIT"):
            raise ApiError(400, "INVALID_TYPE", "type must be CREDIT or DEBIT")
        sql += " AND txn_type = ?"
        args.append(kind)
    order = "DESC" if FIXED else "ASC"
    sql += f" ORDER BY id {order} LIMIT ?"
    args.append(int(raw_limit))
    rows = db.execute(sql, args).fetchall()
    return 200, {"account_no": account_no, "transactions": [
        {"reference": r["reference"], "type": r["txn_type"], "amount": rupees(r["amount_paise"]),
         "balance_after": rupees(r["balance_after_paise"]), "description": r["description"],
         "date": r["created_at"]} for r in rows]}


def transfer(user_id, body):
    from_no, to_no = body.get("from_account"), body.get("to_account")
    remark = body.get("remark") or ""
    if not from_no or not to_no:
        raise ApiError(400, "MISSING_FIELDS", "from_account and to_account are required")
    paise = parse_amount(body.get("amount"))
    if not isinstance(remark, str) or len(remark) > 50:
        raise ApiError(400, "REMARK_TOO_LONG", "Remark can be at most 50 characters")
    if from_no == to_no:
        raise ApiError(400, "SAME_ACCOUNT", "Cannot transfer to the same account")
    src = db.execute("SELECT * FROM accounts WHERE account_no = ?", (from_no,)).fetchone()
    if not src or src["user_id"] != user_id:
        raise ApiError(403, "NOT_OWNER", "Source account does not belong to you")
    dst = db.execute("SELECT * FROM accounts WHERE account_no = ?", (to_no,)).fetchone()
    if not dst:
        raise ApiError(404, "ACCOUNT_NOT_FOUND", "Destination account not found")

    floor = SAVINGS_MIN_BALANCE if src["account_type"] == "SAVINGS" else 0
    remaining = src["balance_paise"] - paise
    if remaining < 0:
        raise ApiError(400, "INSUFFICIENT_FUNDS", "Insufficient balance")
    too_low = remaining < floor if FIXED else remaining <= floor
    if floor and too_low:
        raise ApiError(400, "MIN_BALANCE", "Savings account must keep a minimum balance of 500.00")

    reference = "TXN" + secrets.token_hex(4).upper()
    stamp = now()
    new_dst_balance = dst["balance_paise"] + paise
    db.execute("BEGIN")
    try:
        db.execute("UPDATE accounts SET balance_paise = ? WHERE id = ?", (remaining, src["id"]))
        db.execute("UPDATE accounts SET balance_paise = ? WHERE id = ?", (new_dst_balance, dst["id"]))
        db.execute(
            "INSERT INTO transactions (account_id, txn_type, amount_paise, balance_after_paise, description,"
            " reference, created_at) VALUES (?, 'DEBIT', ?, ?, ?, ?, ?)",
            (src["id"], paise, remaining, f"Transfer to {to_no}", reference, stamp))
        # a transfer between your own accounts is the case build 1.0 forgets to record on the credit side
        if FIXED or src["user_id"] != dst["user_id"]:
            db.execute(
                "INSERT INTO transactions (account_id, txn_type, amount_paise, balance_after_paise, description,"
                " reference, created_at) VALUES (?, 'CREDIT', ?, ?, ?, ?, ?)",
                (dst["id"], paise, new_dst_balance, f"Transfer from {from_no}", reference, stamp))
        if FIXED:
            db.execute(
                "INSERT INTO transfers (reference, from_account_id, to_account_id, amount_paise, remark, status,"
                " created_at) VALUES (?, ?, ?, ?, ?, 'SUCCESS', ?)",
                (reference, src["id"], dst["id"], paise, remark, stamp))
        else:
            db.execute(
                "INSERT INTO transfers (reference, from_account_id, to_account_id, amount_paise, remark, status,"
                " created_at) VALUES ('%s', %d, %d, %d, '%s', 'SUCCESS', '%s')"
                % (reference, src["id"], dst["id"], paise, remark, stamp))
        db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK")
        raise
    return 201, {"reference": reference, "status": "SUCCESS", "amount": rupees(paise),
                 "from_balance": rupees(remaining)}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send(self, status, payload):
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def current_user(self):
        header = self.headers.get("Authorization", "")
        token = header[7:] if header.startswith("Bearer ") else ""
        user_id = sessions.get(token)
        if not user_id:
            raise ApiError(401, "UNAUTHORIZED", "Login required")
        return user_id

    def read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            raise ApiError(400, "BAD_JSON", "Request body is not valid JSON")
        if not isinstance(body, dict):
            raise ApiError(400, "BAD_JSON", "Request body must be a JSON object")
        return body

    def serve_page(self):
        page = (HERE / "static" / "index.html").read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)

    def handle_request(self, method):
        url = urlparse(self.path)
        parts = [p for p in url.path.split("/") if p]
        try:
            if method == "GET" and not parts:
                return self.serve_page()
            with lock:
                if method == "GET" and parts == ["api", "health"]:
                    return self.send(200, {"status": "ok", "build": BUILD})
                if method == "POST" and parts == ["api", "dev", "reset"]:
                    pass  # handled below, reset_data takes the lock itself
                elif method == "POST" and parts == ["api", "login"]:
                    return self.send(*login(self.read_json()))
                elif method == "GET" and parts == ["api", "accounts"]:
                    return self.send(*list_accounts(self.current_user()))
                elif (method == "GET" and len(parts) == 4 and parts[:2] == ["api", "accounts"]
                      and parts[3] == "transactions"):
                    return self.send(*history(self.current_user(), parts[2], parse_qs(url.query)))
                elif method == "POST" and parts == ["api", "transfers"]:
                    user_id = self.current_user()
                    return self.send(*transfer(user_id, self.read_json()))
                else:
                    raise ApiError(404, "NOT_FOUND", "No such endpoint")
            reset_data()
            return self.send(200, {"status": "reset", "build": BUILD})
        except ApiError as err:
            self.send(err.status, {"error": err.message, "code": err.code})
        except Exception:
            self.send(500, {"error": "Internal server error"})

    def do_GET(self):
        self.handle_request("GET")

    def do_POST(self):
        self.handle_request("POST")


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"bank app build {BUILD} on http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
