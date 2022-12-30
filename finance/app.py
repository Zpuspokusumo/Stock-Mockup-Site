import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# export API_KEY=pk_d84486e7dd1c400887fa7190fbaa51b1

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # Complete the implementation of index in such a way that it displays
    # an HTML table summarizing, for the user currently logged in,
    # which stocks the user owns,
    # the numbers of shares owned,
    # the current price of each stock, and
    # the total value of each holding (i.e., shares times price).
    # Also display the user’s current cash balance along with a grand total (i.e., stocks’ total value plus cash).

    # make a table that keep track of the number of stonks by a person
    # maybe make the recordtu table in buy update where id = person_id instead of insert into row if (table row where id and symbol) = 0

    id = session.get("user_id")
    porto = db.execute("SELECT * FROM porto WHERE person_id = ? AND shares IS NOT 0 ORDER BY symbol", id)
    stmoney = 0
    for companies in porto:
        symbl = companies["symbol"]
        stock = lookup(symbl)
        newprice = float(stock["price"])
        ownedshares = int(companies["shares"])
        totale = ownedshares * newprice
        db.execute("UPDATE porto SET price = ?, total = ? WHERE symbol = ? AND person_id = ?", newprice, totale, symbl, id)
        stmoney = stmoney + totale

    cash = db.execute("select cash from users where id = ?", id)
    cashh = float(cash[0]["cash"])
    wealth = cashh + stmoney

    return render_template("index.html", porto=porto, cash=cashh, wealth=wealth)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    # Require that a user input a stock’s symbol, implemented as a text field whose name is symbol.
    # Render an apology if the input is blank or the symbol does not exist (as per the return value of lookup).
    if request.method == "POST":

        symbl = request.form.get("symbol")
        stock = lookup(symbl)
        try:
            shares = int(request.form.get("shares"))
        except ValueError:
            return apology("please enter a number")
        id = session.get("user_id")
        if not request.form.get("shares").isdigit():
            return apology("please enter an integer")

        # if not symbol or stock
        if not symbl:
            return apology("must input a symbol")
        if not stock:
            return apology("that ticker symbol does not exist")

        # cash currenly owned
        cash = db.execute("select cash from users where id = ?", id)
        if float(cash[0]["cash"]) > (float(stock["price"]) * shares):

            # insert record transaction and insert new cash value
            select = db.execute("SELECT * from porto WHERE person_id = ? AND symbol = ?", id, symbl)

            # new cash
            newcash = float(cash[0]["cash"]) - (stock["price"] * shares)
            stkprice = float(stock["price"])

            # if user has a no stocks of that symbol
            if len(select) != 1:
                totale = (shares * stkprice)
                db.execute("INSERT INTO history (person_id, symbol, price, shares) VALUES (?, ?, ?, ?)",
                           id, symbl, stkprice, shares)
                db.execute("INSERT INTO porto (person_id, symbol, name, shares, price, total) VALUES (?, ?, ?, ?, ?, ?)",
                           id, symbl, stock["name"], shares, stkprice, totale)
                db.execute("UPDATE users SET cash = ? WHERE id = ?", newcash, id)
                return redirect("/")
            # if user has stock of that symbol
            else:
                totale = ((currshares + shares) * stkprice)
                currshares = int(select[0]["shares"])
                db.execute("UPDATE history SET shares = ? WHERE person_id = ? and symbol = ?", shares, id, symbl)
                db.execute("UPDATE porto SET shares = ?, price = ?, total = ? WHERE person_id = ? and symbol = ?",
                           (currshares + shares), stkprice, totale, id, symbl)
                db.execute("UPDATE users SET cash = ? WHERE id = ?", newcash, id)
                return redirect("/")
        else:
            return apology("not enough cash", 403)

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    # For each row, make clear whether a stock was bought or sold and include
    # the stock’s symbol,
    # the (purchase or sale) price,
    # the number of shares bought or sold, and
    # the date and time at which the transaction occurred.

    # You might need to alter the table you created for buy or supplement it with an additional table. Try to minimize redundancies.
    id = session.get("user_id")
    history = db.execute("SELECT * FROM history WHERE person_id = ? ORDER BY symbol", id)
    return render_template("history.html", history=history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        stock = lookup(request.form.get("symbol"))
        if not request.form.get("symbol"):
            return apology("you must input a symbol")
        if not stock:
            return apology("that ticker symbol does not exist")

        return render_template("quoting.html", stock=stock)

    # Require that a user input a stock’s symbol, implemented as a text field whose name is symbol.
    # Submit the user’s input via POST to /quote.
    # When a user visits /quote via GET, render one of those templates, inside of which should be an HTML form that submits to /quote via POST
    # In response to a POST, quote can render that second template, embedding within it one or more values from lookup.
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Require that a user input a username, implemented as a text field whose name is username.
    # Render an apology if the user’s input is blank or the username already exists.
    if request.method == "POST":

        # check if username
        if not request.form.get("username"):
            return apology("must provide username")

        # check if password
        elif not request.form.get("password"):
            return apology("must provide password")

        uname = request.form.get("username")
        pword = request.form.get("password")
        conf = request.form.get("confirmation")

        # check if username doesnt already exist
        unames_like = db.execute("SELECT * FROM users WHERE username = ?", uname)
        if len(unames_like) != 0:
            return apology("Username already exists")

        # check if password = confirmation, pword=conf
        if (pword != conf):
            return apology("Password does not match")

        # Require that a user input a password, implemented as a text field whose name is password,
        # and then that same password again, implemented as a text field whose name is confirmation.
        # Render an apology if either input is blank or the passwords do not match.
        hashed = generate_password_hash(pword)

        # Submit the user’s input via POST to /register.
        # INSERT the new user into users, storing a hash of the user’s password, not the password itself.
        # Hash the user’s password with generate_password_hash
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", uname, hashed)
        return render_template("login.html")

        # Odds are you’ll want to create a new template (e.g., register.html) that’s quite similar to login.html.
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    # Require that a user input a stock’s symbol, implemented as a select menu whose name is symbol.
    # Render an apology if the user fails to select a stock or if (somehow, once submitted) the user does not own any shares of that stock.
    # Require that a user input a number of shares, implemented as a field whose name is shares.
    # Render an apology if the input is not a positive integer or if the user does not own that many shares of the stock.
    # Submit the user’s input via POST to /sell.
    # Upon completion, redirect the user to the home page.
    if request.method == "POST":

        id = session.get("user_id")
        symbl = request.form.get("symbol")
        stock = db.execute("SELECT * FROM porto WHERE symbol = ? AND person_id = ?", symbl, id)
        shareinput = request.form.get("shares")

        # if not symbol or stock or stock == 0
        if not shareinput and not symbl:
            return apology("you have to sell something!")
        # if not shareinput:
            # return apology("you must enter a number")
        if not symbl:
            return apology("you must select a stock to sell")
        if not stock:
            return apology("you dont have that stock")

        shares = int(shareinput)
        curshare = stock[0]["shares"]
        soldshare = shares * (-1)
        newshare = curshare + soldshare

        # if input not positive integer or if not enough shares of stocks in hand
        if int(stock[0]["shares"]) == 0:
            return apology("you dont have any of that stock")
        if shares > int(stock[0]["shares"]):
            return apology("you dont have enough stock")
        if shares == 0:
            return apology("you cant sell 0 shares!")

        # copied in its entirety from /buy
        # cash currenly owned
        cash = db.execute("select cash from users where id = ?", id)
        # new cash
        newcash = float(cash[0]["cash"]) + (float(stock[0]["price"]) * shares)
        stkprice = float(stock[0]["price"])
        totale = newshare * stkprice

        # insert record transaction and insert new cash value
        db.execute("INSERT INTO history (person_id, symbol, price, shares) VALUES (?, ?, ?, ?)",
                   id, symbl, stock[0]["price"], soldshare)
        # remove amount of stonks from portofolio
        db.execute("UPDATE porto SET shares = ?, price = ?, total =? WHERE person_id = ? and symbol = ?",
                   newshare, stkprice, totale, id, symbl)
        # update newcash into user cash
        db.execute("UPDATE users SET cash = ? WHERE id = ?", newcash, id)
        return redirect("/")

    else:
        id = session.get("user_id")
        symbols = db.execute("SELECT symbol FROM porto WHERE person_id = ? AND shares > 0", id)
        return render_template("sell.html", symbols=symbols)


@app.route("/add")
@login_required
def add():
    """add 1000 to cash"""
    # get user id
    id = session.get("user_id")

    # cash currenly owned
    cash = db.execute("select cash from users where id = ?", id)

    # new cash
    newcash = float(cash[0]["cash"]) + 1000
    db.execute("UPDATE users SET cash = ? WHERE id = ?", newcash, id)
    return redirect("/")

