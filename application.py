from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import gettempdir

from helpers import *

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = gettempdir()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

@app.route("/")
@login_required
def index():
    # get cash
    u_id = session["user_id"]
    cashdict = db.execute("SELECT cash FROM users WHERE id = :id", id = u_id)
    cash = round(cashdict[0]["cash"], 2)
    
    # get rows
    rows = db.execute("SELECT symbol, SUM(shares) AS shares FROM trans WHERE id = :id GROUP BY symbol", id = u_id)
    
    # get list of stocks held
    stocks = []
    i = 1
    
    # iterate over rows and display
    for row in rows:
        quote = lookup(row["symbol"])
        total = round(float(quote["price"]) * float(row["shares"]), 2)
        name = quote["name"]
        
        STOCK_DICT = {"symbol": row["symbol"], "name": name, "shares": row["shares"], "price": quote["price"], "TOTAL": total }
        stocks.append(STOCK_DICT)
        i = i + 1
        
    return render_template("index.html", stocks = stocks, i = i, cash = cash)
    

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock."""
    
    if request.method == "POST":
        
        # check if fields empty and positive value
        if request.form.get("symbol") == "" or request.form.get("shares") == "" or int(request.form.get("shares")) <= 0:
            return apology("must input valid symbol & number of shares")
        
        # check for valid symbol
        else:
            quote = lookup(request.form.get("symbol"))
            if not quote:
                return apology("Symbol not found")
            else:
                u_id = session["user_id"]
                
                #check if the user has enough money
                price = float(quote["price"])
                symbol = quote["symbol"]
                cashdict = db.execute("SELECT cash FROM users WHERE id = :id", id = u_id)
                cash = float(cashdict[0]["cash"])
                shares = int(request.form.get("shares"))
                money = price*shares
                if cash < money:
                    return apology("not enough money")
                else:
                    # insert data to transaction (trans) database
                    db.execute("INSERT INTO trans (id, symbol, price, shares) VALUES (:id, :symbol, :price, :shares)", id = u_id, price = price, symbol = symbol, shares= shares)
                    
                    # update cash
                    db.execute("UPDATE users SET cash = :cash WHERE id = :id", cash = cash - money, id = u_id)
                    return redirect(url_for("index"))
    else:        
        return render_template("buy.html")
   
    return render_template("buy.html")
                    
@app.route("/history")
@login_required
def history():
    """Show history of transactions."""
    u_id = session["user_id"]
    transaction = ""
    shares = 0
    
    # get data in rows
    db.execute("SELECT * FROM trans WHERE id = :id", id = u_id)
    
    # generates list of holdings
    stocks = []
    for row in rows:
        if int(row["shares"] > 0):
            transaction = "BUY"
            shares = int(row["shares"])
        
        else:
            transaction = "SELL"
            shares = -int(row["shares"])
        
        STOCK_DICT = {"transction": transaction, "time": row["time"], "symbol": row["symbol"], "shares": shares, "price": row["price"] }
        stocks.append(STOCK_DICT)
        
    return render_template("history.html", stocks = stocks)
    

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        quote = lookup(symbol)
        
        # if not found
        if not quote:
            return apology("Symbol not found")
            
        else:
            # send value to quoted.html
            return render_template("quoted.html", name = quote["name"], symbol = quote["symbol"], price = quote["price"])
    
    # show quote template
    else:
        return render_template("quote.html")
            

@app.route("/register", methods=["GET", "POST"])
def register():
    
    session.clear()
    if request.method == "POST":
        
        # check if username entered
        if request.form.get("username") == "":
            return apology ("Please provide username")
            
        # check if password entered
        if request.form.get("password") == "" or request.form.get("confirmation") == "":
            return apology ("Please provide password")
          
        # check if password match  
        if not request.form.get("password") == request.form.get("confirmation"):
            return apology ("Passwords don't match")
            
        # check if the username exists already
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
        if len(rows) != 0:
            return apology ("Username already exists")
            
        else: 
            #hash password
            hashed = pwd_context.encrypt(request.form.get("password"))
            
            # add the user into the database
            db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash)", username = request.form.get("username"), hash = hashed )
            
            # remember the user registration
            rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
            session["user_id"] = rows[0]["id"]
            return redirect(url_for("index"))
            
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock."""
    if request.method == "POST":
        
    # check if fields empty and positive value
        if request.form.get("symbol") == "" or request.form.get("shares") == "" or int(request.form.get("shares")) <= 0:
            return apology("must input valid symbol & number of shares")
    
        # check for valid symbol
        else:
            quote = lookup(request.form.get("symbol"))
            if not quote:
                return apology("Symbol not found")

            else:
                u_id = session["user_id"]
            
                # check if has that stock and enough shares
                symbol = quote["symbol"]
                rows = db.execute("SELECT symbol, SUM(shares) AS shares FROM trans WHERE id = :id GROUP BY symbol", id = u_id)
                shares = int(rows[0]["shares"])
                sellshares = int(request.form.get("shares"))
                symbolbought = rows[0]["symbol"]
                
                if symbol != symbolbought:
                    return apology("No stock with that symbol to sell")
                    
                else:
                    if sellshares > shares:
                        return apology("Not enough of those shares to sell")
                        
                    else:
                        # get price
                        price = float(quote["price"])
                        # insert data into database trans
                        db.execute("INSERT INTO trans (id, symbol, price, shares) VALUES (:id, :symbol, :price, :shares)", id = u_id, price = price, symbol = symbol, shares =- sellshares)
                        # update cash
                        money = price * float(sellshares)
                        cashdict = db.execute("SELECT cash FROM users WHERE id = :id", id = u_id)
                        cash = float(cashdict[0]["cash"])
                        db.execute("UPDATE users SET cash = :cash WHERE id = :id", cash = cash + money, id = u_id)
                        
                        return redirect(url_for("index"))
                            
    else:
        return render_template("sell.html")
                
            