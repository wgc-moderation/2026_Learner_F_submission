"""This file takes the data in my database, and displays it on the website."""
# Import Flask tools.
# And gettin ginformation entered by the user.
# Stores the name of the SQLite database used by the website.
import os
import json
import sqlite3
from datetime import timedelta
from functools import wraps
from sqlite3 import Error

from flask import (
    Flask, render_template, request,
    redirect, url_for, session
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash

# Creates the Flask app and sets the folder for CSS and static files.
app = Flask(__name__, static_folder=".static", static_url_path="/.static")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "Aramico.db")
# Load the private staff account settings.
settings_path = os.path.join(BASE_DIR, "instance", "login.json")

with open(settings_path, encoding="utf-8") as settings_file:
    login_settings = json.load(settings_file)
# Update the Flask app configuration with security settings.
app.config.update(
    SECRET_KEY=login_settings["secret_key"],
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=True,
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30)
)

# Protect forms against forged submissions.
csrf = CSRFProtect(app)


# Decorator to require login for certain views.
def login_required(view):
    """Redirect visitors to login unless they are signed in."""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped_view


# Define the route for the login page.
@app.route("/login", methods=["GET", "POST"])
def login():
    """Check the staff username and password."""
    if session.get("logged_in"):
        return redirect(url_for("render_home"))

    error = None
    username = ""
    # Handle POST requests for login form submission.
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        password_matches = check_password_hash(
            login_settings["password_hash"], password
        )
        # Log the user in id user-pass correct.
        if username == login_settings["username"] and password_matches:
            session.clear()
            session["logged_in"] = True
            session.permanent = False
            return redirect(url_for("render_home"))

        error = "Incorrect username or password."
    # error messages.
    return render_template(
        "login.html", error=error, username=username
    )


# Define the route for logging out.
@app.route("/logout", methods=["POST"])
@login_required
def logout():
    """Log the staff member out."""
    session.clear()
    return redirect(url_for("login"))


# Define an after-request function to prevent caching of private pages.
@app.after_request
def prevent_page_caching(response):
    """Prevent browsers from storing private pages in their cache."""
    if request.endpoint != "static":
        response.headers["Cache-Control"] = "no-store"
    return response


# Define a function to create a connection to the SQLite database.
def create_connection(db_file):
    """Create a connection to the database."""
    # Attempts to connect to the database.
    # If the connection is successful, the connection is returned.
    try:
        connection = sqlite3.connect(db_file)
        return connection
    except Error as e:
        print(e)
    return None


# Define the route for the home page.
@app.route('/')
@login_required
def render_home():
    """Render the home page of the website."""
    return render_template("index.html")


# Define a function to handle sorting of table columns.
def get_sorting(columns):
    """Read the sorting choice and create clickable headings."""
    sort = request.args.get("sort", "id")
    direction = request.args.get("direction", "asc")

    # Only allow column names defined in our code.
    if sort not in columns:
        sort = "id"
    # Only allow direction values defined in our code.
    if direction not in ("asc", "desc"):
        direction = "asc"

    order_by = columns[sort][1] + " " + direction.upper()

    headings = []
    # Create the headings for the table with clickable links for sorting.
    for key, (label, column) in columns.items():
        next_direction = "asc"
        arrow = ""

        if key == sort:
            if direction == "asc":
                next_direction = "desc"
                arrow = " ↑"
            else:
                arrow = " ↓"

        headings.append((label + arrow, key, next_direction))

    return sort, direction, order_by, headings


# Define the route for displaying customers with searching and sorting.
@app.route('/customers')
@login_required
def render_customers():
    """Display customers with searching and sorting."""
    con = create_connection(DATABASE)
    cur = con.cursor()

    search = request.args.get("search", "").strip()

    columns = {
        "id": ("ID", "customer_id"),
        "first_name": ("First Name", "customer_f_name COLLATE NOCASE"),
        "last_name": ("Last Name", "customer_l_name COLLATE NOCASE"),
        "email": ("Email", "customer_email COLLATE NOCASE"),
        "phone": ("Phone Number", "customer_phone_num")
    }
    # Get the sorting parameters and headings for the table.
    sort, direction, order_by, headings = get_sorting(columns)
    # Build the SQL query to fetch customers from the database.
    query = "SELECT * FROM customers"
    parameters = ()
    # If a search term is provided,
    # add a WHERE clause to the query to filter
    # results based on the search term.
    if search:
        query += """
            WHERE customer_f_name LIKE ?
            OR customer_l_name LIKE ?
            OR customer_email LIKE ?
        """
        parameters = (f"%{search}%",) * 3
    # Add an ORDER BY clause to the query to
    # sort the results based on the selected column and direction.
    query += " ORDER BY " + order_by + ", customer_id ASC"
    # Execute the query and fetch the results.
    cur.execute(query, parameters)
    customers = cur.fetchall()
    con.close()
    # Render the customers.html template
    return render_template(
        "customers.html",
        customers=customers,
        search=search,
        sort=sort,
        direction=direction,
        headings=headings
    )


# Define the route for displaying companies
# with searching and sorting.
@app.route("/companies")
@login_required
def render_companies():
    """Display companies with searching and sorting."""
    con = create_connection(DATABASE)
    cur = con.cursor()
    # Get the search term from the request arguments.
    search = request.args.get("search", "").strip()
    # Define the columns for sorting and their corresponding database fields.
    columns = {
        "id": ("Company ID", "company_id"),
        "name": ("Company Name", "company_name COLLATE NOCASE"),
        "product": ("Products", "company_product COLLATE NOCASE"),
        "year": ("Year Opened", "company_year_opened")
    }

    sort, direction, order_by, headings = get_sorting(columns)

    query = """
        SELECT company_id, company_name, company_product,
               company_year_opened, images
        FROM companies
    """
    parameters = ()
    # Search for companies based on the provided search term, if any.
    if search:
        query += " WHERE company_name LIKE ?"
        parameters = (f"%{search}%",)

    query += " ORDER BY " + order_by + ", company_id ASC"

    cur.execute(query, parameters)
    companies = cur.fetchall()
    con.close()

    return render_template(
        "companies.html",
        companies=companies,
        search=search,
        sort=sort,
        direction=direction,
        headings=headings
    )


# Define the route for displaying sales with searching and sorting.
@app.route('/sales')
@login_required
def render_sales():
    """Display sales with searching and sorting."""
    con = create_connection(DATABASE)
    cur = con.cursor()
    # Get the search term from the request arguments.
    search = request.args.get("search", "").strip()
    # Define the columns for sorting and their corresponding database fields.
    columns = {
        "id": ("Sale ID", "sales.sale_id"),
        "customer": (
            "Customer",
            "customers.customer_f_name COLLATE NOCASE"
        ),
        "company": (
            "Company",
            "companies.company_name COLLATE NOCASE"
        ),
        "date": (
            "Sale Date",
            "substr(sales.sale_date, 7, 4) || '-' || "
            "substr(sales.sale_date, 4, 2) || '-' || "
            "substr(sales.sale_date, 1, 2)"
        )
    }

    # Get the sorting parameters and headings for the table.
    sort, direction, order_by, headings = get_sorting(columns)
    # Build the SQL query to fetch sales from the database,
    # joining with customers and companies.
    query = """
        SELECT sales.sale_id,
               customers.customer_f_name,
               customers.customer_l_name,
               companies.company_name,
               sales.sale_date
        FROM sales
        JOIN customers
            ON sales.customer_id = customers.customer_id
        JOIN companies
            ON sales.company_id = companies.company_id
    """
    parameters = ()
    # Search for sales based on the provided search term, if any.
    if search:
        query += " WHERE CAST(sales.sale_id AS TEXT) LIKE ?"
        parameters = (f"%{search}%",)

    query += " ORDER BY " + order_by + ", sales.sale_id ASC"

    cur.execute(query, parameters)
    sales = cur.fetchall()
    con.close()

    return render_template(
        "sales.html",
        sales=sales,
        search=search,
        sort=sort,
        direction=direction,
        headings=headings
    )


# Run the Flask app in debug mode if this script is executed directly.
if __name__ == "__main__":
    app.run(debug=True)
