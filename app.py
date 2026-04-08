from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

app = Flask(__name__)

# ---------------- DB CONNECTION ----------------
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Prasi@123",
    database="banking_system"
)

cursor = db.cursor(dictionary=True)

# ---------------- DASHBOARD ----------------
@app.route("/")
def dashboard():

    # 🔹 Customer + Account Data
    cursor.execute("""
        SELECT c.customer_id, c.name, c.email,
               a.account_id, a.account_type, a.balance
        FROM customers c
        LEFT JOIN accounts a ON c.customer_id = a.customer_id
    """)
    data = cursor.fetchall()

    # 🔥 TOTAL DEPOSITS (FIXED)
    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total_deposit
        FROM transactions
        WHERE txn_type = 'DEPOSIT'
    """)
    total_deposit = cursor.fetchone()["total_deposit"]

    # 🔥 TOTAL WITHDRAWALS (FIXED)
    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total_withdraw
        FROM transactions
        WHERE txn_type = 'WITHDRAW'
    """)
    total_withdraw = cursor.fetchone()["total_withdraw"]

    # 🔥 MONTHLY TRANSACTION TREND
    cursor.execute("""
        SELECT DATE_FORMAT(txn_date, '%Y-%m') AS month,
               SUM(amount) AS total
        FROM transactions
        GROUP BY month
        ORDER BY month
    """)
    chart_data = cursor.fetchall()

    months = [row["month"] for row in chart_data]
    totals = [float(row["total"]) for row in chart_data]

    return render_template(
        "dashboard.html",
        data=data,
        total_deposit=total_deposit,
        total_withdraw=total_withdraw,
        months=months,
        totals=totals
    )

# ---------------- ADD CUSTOMER ----------------
@app.route("/add_customer", methods=["GET", "POST"])
def add_customer():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]

        cursor.execute("SELECT * FROM customers WHERE email=%s", (email,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO customers(name, email) VALUES (%s, %s)",
                (name, email)
            )
            db.commit()

        return redirect(url_for("dashboard"))

    return render_template("add_customer.html")

# ---------------- OPEN ACCOUNT ----------------
@app.route("/open_account", methods=["GET", "POST"])
def open_account():
    if request.method == "POST":
        customer_id = request.form["customer_id"]
        account_type = request.form["account_type"]

        cursor.execute(
            "INSERT INTO accounts(customer_id, account_type, balance) VALUES (%s, %s, 0)",
            (customer_id, account_type)
        )
        db.commit()

        return redirect(url_for("dashboard"))

    return render_template("open_account.html")

# ---------------- DEPOSIT ----------------
@app.route("/deposit", methods=["GET", "POST"])
def deposit():
    if request.method == "POST":
        account_id = request.form["account_id"]
        amount = float(request.form["amount"])

        # update balance
        cursor.execute(
            "UPDATE accounts SET balance = balance + %s WHERE account_id = %s",
            (amount, account_id)
        )

        # insert transaction WITH DATE ✅
        cursor.execute(
            "INSERT INTO transactions(account_id, txn_type, amount, txn_date) VALUES (%s, %s, %s, NOW())",
            (account_id, "DEPOSIT", amount)
        )

        db.commit()
        return redirect(url_for("dashboard"))

    return render_template("deposit.html")

# ---------------- WITHDRAW ----------------
@app.route("/withdraw", methods=["GET", "POST"])
def withdraw():
    if request.method == "POST":
        account_id = request.form["account_id"]
        amount = float(request.form["amount"])

        cursor.execute("SELECT balance FROM accounts WHERE account_id=%s", (account_id,))
        acc = cursor.fetchone()

        if acc and acc["balance"] >= amount:
            cursor.execute(
                "UPDATE accounts SET balance = balance - %s WHERE account_id = %s",
                (amount, account_id)
            )

            # insert transaction WITH DATE ✅
            cursor.execute(
                "INSERT INTO transactions(account_id, txn_type, amount, txn_date) VALUES (%s, %s, %s, NOW())",
                (account_id, "WITHDRAW", amount)
            )

            db.commit()

        return redirect(url_for("dashboard"))

    return render_template("withdraw.html")

# ---------------- LOAN EMI ----------------
@app.route("/loan", methods=["GET", "POST"])
def loan():
    emi = None

    if request.method == "POST":
        principal = float(request.form["principal"])
        rate = float(request.form["rate"])
        months = int(request.form["months"])

        r = rate / 12 / 100
        emi = principal * r * (1 + r) ** months / ((1 + r) ** months - 1)

    return render_template("loan.html", emi=emi)

# ---------------- CHARTS ----------------
@app.route("/charts")
def charts():

    # 💰 Deposit vs Withdraw
    cursor.execute("""
        SELECT txn_type, SUM(amount) as total 
        FROM transactions 
        GROUP BY txn_type
    """)
    trans_data = cursor.fetchall()

    labels1 = [row['txn_type'] for row in trans_data]
    values1 = [float(row['total']) for row in trans_data]

    # 🏦 Account Type Distribution
    cursor.execute("""
        SELECT account_type, COUNT(*) as count 
        FROM accounts 
        GROUP BY account_type
    """)
    acc_data = cursor.fetchall()

    labels2 = [row['account_type'] for row in acc_data]
    values2 = [row['count'] for row in acc_data]

    # 👑 Top 5 Customers
    cursor.execute("""
        SELECT c.name, SUM(a.balance) as total_balance
        FROM customers c
        JOIN accounts a ON c.customer_id = a.customer_id
        GROUP BY c.name
        ORDER BY total_balance DESC
        LIMIT 5
    """)
    top_data = cursor.fetchall()

    labels3 = [row['name'] for row in top_data]
    values3 = [float(row['total_balance']) for row in top_data]

    return render_template(
        "charts.html",
        labels1=labels1, values1=values1,
        labels2=labels2, values2=values2,
        labels3=labels3, values3=values3
    )



# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)