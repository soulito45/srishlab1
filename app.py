"""
Intelligent Data Analysis Assistant (IDAA)
============================================
A Flask-based Data Science web application that lets a user
register/login, upload a dataset (CSV/Excel), automatically runs
EDA on it, allows interactive
filtering/grouping, custom chart building, and exports a PDF report.

Run with:  python app.py
"""

import os
import uuid
import io
import secrets
import hmac
from datetime import datetime
from urllib.parse import urlparse

from flask import (
    Flask, render_template, redirect, url_for, flash, request,
    jsonify, send_file, abort, session
)
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from werkzeug.utils import secure_filename
import pandas as pd

from config import Config
from models import db, User, Dataset, QueryHistory
from utils import eda, query_engine, report_generator

# ---------------------------------------------------------------------------
# App / extensions setup
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config.from_object(Config)

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), "database"), exist_ok=True)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access the Intelligent Data Analysis Assistant."
login_manager.login_message_category = "warning"


@app.context_processor
def inject_csrf_token():
    token = session.setdefault("csrf_token", secrets.token_urlsafe(32))
    return {"csrf_token": token}


@app.before_request
def validate_csrf_token():
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return None
    expected = session.get("csrf_token")
    supplied = request.form.get("csrf_token") or request.headers.get("X-CSRFToken")
    if not expected or not supplied or not hmac.compare_digest(expected, supplied):
        if request.is_json:
            return jsonify({"error": "Invalid or missing CSRF token."}), 400
        abort(400, description="Invalid or missing CSRF token.")
    return None


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]


def get_owned_dataset_or_404(dataset_id):
    ds = db.session.get(Dataset, dataset_id)
    if ds is None or ds.user_id != current_user.id:
        abort(404)
    return ds


def load_dataset_dataframe(dataset):
    try:
        return eda.load_dataframe(dataset.filepath)
    except FileNotFoundError:
        abort(404, description="The stored dataset file is missing.")
    except (OSError, ValueError) as error:
        abort(422, description=f"The dataset cannot be analyzed: {error}")


def is_safe_redirect(target):
    """Only allow relative redirects or redirects back to this application."""
    if not target:
        return False
    parsed = urlparse(target)
    return not parsed.netloc or parsed.netloc == urlparse(request.host_url).netloc


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        full_name = request.form.get("full_name", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not username or not email or not password:
            flash("Please fill in all required fields.", "danger")
            return render_template("register.html")

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("register.html")

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("Username or email already registered.", "danger")
            return render_template("register.html")

        user = User(username=username, email=email, full_name=full_name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier.lower())
        ).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f"Welcome back, {user.full_name or user.username}!", "success")
            next_page = request.args.get("next")
            return redirect(next_page if is_safe_redirect(next_page) else url_for("dashboard"))

        flash("Invalid username/email or password.", "danger")

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Dashboard & Upload
# ---------------------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    datasets = Dataset.query.filter_by(user_id=current_user.id).order_by(Dataset.uploaded_at.desc()).all()

    total_rows_analyzed = sum(d.n_rows for d in datasets)
    return render_template("dashboard.html", datasets=datasets, total_rows_analyzed=total_rows_analyzed)


@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        file = request.files.get("file")
        description = request.form.get("description", "").strip()

        if not file or file.filename == "":
            flash("Please choose a file to upload.", "danger")
            return redirect(url_for("upload"))

        if not allowed_file(file.filename):
            flash("Only .csv, .xlsx and .xls files are supported.", "danger")
            return redirect(url_for("upload"))

        original_name = secure_filename(file.filename)
        stored_filename = f"{uuid.uuid4().hex}_{original_name}"
        user_folder = os.path.join(app.config["UPLOAD_FOLDER"], str(current_user.id))
        os.makedirs(user_folder, exist_ok=True)
        filepath = os.path.join(user_folder, stored_filename)
        file.save(filepath)

        try:
            df, _ = eda.load_dataframe_with_report(filepath)
        except Exception as e:
            os.remove(filepath)
            flash(f"Could not read the file: {e}", "danger")
            return redirect(url_for("upload"))

        dataset = Dataset(
            user_id=current_user.id,
            original_name=original_name,
            stored_filename=stored_filename,
            filepath=filepath,
            n_rows=df.shape[0],
            n_columns=df.shape[1],
            file_size_kb=os.path.getsize(filepath) / 1024,
            description=description,
        )
        db.session.add(dataset)
        db.session.commit()

        flash(f"'{original_name}' cleaned and analyzed successfully!", "success")
        return redirect(url_for("analysis", dataset_id=dataset.id))

    return render_template("upload.html")


@app.route("/delete/<int:dataset_id>", methods=["POST"])
@login_required
def delete_dataset(dataset_id):
    ds = get_owned_dataset_or_404(dataset_id)
    try:
        if os.path.exists(ds.filepath):
            os.remove(ds.filepath)
    except OSError:
        pass
    QueryHistory.query.filter_by(dataset_id=dataset_id).delete()
    db.session.delete(ds)
    db.session.commit()
    flash("Dataset deleted.", "info")
    return redirect(url_for("dashboard"))


# ---------------------------------------------------------------------------
# Analysis (Auto EDA)
# ---------------------------------------------------------------------------
@app.route("/analysis/<int:dataset_id>")
@login_required
def analysis(dataset_id):
    ds = get_owned_dataset_or_404(dataset_id)
    df, cleaning_report = eda.load_dataframe_with_report(ds.filepath)

    overview = eda.basic_overview(df)
    profiles = eda.column_profile(df)

    missing_chart = eda.missing_value_chart(df)
    corr_chart = eda.correlation_heatmap(df)
    dist_charts = eda.numeric_distribution_charts(df)
    cat_charts = eda.categorical_top_values(df)

    preview_rows = df.head(10).fillna("").to_dict(orient="records")
    preview_cols = df.columns.tolist()

    return render_template(
        "analysis.html",
        ds=ds, overview=overview, profiles=profiles,
        missing_chart=missing_chart, corr_chart=corr_chart,
        dist_charts=dist_charts, cat_charts=cat_charts,
        preview_rows=preview_rows, preview_cols=preview_cols,
        cleaning_report=cleaning_report,
    )


@app.route("/download-cleaned/<int:dataset_id>")
@login_required
def download_cleaned(dataset_id):
    ds = get_owned_dataset_or_404(dataset_id)
    df = load_dataset_dataframe(ds)
    filename = f"cleaned_{os.path.splitext(ds.original_name)[0]}.csv"
    buffer = io.BytesIO(df.to_csv(index=False).encode("utf-8"))
    return send_file(buffer, mimetype="text/csv", as_attachment=True, download_name=filename)


# ---------------------------------------------------------------------------
# Query builder (filter / group)
# ---------------------------------------------------------------------------
@app.route("/query/<int:dataset_id>")
@login_required
def query_page(dataset_id):
    ds = get_owned_dataset_or_404(dataset_id)
    df = load_dataset_dataframe(ds)
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    all_cols = df.columns.tolist()
    return render_template("query.html", ds=ds, all_cols=all_cols, numeric_cols=numeric_cols)


@app.route("/api/filter/<int:dataset_id>", methods=["POST"])
@login_required
def api_filter(dataset_id):
    ds = get_owned_dataset_or_404(dataset_id)
    df = load_dataset_dataframe(ds)

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "Invalid request payload."}), 400
    filters = payload.get("filters", [])
    if not isinstance(filters, list):
        return jsonify({"error": "Filters must be a list."}), 400
    try:
        page = max(1, int(payload.get("page", 1)))
    except (TypeError, ValueError):
        return jsonify({"error": "Page must be a positive number."}), 400

    try:
        filtered_df, applied = query_engine.apply_filters(df, filters)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    page_df, total, total_pages = query_engine.paginate(filtered_df, page=page, per_page=15)

    if applied:
        history = QueryHistory(
            dataset_id=dataset_id, user_id=current_user.id,
            query_summary=" AND ".join(applied)
        )
        db.session.add(history)
        db.session.commit()

    return jsonify({
        "columns": df.columns.tolist(),
        "rows": page_df.fillna("").to_dict(orient="records"),
        "total_matched": total,
        "total_pages": total_pages,
        "current_page": page,
        "applied_filters": applied,
    })


@app.route("/api/group/<int:dataset_id>", methods=["POST"])
@login_required
def api_group(dataset_id):
    ds = get_owned_dataset_or_404(dataset_id)
    df = load_dataset_dataframe(ds)

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "Invalid request payload."}), 400
    group_col = payload.get("group_col")
    agg_col = payload.get("agg_col")
    agg_func = payload.get("agg_func", "sum")

    grouped = query_engine.apply_group(df, group_col, agg_col, agg_func)
    if grouped is None:
        return jsonify({"error": "Invalid grouping configuration."}), 400

    chart_col = "count" if agg_func == "count" else agg_col
    chart = eda.build_grouped_bar_chart(grouped, group_col, chart_col, agg_func)

    return jsonify({
        "rows": grouped.head(50).fillna("").to_dict(orient="records"),
        "columns": grouped.columns.tolist(),
        "chart": chart,
    })


# ---------------------------------------------------------------------------
# Chart builder
# ---------------------------------------------------------------------------
@app.route("/visualize/<int:dataset_id>")
@login_required
def visualize(dataset_id):
    ds = get_owned_dataset_or_404(dataset_id)
    df = load_dataset_dataframe(ds)
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    all_cols = df.columns.tolist()
    return render_template("visualize.html", ds=ds, all_cols=all_cols,
                           numeric_cols=numeric_cols, categorical_cols=categorical_cols)


@app.route("/api/chart/<int:dataset_id>", methods=["POST"])
@login_required
def api_chart(dataset_id):
    ds = get_owned_dataset_or_404(dataset_id)
    df = load_dataset_dataframe(ds)

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "Invalid request payload."}), 400
    chart_type = payload.get("chart_type")
    x_col = payload.get("x_col")
    y_col = payload.get("y_col") or None
    agg_func = payload.get("agg_func") or "sum"

    valid_chart_types = {"bar", "line", "scatter", "pie", "box", "histogram"}
    valid_agg_funcs = {"sum", "mean", "count", "max", "min", "median"}
    if chart_type not in valid_chart_types or x_col not in df.columns:
        return jsonify({"error": "Invalid chart type or X-axis column."}), 400
    if chart_type in {"bar", "line", "scatter", "box"} and y_col not in df.columns:
        return jsonify({"error": "This chart requires a valid Y-axis column."}), 400
    if chart_type in {"bar", "line"} and agg_func not in valid_agg_funcs:
        return jsonify({"error": "Invalid aggregation function."}), 400
    if chart_type in {"bar", "line", "scatter", "box"} and y_col:
        if chart_type != "scatter" and agg_func != "count" and not pd.api.types.is_numeric_dtype(df[y_col]):
            return jsonify({"error": "The selected Y-axis column must be numeric."}), 400

    chart = eda.build_custom_chart(df, chart_type, x_col, y_col, agg_func)
    return jsonify(chart), 400 if chart.get("error") else 200


# ---------------------------------------------------------------------------
# PDF report
# ---------------------------------------------------------------------------
@app.route("/report/<int:dataset_id>")
@login_required
def report(dataset_id):
    ds = get_owned_dataset_or_404(dataset_id)
    df = load_dataset_dataframe(ds)

    overview = eda.basic_overview(df)
    profiles = eda.column_profile(df)
    buffer = report_generator.generate_pdf_report(
        ds.original_name, overview, profiles,
        generated_by=current_user.username
    )

    filename = f"Srish_Report_{ds.original_name.rsplit('.', 1)[0]}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype="application/pdf")


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return render_template("errors/404.html"), 404


@app.errorhandler(413)
def too_large(e):
    flash("File is too large. Maximum allowed size is 25 MB.", "danger")
    return redirect(url_for("upload"))


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
def create_tables():
    with app.app_context():
        db.create_all()


create_tables()

if __name__ == "__main__":
    print("=" * 60)
    print("  Intelligent Data Analysis Assistant (IDAA)")
    print("  Server running at: http://127.0.0.1:5000")
    print("=" * 60)
    # NOTE: use_reloader is disabled on purpose. The default Werkzeug
    # auto-reloader watches the entire project folder (including
    # uploads/ and database/) and restarts the server whenever a file
    # is written there -- which happens on every dataset upload and can
    # drop the in-flight request. debug=True still gives the interactive
    # debugger on errors.
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1", use_reloader=False,
            host="127.0.0.1", port=5000)
