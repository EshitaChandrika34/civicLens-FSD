
import os
import uuid

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from db import get_db_connection


app = Flask(__name__)

# Set FLASK_SECRET_KEY in your environment before deploying.
# This fallback is only for local development.
app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "civiclens-local-development-key-change-before-deployment"
)

UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def mark_delayed(issues):
    """Add a 48-hour delay flag to issue dictionaries for templates."""
    now = datetime.now()
    for issue in issues:
        created_at = issue.get("created_at")
        issue["is_delayed"] = (
            issue.get("status") != "Resolved"
            and created_at is not None
            and now - created_at > timedelta(hours=48)
        )
    return issues


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )



from functools import wraps

def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))

        return view_func(*args, **kwargs)

    return wrapped_view



def admin_required():
    """Return True only for a logged-in admin."""
    return (
        "user_id" in session
        and session.get("user_role") == "admin"
    )


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

@app.route("/")
def home():
    connection = get_db_connection()

    stats = {
        "total": 0,
        "progress": 0,
        "resolved": 0
    }

    recent_issues = []

    if connection is not None:
        cursor = None

        try:
            cursor = connection.cursor(dictionary=True)

            cursor.execute("""
                SELECT
                    COUNT(*) AS total,
                    COALESCE(
                        SUM(status = 'In Progress'), 0
                    ) AS progress,
                    COALESCE(
                        SUM(status = 'Resolved'), 0
                    ) AS resolved
                FROM issues
            """)

            stats = cursor.fetchone() or stats

            cursor.execute("""
                SELECT issue_id, title, category, locality,
                       status, created_at
                FROM issues
                ORDER BY created_at DESC
                LIMIT 5
            """)

            recent_issues = mark_delayed(cursor.fetchall())

        except Exception:
            app.logger.exception("Could not load homepage data")
            flash("Some homepage information could not be loaded.", "error")

        finally:
            if cursor is not None:
                cursor.close()
            connection.close()

    return render_template(
        "index.html",
        stats=stats,
        recent_issues=recent_issues
    )


# --------------------------------------------------
# SIGNUP
# --------------------------------------------------

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not name or len(name) > 100:
        flash("Enter a name with at most 100 characters.", "error")
        return redirect(url_for("signup"))

    if (
        not email
        or len(email) > 150
        or "@" not in email
        or "." not in email.rsplit("@", 1)[-1]
    ):
        flash("Enter a valid email address.", "error")
        return redirect(url_for("signup"))

    if len(password) < 8:
        flash("Password must contain at least 8 characters.", "error")
        return redirect(url_for("signup"))

    if password != confirm_password:
        flash("Passwords do not match.", "error")
        return redirect(url_for("signup"))

    connection = get_db_connection()

    if connection is None:
        flash("Database unavailable. Please try again.", "error")
        return redirect(url_for("signup"))

    cursor = None

    try:
        cursor = connection.cursor()

        cursor.execute(
            "SELECT user_id FROM users WHERE email = %s",
            (email,)
        )

        if cursor.fetchone():
            flash("An account with this email already exists.", "error")
            return redirect(url_for("signup"))

        password_hash = generate_password_hash(password)

        cursor.execute("""
            INSERT INTO users (name, email, password_hash, role)
            VALUES (%s, %s, %s, %s)
        """, (name, email, password_hash, "resident"))

        connection.commit()

        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for("login"))

    except Exception:
        connection.rollback()
        app.logger.exception("Signup failed")
        flash("Unable to create your account. Please try again.", "error")
        return redirect(url_for("signup"))

    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


# --------------------------------------------------
# LOGIN
# --------------------------------------------------


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    connection = get_db_connection()

    if connection is None:
        flash("Database unavailable. Please try again.", "error")
        return redirect(url_for("login"))

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT user_id, name, email, password_hash, role
            FROM users
            WHERE email = %s
        """, (email,))

        user = cursor.fetchone()

        if (
            user is None
            or not check_password_hash(user["password_hash"], password)
        ):
            flash("Invalid email or password.", "error")
            return redirect(url_for("login"))

        # Store the logged-in user's information.
        session.clear()
        session["user_id"] = user["user_id"]
        session["user_name"] = user["name"]
        session["user_email"] = user["email"]
        session["user_role"] = user["role"]

        flash("Welcome back, " + user["name"] + "!", "success")

        # Redirect based on the user's actual role.
        if user["role"] == "admin":
            return redirect(url_for("admin_dashboard"))

        return redirect(url_for("home"))

    except Exception:
        app.logger.exception("Login failed")
        flash("Unable to log in. Please try again.", "error")
        return redirect(url_for("login"))

    finally:
        if cursor is not None:
            cursor.close()

        connection.close()


# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


# --------------------------------------------------
# REPORT AN ISSUE
# Only logged-in residents can submit reports.
# --------------------------------------------------



@app.route("/my-reports")
@login_required
def my_reports():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT issue_id, title, category, locality, status,
                   priority, created_at
            FROM issues
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (session["user_id"],))

        reports = mark_delayed(cursor.fetchall())

    finally:
        cursor.close()
        conn.close()

    return render_template("my_reports.html", reports=reports)


@app.route("/report", methods=["GET", "POST"])
@login_required
def report():
    if request.method == "GET":
        return render_template("report.html")

    title = request.form.get("title", "").strip()
    category = request.form.get("category", "").strip()
    locality = request.form.get("locality", "").strip()
    description = request.form.get("description", "").strip()

    # Read and validate the selected map coordinates.
    latitude_text = request.form.get("latitude", "").strip()
    longitude_text = request.form.get("longitude", "").strip()

    try:
        latitude = float(latitude_text)
        longitude = float(longitude_text)

        if not (-90 <= latitude <= 90):
            raise ValueError("Invalid latitude")

        if not (-180 <= longitude <= 180):
            raise ValueError("Invalid longitude")

    except (TypeError, ValueError):
        flash("Please select a valid location on the map.", "error")
        return redirect(url_for("report"))

    valid_categories = {
        "Roads",
        "Garbage",
        "Water",
        "Streetlights",
        "Drainage",
        "Other"
    }

    if (
        not title
        or len(title) > 150
        or not locality
        or len(locality) > 150
        or not description
        or len(description) > 3000
        or category not in valid_categories
    ):
        flash("Please enter valid details in all required fields.", "error")
        return redirect(url_for("report"))

    # Handle optional photo upload.
    photo = request.files.get("photo")
    photo_path = None
    saved_path = None

    if photo and photo.filename:
        if not allowed_file(photo.filename):
            flash("Use a JPG, JPEG, PNG, or WEBP image.", "error")
            return redirect(url_for("report"))

        original_name = secure_filename(photo.filename)

        if not original_name:
            flash("Please choose a valid image filename.", "error")
            return redirect(url_for("report"))

        extension = original_name.rsplit(".", 1)[1].lower()
        new_filename = f"{uuid.uuid4().hex}.{extension}"

        saved_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            new_filename
        )

        try:
            photo.save(saved_path)
            photo_path = f"uploads/{new_filename}"

        except Exception:
            app.logger.exception("Image upload failed")
            flash("Unable to upload the image.", "error")
            return redirect(url_for("report"))

    connection = get_db_connection()

    if connection is None:
        if saved_path and os.path.exists(saved_path):
            os.remove(saved_path)

        flash("Database unavailable. Please try again.", "error")
        return redirect(url_for("report"))

    cursor = None

    try:
        cursor = connection.cursor()

        user_id = session["user_id"]

        # Save report details and selected map coordinates.
        cursor.execute("""
            INSERT INTO issues (
                user_id,
                title,
                description,
                category,
                locality,
                photo_path,
                latitude,
                longitude,
                priority,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id,
            title,
            description,
            category,
            locality,
            photo_path,
            latitude,
            longitude,
            "Medium",
            "Reported"
        ))

        connection.commit()

        flash("Your issue has been reported successfully!", "success")
        return redirect(url_for("home"))

    except Exception:
        connection.rollback()

        if saved_path and os.path.exists(saved_path):
            os.remove(saved_path)

        app.logger.exception("Could not save the issue")
        flash("Unable to save your report. Please try again.", "error")
        return redirect(url_for("report"))

    finally:
        if cursor is not None:
            cursor.close()

        connection.close()

# --------------------------------------------------
# EXPLORE ISSUES
# Supports optional category filtering.
# --------------------------------------------------

@app.route("/issues")
def issues():
    connection = get_db_connection()

    if connection is None:
        flash("Database unavailable. Please try again.", "error")
        return render_template(
            "issues.html",
            issues=[],
            selected_category=""
        )

    all_issues = []
    selected_category = request.args.get("category", "").strip()

    valid_categories = {
        "Roads",
        "Garbage",
        "Water",
        "Streetlights",
        "Drainage",
        "Other"
    }

    if selected_category not in valid_categories:
        selected_category = ""

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        if selected_category:
            cursor.execute("""
                SELECT issue_id, title, description, category,
                       locality, photo_path, priority, status, created_at
                FROM issues
                WHERE category = %s
                ORDER BY created_at DESC
            """, (selected_category,))
        else:
            cursor.execute("""
                SELECT issue_id, title, description, category,
                       locality, photo_path, priority, status, created_at
                FROM issues
                ORDER BY created_at DESC
            """)

        all_issues = mark_delayed(cursor.fetchall())

    except Exception:
        app.logger.exception("Could not load issues")
        flash("Unable to load reports.", "error")

    finally:
        if cursor is not None:
            cursor.close()
        connection.close()

    return render_template(
        "issues.html",
        issues=all_issues,
        selected_category=selected_category
    )


# --------------------------------------------------
# ISSUE DETAILS AND STATUS HISTORY
# --------------------------------------------------


# --------------------------------------------------
# ISSUE DETAILS, STATUS HISTORY AND VOTING
# --------------------------------------------------



@app.route("/issues/<int:issue_id>")
def issue_details(issue_id):
    connection = get_db_connection()

    if connection is None:
        flash("Database unavailable. Please try again.", "error")
        return redirect(url_for("issues"))

    cursor = None
    issue = None
    updates = []
    vote_count = 0
    user_has_voted = False
    is_delayed = False

    try:
        cursor = connection.cursor(dictionary=True)

        # Get issue details, including both evidence photo paths.
        cursor.execute("""
            SELECT
                issue_id,
                user_id,
                title,
                description,
                category,
                locality,
                photo_path,
                priority,
                status,
                created_at,
                progress_photo_path,
                resolution_photo_path
            FROM issues
            WHERE issue_id = %s
        """, (issue_id,))

        issue = cursor.fetchone()

        if issue is None:
            return "Issue not found", 404

        # Show a delay warning after 48 hours if the issue is not resolved.
        if issue["created_at"] is not None:
            is_delayed = (
                issue["status"] != "Resolved"
                and datetime.now() - issue["created_at"] > timedelta(hours=48)
            )

        # Load status history.
        cursor.execute("""
            SELECT old_status, new_status, comment, updated_at
            FROM issue_updates
            WHERE issue_id = %s
            ORDER BY updated_at DESC
        """, (issue_id,))

        updates = cursor.fetchall()

        # Count community votes.
        cursor.execute("""
            SELECT COUNT(*) AS total_votes
            FROM issue_votes
            WHERE issue_id = %s
        """, (issue_id,))

        vote_result = cursor.fetchone()
        vote_count = vote_result["total_votes"]

        # Check whether the current user has voted.
        if "user_id" in session:
            cursor.execute("""
                SELECT vote_id
                FROM issue_votes
                WHERE issue_id = %s AND user_id = %s
            """, (issue_id, session["user_id"]))

            user_has_voted = cursor.fetchone() is not None

    except Exception:
        app.logger.exception("Could not load issue details")
        flash("Unable to load issue details.", "error")
        return redirect(url_for("issues"))

    finally:
        if cursor is not None:
            cursor.close()
        connection.close()

    return render_template(
        "issue_details.html",
        issue=issue,
        updates=updates,
        vote_count=vote_count,
        user_has_voted=user_has_voted,
        is_delayed=is_delayed
    )

# --------------------------------------------------
# UPVOTE AN ISSUE
# One vote per logged-in user per issue
# --------------------------------------------------

@app.route("/issues/<int:issue_id>/vote", methods=["POST"])
@login_required
def vote_issue(issue_id):
    connection = get_db_connection()

    if connection is None:
        flash("Database unavailable. Please try again.", "error")
        return redirect(url_for("issues"))

    cursor = None

    try:
        cursor = connection.cursor()

        # Confirm that the issue exists
        cursor.execute(
            "SELECT issue_id FROM issues WHERE issue_id = %s",
            (issue_id,)
        )

        if cursor.fetchone() is None:
            flash("Issue not found.", "error")
            return redirect(url_for("issues"))

        # Check for an existing vote
        cursor.execute("""
            SELECT vote_id
            FROM issue_votes
            WHERE issue_id = %s AND user_id = %s
        """, (issue_id, session["user_id"]))

        if cursor.fetchone():
            flash("You have already upvoted this issue.", "info")
        else:
            cursor.execute("""
                INSERT INTO issue_votes (issue_id, user_id)
                VALUES (%s, %s)
            """, (issue_id, session["user_id"]))

            connection.commit()
            flash("Your upvote has been recorded!", "success")

    except Exception:
        connection.rollback()
        app.logger.exception("Could not record issue vote")
        flash("Unable to record your vote. Please try again.", "error")

    finally:
        if cursor is not None:
            cursor.close()
        connection.close()

    return redirect(url_for("issue_details", issue_id=issue_id))


# --------------------------------------------------
# INTERACTIVE MAP OF REPORTED ISSUES
# --------------------------------------------------

@app.route("/map")
def issue_map():
    connection = get_db_connection()

    if connection is None:
        flash("Database unavailable. Please try again.", "error")
        return redirect(url_for("issues"))

    cursor = None
    map_issues = []

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                issue_id,
                title,
                category,
                locality,
                status,
                latitude,
                longitude
            FROM issues
            WHERE latitude IS NOT NULL
              AND longitude IS NOT NULL
            ORDER BY created_at DESC
        """)

        rows = cursor.fetchall()

        # Only use coordinates within valid geographic ranges.
        for issue in rows:
            try:
                latitude = float(issue["latitude"])
                longitude = float(issue["longitude"])

                if (
                    -90 <= latitude <= 90
                    and -180 <= longitude <= 180
                ):
                    map_issues.append({
                        "issue_id": issue["issue_id"],
                        "title": issue["title"],
                        "category": issue["category"],
                        "locality": issue["locality"],
                        "status": issue["status"],
                        "latitude": latitude,
                        "longitude": longitude
                    })

            except (TypeError, ValueError):
                continue

    except Exception:
        app.logger.exception("Could not load map issues")
        flash("Unable to load map information.", "error")

    finally:
        if cursor is not None:
            cursor.close()
        connection.close()

    return render_template(
        "map.html",
        map_issues=map_issues
    )

# --------------------------------------------------
# ADMIN DASHBOARD
# Only accounts with role='admin' can access it.
# --------------------------------------------------


@app.route("/admin")
def admin_dashboard():
    if not admin_required():
        flash("Admin access is required.", "error")
        return redirect(url_for("login"))

    connection = get_db_connection()

    if connection is None:
        flash("Database unavailable. Please try again.", "error")
        return redirect(url_for("home"))

    categories = [
        "Roads",
        "Garbage",
        "Water",
        "Streetlights",
        "Drainage",
        "Other"
    ]

    all_issues = []
    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT issue_id, title, category, locality,
                   priority, status, created_at
            FROM issues
            ORDER BY created_at DESC
        """)

        all_issues = mark_delayed(cursor.fetchall())

    except Exception:
        app.logger.exception("Could not load admin dashboard")
        flash("Unable to load reports.", "error")

    finally:
        if cursor is not None:
            cursor.close()
        connection.close()

    # Count reports in each category.
    category_counts = {
        category: sum(
            1 for issue in all_issues
            if issue["category"] == category
        )
        for category in categories
    }

    # Keep summary numbers based on ALL reports.
    total_count = len(all_issues)
    progress_count = sum(
        1 for issue in all_issues
        if issue["status"] == "In Progress"
    )
    resolved_count = sum(
        1 for issue in all_issues
        if issue["status"] == "Resolved"
    )

    # Filter reports when a category is selected.
    selected_category = request.args.get("category", "").strip()

    if selected_category not in categories:
        selected_category = ""

    if selected_category:
        issues = [
            issue for issue in all_issues
            if issue["category"] == selected_category
        ]
    else:
        issues = all_issues

    return render_template(
        "admin.html",
        issues=issues,
        categories=categories,
        category_counts=category_counts,
        selected_category=selected_category,
        total_count=total_count,
        progress_count=progress_count,
        resolved_count=resolved_count
    )

# --------------------------------------------------
# UPDATE ISSUE STATUS
# Only admins can change report status.
# --------------------------------------------------


@app.route("/admin/update/<int:issue_id>", methods=["POST"])

def update_issue_status(issue_id):
    if not admin_required():
        flash("Admin access is required.", "error")
        return redirect(url_for("login"))

    new_status = request.form.get("status", "").strip()
    comment = request.form.get("comment", "").strip()
    evidence_photo = request.files.get("evidence_photo")

    allowed_statuses = {"Reported", "In Progress", "Resolved"}

    if new_status not in allowed_statuses or len(comment) > 1000:
        flash("Please provide a valid status and comment.", "error")
        return redirect(url_for("admin_dashboard"))

    # Require a photo for progress and resolution.
    if new_status in {"In Progress", "Resolved"}:
        if not evidence_photo or not evidence_photo.filename:
            if new_status == "Resolved":
                flash(
                    "Upload a resolution photo before marking this issue Resolved.",
                    "error"
                )
            else:
                flash(
                    "Upload a progress photo before marking this issue In Progress.",
                    "error"
                )

            return redirect(url_for("admin_dashboard"))

        if not allowed_file(evidence_photo.filename):
            flash("Use a JPG, JPEG, PNG, or WEBP image.", "error")
            return redirect(url_for("admin_dashboard"))

    connection = get_db_connection()

    if connection is None:
        flash("Database unavailable. Please try again.", "error")
        return redirect(url_for("admin_dashboard"))

    cursor = None
    saved_path = None

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT status
            FROM issues
            WHERE issue_id = %s
        """, (issue_id,))

        issue = cursor.fetchone()

        if issue is None:
            flash("Issue not found.", "error")
            return redirect(url_for("admin_dashboard"))

        old_status = issue["status"]
        photo_path = None

        # Save evidence photo if the new status requires one.
        if new_status in {"In Progress", "Resolved"}:
            safe_name = secure_filename(evidence_photo.filename)

            if not safe_name or "." not in safe_name:
                flash("Please choose a valid image file.", "error")
                return redirect(url_for("admin_dashboard"))

            extension = safe_name.rsplit(".", 1)[1].lower()

            if extension not in ALLOWED_EXTENSIONS:
                flash("Unsupported image format.", "error")
                return redirect(url_for("admin_dashboard"))

            new_filename = f"{uuid.uuid4().hex}.{extension}"

            saved_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                new_filename
            )

            evidence_photo.save(saved_path)
            photo_path = f"uploads/{new_filename}"

        # Update status and the corresponding evidence photo.
        if new_status == "In Progress":
            cursor.execute("""
                UPDATE issues
                SET status = %s,
                    progress_photo_path = %s
                WHERE issue_id = %s
            """, (new_status, photo_path, issue_id))

        elif new_status == "Resolved":
            cursor.execute("""
                UPDATE issues
                SET status = %s,
                    resolution_photo_path = %s
                WHERE issue_id = %s
            """, (new_status, photo_path, issue_id))

        else:
            cursor.execute("""
                UPDATE issues
                SET status = %s
                WHERE issue_id = %s
            """, (new_status, issue_id))

        # Preserve the issue status history.
        cursor.execute("""
            INSERT INTO issue_updates
                (issue_id, updated_by, old_status, new_status, comment)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            issue_id,
            session["user_id"],
            old_status,
            new_status,
            comment or None
        ))

        connection.commit()
        saved_path = None

        flash(
            "Issue status and photo evidence updated successfully.",
            "success"
        )

    except Exception:
        connection.rollback()

        if saved_path and os.path.exists(saved_path):
            try:
                os.remove(saved_path)
            except OSError:
                app.logger.exception("Could not remove an unused upload")

        app.logger.exception("Could not update issue status")
        flash("Unable to update the issue. Please try again.", "error")

    finally:
        if cursor is not None:
            cursor.close()

        connection.close()

    return redirect(url_for("admin_dashboard"))

# --------------------------------------------------
# FILE TOO LARGE ERROR
# --------------------------------------------------

@app.errorhandler(413)
def file_too_large(error):
    flash("Image is too large. Maximum size is 5 MB.", "error")
    return redirect(url_for("report"))


# --------------------------------------------------
# RUN APPLICATION
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
