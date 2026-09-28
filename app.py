from flask import render_template_string
import os
import sqlite3
from functools import wraps
from datetime import datetime
from flask import (
    Flask, request, redirect, url_for, session,
    render_template_string, flash
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "greater-grace-change-this-secret"
)

app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

DATABASE = "church.db"
UPLOAD_FOLDER = "static/uploads"

CHURCH_NAME = "Greater Grace Church"
CHURCH_NUMBER = "078 586 0846"

SUPER_ADMIN_WHATSAPP = "0785860846"

ALLOWED_IMAGE = {
    "png", "jpg", "jpeg", "gif", "webp"
}

ALLOWED_VIDEO = {
    "mp4", "webm", "mov", "m4v"
}

ALLOWED_AUDIO = {
    "mp3", "wav", "m4a", "ogg"
}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# =========================================================
# DATABASE
# =========================================================

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def add_column_if_missing(db, table, column, definition):
    columns = [
        row["name"]
        for row in db.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()
    ]

    if column not in columns:
        db.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )


def init_db():

    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            whatsapp TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'member',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            post_type TEXT NOT NULL,
            media_url TEXT,
            author_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(author_id) REFERENCES users(id)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            event_date TEXT NOT NULL,
            description TEXT,
            created_by INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(created_by) REFERENCES users(id)
        )
    """)

    # Add extra event fields to older databases.
    add_column_if_missing(
        db, "events", "event_time", "TEXT"
    )

    add_column_if_missing(
        db, "events", "location", "TEXT"
    )

    # Add sermon information to older databases.
    add_column_if_missing(
        db, "posts", "preacher", "TEXT"
    )

    db.commit()
    db.close()


# =========================================================
# HELPERS
# =========================================================

def clean_whatsapp(number):
    return (
        number
        .strip()
        .replace(" ", "")
        .replace("-", "")
    )


def current_user():

    user_id = session.get("user_id")

    if not user_id:
        return None

    db = get_db()

    user = db.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    db.close()

    return user


def login_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        if not current_user():
            flash("Please log in first.")
            return redirect(url_for("login"))

        return view(*args, **kwargs)

    return wrapped


def admin_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        user = current_user()

        if not user:
            flash("Please log in first.")
            return redirect(url_for("login"))

        if user["role"] not in ("admin", "super_admin"):
            flash("Admin access required.")
            return redirect(url_for("home"))

        return view(*args, **kwargs)

    return wrapped


def super_admin_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        user = current_user()

        if not user:
            return redirect(url_for("login"))

        if user["role"] != "super_admin":
            flash("Only the Super Admin can do that.")
            return redirect(url_for("admin"))

        return view(*args, **kwargs)

    return wrapped


def allowed_file(filename, allowed):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in allowed
    )


def save_upload(file, allowed):

    if not file or not file.filename:
        return None

    if not allowed_file(file.filename, allowed):
        return None

    original = secure_filename(file.filename)

    extension = original.rsplit(".", 1)[1].lower()

    unique_name = (
        datetime.now().strftime("%Y%m%d%H%M%S%f")
        + "."
        + extension
    )

    path = os.path.join(
        UPLOAD_FOLDER,
        unique_name
    )

    file.save(path)

    return url_for(
        "static",
        filename="uploads/" + unique_name
    )


# =========================================================
# DESIGN
# =========================================================

BASE = """
<!DOCTYPE html>
<html>
<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>{{ title }} - Greater Grace Church</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f3f4f6;
    color: #111827;
}

nav {
    background: #172554;
    color: white;
    padding: 14px;
    position: sticky;
    top: 0;
    z-index: 100;
}

.nav-inner {
    max-width: 1150px;
    margin: auto;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
}

.brand {
    font-weight: bold;
    font-size: 20px;
}

nav a {
    color: white;
    text-decoration: none;
    margin: 4px;
    display: inline-block;
}

.container {
    max-width: 1150px;
    margin: auto;
    padding: 20px;
}

.hero {
    background: linear-gradient(
        135deg,
        #172554,
        #3730a3
    );

    color: white;
    text-align: center;
    padding: 70px 20px;
}

.hero h1 {
    font-size: 42px;
    margin: 0 0 12px;
}

.hero p {
    font-size: 19px;
}

.btn {
    display: inline-block;
    padding: 12px 18px;
    border: 0;
    border-radius: 8px;
    background: #facc15;
    color: #111827;
    text-decoration: none;
    font-weight: bold;
    cursor: pointer;
    margin: 4px;
}

.btn-blue {
    background: #2563eb;
    color: white;
}

.btn-red {
    background: #dc2626;
    color: white;
}

.btn-green {
    background: #16a34a;
    color: white;
}

.card {
    background: white;
    padding: 20px;
    border-radius: 14px;
    margin: 15px 0;
    box-shadow: 0 2px 10px rgba(0,0,0,.07);
}

.grid {
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(230px, 1fr));
    gap: 16px;
}

input,
textarea,
select {
    width: 100%;
    padding: 13px;
    margin: 7px 0 15px;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    font-size: 16px;
}

textarea {
    min-height: 130px;
}

label {
    font-weight: bold;
}

.message {
    background: #dbeafe;
    border-left: 5px solid #2563eb;
    padding: 12px;
    margin: 15px 0;
    border-radius: 8px;
}

.media {
    width: 100%;
    max-height: 550px;
    object-fit: cover;
    border-radius: 12px;
}

.video {
    width: 100%;
    max-height: 550px;
    border-radius: 12px;
}

.meta {
    color: #6b7280;
    font-size: 14px;
}

.badge {
    display: inline-block;
    padding: 5px 9px;
    background: #e0e7ff;
    color: #3730a3;
    border-radius: 20px;
    font-size: 13px;
}

footer {
    background: #111827;
    color: white;
    text-align: center;
    padding: 35px 15px;
    margin-top: 40px;
}

@media(max-width:700px) {

    .nav-inner {
        display: block;
    }

    .hero h1 {
        font-size: 32px;
    }

    nav a {
        font-size: 14px;
    }
}

</style>

</head>

<body>

<nav>

<div class="nav-inner">

<div class="brand">
Greater Grace Church
</div>

<div>

<a href="{{ url_for('home') }}">Home</a>

<a href="{{ url_for('gallery') }}">Gallery</a>

<a href="{{ url_for('videos') }}">Videos</a>

<a href="{{ url_for('sermons') }}">Sermons</a>

<a href="{{ url_for('events') }}">Events</a>

{% if user %}

<a href="{{ url_for('dashboard') }}">
Dashboard
</a>

{% if user['role'] in ['admin','super_admin'] %}

<a href="{{ url_for('admin') }}">
Admin
</a>

{% endif %}

<a href="{{ url_for('logout') }}">
Logout
</a>

{% else %}

<a href="{{ url_for('login') }}">
Login
</a>

<a href="{{ url_for('register') }}">
Register
</a>

{% endif %}

</div>

</div>

</nav>


{% with messages = get_flashed_messages() %}

{% if messages %}

<div class="container">

{% for message in messages %}

<div class="message">
{{ message }}
</div>

{% endfor %}

</div>

{% endif %}

{% endwith %}


{{ content|safe }}


<footer>

<h3>Greater Grace Church</h3>

<p>
Growing in Grace • Walking in Faith • Reaching the World
</p>

<p>
WhatsApp: {{ church_number }}
</p>

</footer>

</body>
</html>
"""


def page(title, content):

    return render_template_string(
        BASE,
        title=title,
        content=content,
        user=current_user(),
        church_number=CHURCH_NUMBER
    )


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    db = get_db()

    posts = db.execute("""
        SELECT posts.*, users.full_name
        FROM posts
        JOIN users
        ON users.id = posts.author_id
        ORDER BY posts.id DESC
        LIMIT 8
    """).fetchall()

    events = db.execute("""
        SELECT events.*, users.full_name
        FROM events
        JOIN users
        ON users.id = events.created_by
        ORDER BY event_date ASC
        LIMIT 5
    """).fetchall()

    db.close()

    content = render_template_string("""

<section class="hero">

<h1>Greater Grace Church</h1>

<p>
Growing in Grace • Walking in Faith • Reaching the World
</p>

{% if not user %}

<a class="btn"
   href="{{ url_for('register') }}">
Join Our Online Church Community
</a>

<a class="btn btn-blue"
   href="{{ url_for('login') }}">
Member Login
</a>

{% endif %}

</section>


<div class="container">

<div class="card">

<h2>Welcome to Greater Grace Church</h2>

<p>
Stay connected with our church family online.
See our latest announcements, photos, videos,
sermons and upcoming events.
</p>

</div>


<h2>📢 Latest Church Updates</h2>

{% if posts %}

{% for post in posts %}

<div class="card">

<span class="badge">
{{ post['post_type']|upper }}
</span>

<h2>
{{ post['title'] }}
</h2>

{% if post['content'] %}

<p>
{{ post['content'] }}
</p>

{% endif %}


{% if post['post_type'] == 'photo'
      and post['media_url'] %}

<img class="media"
     src="{{ post['media_url'] }}">

{% endif %}


{% if post['post_type'] == 'video'
      and post['media_url'] %}

<video class="video"
       controls
       src="{{ post['media_url'] }}">
</video>

{% endif %}


{% if post['post_type'] == 'sermon' %}

{% if post['preacher'] %}

<p>
<strong>Preacher:</strong>
{{ post['preacher'] }}
</p>

{% endif %}

{% if post['media_url'] %}

<a class="btn btn-blue"
   href="{{ post['media_url'] }}"
   target="_blank">
🎙️ Open Sermon
</a>

{% endif %}

{% endif %}


<p class="meta">
Posted by {{ post['full_name'] }}
•
{{ post['created_at'] }}
</p>

</div>

{% endfor %}

{% else %}

<div class="card">
<p>No church updates yet.</p>
</div>

{% endif %}


<h2>📅 Upcoming Events</h2>

{% if events %}

{% for event in events %}

<div class="card">

<h3>
{{ event['title'] }}
</h3>

<p>
<strong>Date:</strong>
{{ event['event_date'] }}
</p>

{% if event['event_time'] %}

<p>
<strong>Time:</strong>
{{ event['event_time'] }}
</p>

{% endif %}

{% if event['location'] %}

<p>
<strong>Location:</strong>
{{ event['location'] }}
</p>

{% endif %}

<p>
{{ event['description'] or '' }}
</p>

</div>

{% endfor %}

{% else %}

<div class="card">
<p>No upcoming events yet.</p>
</div>

{% endif %}

</div>

""", posts=posts, events=events, user=current_user())

    return page("Home", content)


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        full_name = request.form.get(
            "full_name", ""
        ).strip()

        whatsapp = clean_whatsapp(
            request.form.get("whatsapp", "")
        )

        password = request.form.get(
            "password", ""
        )

        if not full_name or not whatsapp or not password:

            flash("Please complete all fields.")

            return redirect(url_for("register"))

        if len(password) < 6:

            flash(
                "Password must contain at least 6 characters."
            )

            return redirect(url_for("register"))

        db = get_db()

        existing = db.execute(
            "SELECT id FROM users WHERE whatsapp = ?",
            (whatsapp,)
        ).fetchone()

        if existing:

            db.close()

            flash(
                "That WhatsApp number is already registered."
            )

            return redirect(url_for("login"))

        role = "member"

        if whatsapp == SUPER_ADMIN_WHATSAPP:

            role = "super_admin"

        db.execute("""
            INSERT INTO users
            (
                full_name,
                whatsapp,
                password_hash,
                role
            )
            VALUES (?, ?, ?, ?)
        """, (
            full_name,
            whatsapp,
            generate_password_hash(password),
            role
        ))

        db.commit()
        db.close()

        flash(
            "Registration successful. Please log in."
        )

        return redirect(url_for("login"))

    content = """

<div class="container">

<div class="card">

<h2>👤 Create Church Account</h2>

<p>
Register using your name and WhatsApp number.
</p>

<form method="POST">

<label>Full Name</label>

<input
type="text"
name="full_name"
placeholder="Your full name"
required
>


<label>WhatsApp Number</label>

<input
type="text"
name="whatsapp"
placeholder="0785860846"
required
>


<label>Password</label>

<input
type="password"
name="password"
placeholder="At least 6 characters"
required
>


<button class="btn btn-blue"
        type="submit">
Register
</button>

</form>

</div>

</div>

"""

    return page("Register", content)


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        whatsapp = clean_whatsapp(
            request.form.get("whatsapp", "")
        )

        password = request.form.get(
            "password", ""
        )

        db = get_db()

        user = db.execute(
            "SELECT * FROM users WHERE whatsapp = ?",
            (whatsapp,)
        ).fetchone()

        db.close()

        if user and check_password_hash(
            user["password_hash"],
            password
        ):

            session["user_id"] = user["id"]

            flash(
                "Welcome back, "
                + user["full_name"]
                + "!"
            )

            return redirect(url_for("dashboard"))

        flash(
            "Incorrect WhatsApp number or password."
        )

    content = """

<div class="container">

<div class="card">

<h2>🔐 Member Login</h2>

<form method="POST">

<label>WhatsApp Number</label>

<input
type="text"
name="whatsapp"
placeholder="0785860846"
required
>


<label>Password</label>

<input
type="password"
name="password"
required
>


<button class="btn btn-blue"
        type="submit">
Login
</button>

</form>

<p>
Don't have an account?
<a href="/register">Register here</a>
</p>

</div>

</div>

"""

    return page("Login", content)


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    flash("You have been logged out.")

    return redirect(url_for("home"))


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
@login_required
def dashboard():

    user = current_user()

    content = render_template_string("""

<div class="container">

<div class="card">

<h2>
Welcome, {{ user['full_name'] }} 👋
</h2>

<p>
Your Greater Grace Church account is active.
</p>

<p>
<strong>Account:</strong>
{{ user['role'] }}
</p>

</div>


<div class="grid">

<div class="card">

<h3>📸 Gallery</h3>

<p>
View church photos.
</p>

<a class="btn btn-blue"
   href="{{ url_for('gallery') }}">
Open Gallery
</a>

</div>


<div class="card">

<h3>🎥 Videos</h3>

<p>
Watch church videos.
</p>

<a class="btn btn-blue"
   href="{{ url_for('videos') }}">
Watch Videos
</a>

</div>


<div class="card">

<h3>🎙️ Sermons</h3>

<p>
Access church sermons.
</p>

<a class="btn btn-blue"
   href="{{ url_for('sermons') }}">
View Sermons
</a>

</div>


<div class="card">

<h3>📅 Events</h3>

<p>
See upcoming church events.
</p>

<a class="btn btn-blue"
   href="{{ url_for('events') }}">
View Events
</a>

</div>

</div>


{% if user['role'] in ['admin','super_admin'] %}

<div class="card">

<h2>🛡️ Admin Access</h2>

<p>
You can publish church content.
</p>

<a class="btn btn-blue"
   href="{{ url_for('admin') }}">
Open Admin Dashboard
</a>

</div>

{% endif %}

</div>

""", user=user)

    return page("Dashboard", content)


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin")
@admin_required
def admin():

    db = get_db()

    users = db.execute("""
        SELECT *
        FROM users
        ORDER BY id DESC
    """).fetchall()

    posts = db.execute("""
        SELECT posts.*, users.full_name
        FROM posts
        JOIN users
        ON users.id = posts.author_id
        ORDER BY posts.id DESC
    """).fetchall()

    events = db.execute("""
        SELECT events.*, users.full_name
        FROM events
        JOIN users
        ON users.id = events.created_by
        ORDER BY events.id DESC
    """).fetchall()

    db.close()

    content = render_template_string("""

<div class="container">

<h1>🛡️ Church Admin Dashboard</h1>


<div class="grid">


<div class="card">

<h3>📢 Announcement</h3>

<p>
Publish church news and announcements.
</p>

<a class="btn btn-blue"
   href="{{ url_for('new_post') }}">
Create Post
</a>

</div>


<div class="card">

<h3>📸 Photo</h3>

<p>
Upload photos from church activities.
</p>

<a class="btn btn-blue"
   href="{{ url_for('new_post') }}">
Upload Photo
</a>

</div>


<div class="card">

<h3>🎥 Video</h3>

<p>
Upload a church video.
</p>

<a class="btn btn-blue"
   href="{{ url_for('new_post') }}">
Upload Video
</a>

</div>


<div class="card">

<h3>🎙️ Sermon</h3>

<p>
Publish a sermon.
</p>

<a class="btn btn-blue"
   href="{{ url_for('new_post') }}">
Add Sermon
</a>

</div>


<div class="card">

<h3>📅 Event</h3>

<p>
Create an upcoming church event.
</p>

<a class="btn btn-blue"
   href="{{ url_for('new_event') }}">
Add Event
</a>

</div>


</div>


{% if user['role'] == 'super_admin' %}

<div class="card">

<h2>👥 Member Management</h2>

{% for member in users %}

<p>

<strong>
{{ member['full_name'] }}
</strong>

<br>

WhatsApp:
{{ member['whatsapp'] }}

<br>

Role:
<strong>
{{ member['role'] }}
</strong>

</p>


{% if member['role'] == 'member' %}

<form method="POST"
action="{{ url_for('make_admin', user_id=member['id']) }}">

<button class="btn btn-blue"
type="submit">

Make Admin

</button>

</form>

{% elif member['role'] == 'admin' %}

<form method="POST"
action="{{ url_for('make_member', user_id=member['id']) }}">

<button class="btn btn-red"
type="submit">

Remove Admin

</button>

</form>

{% endif %}

<hr>

{% endfor %}

</div>

{% endif %}


<div class="card">

<h2>📢 Published Content</h2>

{% for post in posts %}

<p>

<strong>
{{ post['title'] }}
</strong>

<br>

Type:
{{ post['post_type'] }}

<br>

Posted by:
{{ post['full_name'] }}

</p>

<form method="POST"
action="{{ url_for('delete_post', post_id=post['id']) }}">

<button class="btn btn-red"
type="submit">

Delete Post

</button>

</form>

<hr>

{% else %}

<p>No posts yet.</p>

{% endfor %}

</div>


<div class="card">

<h2>📅 Events</h2>

{% for event in events %}

<p>

<strong>
{{ event['title'] }}
</strong>

<br>

{{ event['event_date'] }}

</p>

<form method="POST"
action="{{ url_for('delete_event', event_id=event['id']) }}">

<button class="btn btn-red"
type="submit">

Delete Event

</button>

</form>

<hr>

{% else %}

<p>No events yet.</p>

{% endfor %}

</div>

</div>

""",
        users=users,
        posts=posts,
        events=events,
        user=current_user()
    )

    return page("Admin", content)


# =========================================================
# MAKE ADMIN
# =========================================================

@app.route(
    "/admin/make-admin/<int:user_id>",
    methods=["POST"]
)
@super_admin_required
def make_admin(user_id):

    db = get_db()

    db.execute(
        "UPDATE users SET role = 'admin' WHERE id = ?",
        (user_id,)
    )

    db.commit()
    db.close()

    flash("Member is now an Admin.")

    return redirect(url_for("admin"))


# =========================================================
# REMOVE ADMIN
# =========================================================

@app.route(
    "/admin/make-member/<int:user_id>",
    methods=["POST"]
)
@super_admin_required
def make_member(user_id):

    db = get_db()

    user = db.execute(
        "SELECT role FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    if user and user["role"] == "super_admin":

        db.close()

        flash(
            "The Super Admin cannot be removed."
        )

        return redirect(url_for("admin"))

    db.execute(
        "UPDATE users SET role = 'member' WHERE id = ?",
        (user_id,)
    )

    db.commit()
    db.close()

    flash("Admin access removed.")

    return redirect(url_for("admin"))


# =========================================================
# NEW POST
# =========================================================

@app.route(
    "/admin/post/new",
    methods=["GET", "POST"]
)
@admin_required
def new_post():

    if request.method == "POST":

        title = request.form.get(
            "title", ""
        ).strip()

        content = request.form.get(
            "content", ""
        ).strip()

        post_type = request.form.get(
            "post_type",
            "announcement"
        )

        preacher = request.form.get(
            "preacher",
            ""
        ).strip()

        media_url = request.form.get(
            "media_url",
            ""
        ).strip()

        uploaded_url = None

        # Photo upload
        if post_type == "photo":

            uploaded_url = save_upload(
                request.files.get("media_file"),
                ALLOWED_IMAGE
            )

        # Video upload
        elif post_type == "video":

            uploaded_url = save_upload(
                request.files.get("media_file"),
                ALLOWED_VIDEO
            )

        # Sermon audio upload
        elif post_type == "sermon":

            uploaded_url = save_upload(
                request.files.get("media_file"),
                ALLOWED_AUDIO
            )

        if uploaded_url:
            media_url = uploaded_url

        if not title:

            flash("Please enter a title.")

            return redirect(
                url_for("new_post")
            )

        user = current_user()

        db = get_db()

        db.execute("""
            INSERT INTO posts
            (
                title,
                content,
                post_type,
                media_url,
                author_id,
                preacher
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            title,
            content,
            post_type,
            media_url,
            user["id"],
            preacher
        ))

        db.commit()
        db.close()

        flash(
            "Church content published successfully."
        )

        return redirect(url_for("admin"))


    content = """

<div class="container">

<div class="card">

<h2>📢 Publish Church Content</h2>

<form method="POST"
      enctype="multipart/form-data">


<label>Title</label>

<input
type="text"
name="title"
placeholder="Sunday Service"
required
>


<label>Message / Description</label>

<textarea
name="content"
placeholder="Write the church message..."
></textarea>


<label>Content Type</label>

<select name="post_type"
        id="post_type">

<option value="announcement">
📢 Announcement
</option>

<option value="photo">
📸 Photo
</option>

<option value="video">
🎥 Video
</option>

<option value="sermon">
🎙️ Sermon
</option>

</select>


<label>Preacher
(sermons only)</label>

<input
type="text"
name="preacher"
placeholder="Name of preacher"
>


<label>Upload File</label>

<input
type="file"
name="media_file"
accept="image/*,video/*,audio/*"
>


<p>
For a sermon, you can upload an audio file.
For a video, upload an MP4/video file.
For a photo, upload an image.
</p>


<label>
OR paste a media link
</label>

<input
type="url"
name="media_url"
placeholder="https://..."
>


<button
class="btn btn-blue"
type="submit">

Publish

</button>

</form>

</div>

</div>

"""

    return page(
        "Publish Content",
        content
    )


# =========================================================
# NEW EVENT
# =========================================================

@app.route(
    "/admin/event/new",
    methods=["GET", "POST"]
)
@admin_required
def new_event():

    if request.method == "POST":

        title = request.form.get(
            "title", ""
        ).strip()

        event_date = request.form.get(
            "event_date", ""
        ).strip()

        event_time = request.form.get(
            "event_time", ""
        ).strip()

        location = request.form.get(
            "location", ""
        ).strip()

        description = request.form.get(
            "description", ""
        ).strip()

        if not title or not event_date:

            flash(
                "Event title and date are required."
            )

            return redirect(
                url_for("new_event")
            )

        user = current_user()

        db = get_db()

        db.execute("""
            INSERT INTO events
            (
                title,
                event_date,
                event_time,
                location,
                description,
                created_by
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            title,
            event_date,
            event_time,
            location,
            description,
            user["id"]
        ))

        db.commit()
        db.close()

        flash("Event added successfully.")

        return redirect(
            url_for("admin")
        )


    content = """

<div class="container">

<div class="card">

<h2>📅 Add Church Event</h2>

<form method="POST">

<label>Event Name</label>

<input
type="text"
name="title"
placeholder="Youth Sunday"
required
>


<label>Date</label>

<input
type="date"
name="event_date"
required
>


<label>Time</label>

<input
type="time"
name="event_time"
>


<label>Location</label>

<input
type="text"
name="location"
placeholder="Church auditorium"
>


<label>Description</label>

<textarea
name="description"
placeholder="Event information..."
></textarea>


<button
class="btn btn-blue"
type="submit">

Add Event

</button>

</form>

</div>

</div>

"""

    return page(
        "Add Event",
        content
    )


# =========================================================
# GALLERY
# =========================================================

@app.route("/gallery")
def gallery():

    db = get_db()

    photos = db.execute("""
        SELECT posts.*, users.full_name
        FROM posts
        JOIN users
        ON users.id = posts.author_id
        WHERE post_type = 'photo'
        ORDER BY posts.id DESC
    """).fetchall()

    db.close()

    content = render_template_string("""

<div class="container">

<h1>📸 Church Gallery</h1>

<p>
Photos from Greater Grace Church services
and activities.
</p>

<div class="grid">

{% for photo in photos %}

<div class="card">

{% if photo['media_url'] %}

<img class="media"
     src="{{ photo['media_url'] }}">

{% endif %}

<h3>
{{ photo['title'] }}
</h3>

<p>
{{ photo['content'] or '' }}
</p>

<p class="meta">
{{ photo['created_at'] }}
</p>

</div>

{% else %}

<div class="card">

<p>
No church photos have been uploaded yet.
</p>

</div>

{% endfor %}

</div>

</div>

""", photos=photos)

    return page(
        "Gallery",
        content
    )


# =========================================================
# VIDEOS
# =========================================================

@app.route("/videos")
def videos():

    db = get_db()

    videos = db.execute("""
        SELECT posts.*, users.full_name
        FROM posts
        JOIN users
        ON users.id = posts.author_id
        WHERE post_type = 'video'
        ORDER BY posts.id DESC
    """).fetchall()

    db.close()

    content = render_template_string("""

<div class="container">

<h1>🎥 Church Videos</h1>

{% for video in videos %}

<div class="card">

<h2>
{{ video['title'] }}
</h2>

{% if video['media_url'] %}

<video
class="video"
controls
src="{{ video['media_url'] }}">
</video>

{% endif %}

<p>
{{ video['content'] or '' }}
</p>

<p class="meta">
Posted by {{ video['full_name'] }}
•
{{ video['created_at'] }}
</p>

</div>

{% else %}

<div class="card">
<p>
No church videos have been uploaded yet.
</p>
</div>

{% endfor %}

</div>

""", videos=videos)

    return page(
        "Videos",
        content
    )


# =========================================================
# SERMONS
# =========================================================

@app.route("/sermons")
def sermons():

    db = get_db()

    sermons = db.execute("""
        SELECT posts.*, users.full_name
        FROM posts
        JOIN users
        ON users.id = posts.author_id
        WHERE post_type = 'sermon'
        ORDER BY posts.id DESC
    """).fetchall()

    db.close()

    content = render_template_string("""

<div class="container">

<h1>🎙️ Sermons</h1>

{% for sermon in sermons %}

<div class="card">

<h2>
{{ sermon['title'] }}
</h2>

{% if sermon['preacher'] %}

<p>
<strong>Preacher:</strong>
{{ sermon['preacher'] }}
</p>

{% endif %}

<p>
{{ sermon['content'] or '' }}
</p>


{% if sermon['media_url'] %}

<a
class="btn btn-blue"
href="{{ sermon['media_url'] }}"
target="_blank">

🎧 Listen / Open Sermon

</a>

{% endif %}


<p class="meta">
{{ sermon['created_at'] }}
</p>

</div>

{% else %}

<div class="card">

<p>
No sermons have been published yet.
</p>

</div>

{% endfor %}

</div>

""", sermons=sermons)

    return page(
        "Sermons",
        content
    )


# =========================================================
# EVENTS
# =========================================================

@app.route("/events")
def events():

    db = get_db()

    events_list = db.execute("""
        SELECT events.*, users.full_name
        FROM events
        JOIN users
        ON users.id = events.created_by
        ORDER BY event_date ASC
    """).fetchall()

    db.close()

    content = render_template_string("""

<div class="container">

<h1>📅 Church Events</h1>

{% for event in events_list %}

<div class="card">

<h2>
{{ event['title'] }}
</h2>

<p>
<strong>📅 Date:</strong>
{{ event['event_date'] }}
</p>

{% if event['event_time'] %}

<p>
<strong>⏰ Time:</strong>
{{ event['event_time'] }}
</p>

{% endif %}

{% if event['location'] %}

<p>
<strong>📍 Location:</strong>
{{ event['location'] }}
</p>

{% endif %}

<p>
{{ event['description'] or '' }}
</p>

</div>

{% else %}

<div class="card">

<p>
No events have been added yet.
</p>

</div>

{% endfor %}

</div>

""", events_list=events_list)

    return page(
        "Events",
        content
    )


# =========================================================
# DELETE POST
# =========================================================

@app.route(
    "/admin/post/delete/<int:post_id>",
    methods=["POST"]
)
@admin_required
def delete_post(post_id):

    db = get_db()

    db.execute(
        "DELETE FROM posts WHERE id = ?",
        (post_id,)
    )

    db.commit()
    db.close()

    flash("Post deleted.")

    return redirect(url_for("admin"))


# =========================================================
# DELETE EVENT
# =========================================================

@app.route(
    "/admin/event/delete/<int:event_id>",
    methods=["POST"]
)
@admin_required
def delete_event(event_id):

    db = get_db()

    db.execute(
        "DELETE FROM events WHERE id = ?",
        (event_id,)
    )

    db.commit()
    db.close()

    flash("Event deleted.")

    return redirect(url_for("admin"))


# =========================================================
# START
# =========================================================

init_db()




# ============================================================
# PRAYER_SYSTEM_START
# Greater Grace Church - Prayer Request System
# ============================================================

@app.route("/prayer-request", methods=["GET", "POST"])
def prayer_request():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("church.db")
    conn.row_factory = sqlite3.Row

    user = conn.execute(
        "SELECT id, full_name, whatsapp FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()

    if not user:
        conn.close()
        session.clear()
        return redirect(url_for("login"))

    if request.method == "POST":
        prayer_text = request.form.get("request", "").strip()

        if not prayer_text:
            conn.close()
            return render_template_string(PRAYER_FORM_HTML,
                user=user,
                message="Please write your prayer request.",
                success=False
            )

        conn.execute(
            """
            INSERT INTO prayer_requests
            (user_id, full_name, whatsapp, request)
            VALUES (?, ?, ?, ?)
            """,
            (
                user["id"],
                user["full_name"],
                user["whatsapp"],
                prayer_text
            )
        )
        conn.commit()
        conn.close()

        return render_template_string(PRAYER_FORM_HTML,
            user=user,
            message="🙏 Your prayer request has been submitted successfully. Our church team will pray with you.",
            success=True
        )

    conn.close()

    return render_template_string(
        PRAYER_FORM_HTML,
        user=user,
        message="",
        success=False
    )


PRAYER_FORM_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Prayer Request - Greater Grace Church</title>

<style>
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f4f6f8;
    color: #222;
}

.header {
    background: #111827;
    color: white;
    padding: 22px 16px;
    text-align: center;
}

.header h1 {
    margin: 0;
    font-size: 25px;
}

.header p {
    margin: 7px 0 0;
    opacity: .9;
}

.container {
    max-width: 650px;
    margin: 25px auto;
    padding: 0 15px;
}

.card {
    background: white;
    padding: 22px;
    border-radius: 15px;
    box-shadow: 0 3px 12px rgba(0,0,0,.08);
}

h2 {
    margin-top: 0;
}

label {
    display: block;
    margin-top: 15px;
    margin-bottom: 7px;
    font-weight: bold;
}

input,
textarea {
    width: 100%;
    padding: 13px;
    border: 1px solid #d1d5db;
    border-radius: 9px;
    font-size: 16px;
}

textarea {
    min-height: 180px;
    resize: vertical;
}

button {
    width: 100%;
    margin-top: 18px;
    padding: 14px;
    border: none;
    border-radius: 9px;
    background: #111827;
    color: white;
    font-size: 16px;
    font-weight: bold;
}

.success {
    background: #dcfce7;
    color: #166534;
    padding: 13px;
    border-radius: 9px;
    margin-bottom: 15px;
}

.error {
    background: #fee2e2;
    color: #991b1b;
    padding: 13px;
    border-radius: 9px;
    margin-bottom: 15px;
}

.back {
    display: block;
    text-align: center;
    margin-top: 18px;
    text-decoration: none;
    color: #111827;
    font-weight: bold;
}

.info {
    background: #f3f4f6;
    padding: 12px;
    border-radius: 9px;
    margin-bottom: 15px;
}
</style>
</head>

<body>

<div class="header">
    <h1>🙏 Greater Grace Church</h1>
    <p>Prayer Request</p>
</div>

<div class="container">
    <div class="card">

        <h2>Submit a Prayer Request</h2>

        <p>
            We believe in the power of prayer.
            Share your prayer request with our church family.
        </p>

        {% if message %}
            <div class="{{ 'success' if success else 'error' }}">
                {{ message }}
            </div>
        {% endif %}

        <div class="info">
            <strong>Name:</strong> {{ user["full_name"] }}<br>
            <strong>WhatsApp:</strong> {{ user["whatsapp"] }}
        </div>

        <form method="POST">

            <label>Prayer Request</label>

            <textarea
                name="request"
                placeholder="Write your prayer request here..."
                required></textarea>

            <button type="submit">
                🙏 Submit Prayer Request
            </button>

        </form>

        <a class="back" href="{{ url_for('dashboard') }}">
            ← Back to Dashboard
        </a>

    </div>
</div>

</body>
</html>
"""


@app.route("/admin/prayer-requests")
def admin_prayer_requests():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("church.db")
    conn.row_factory = sqlite3.Row

    user = conn.execute(
        "SELECT role FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()

    if not user or user["role"] not in ("admin", "super_admin"):
        conn.close()
        return "Access denied", 403

    prayers = conn.execute(
        """
        SELECT *
        FROM prayer_requests
        ORDER BY created_at DESC
        """
    ).fetchall()

    conn.close()

    return render_template_string(
        ADMIN_PRAYER_HTML,
        prayers=prayers
    )


@app.route("/admin/prayer-requests/delete/<int:prayer_id>", methods=["POST"])
def delete_prayer_request(prayer_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("church.db")
    conn.row_factory = sqlite3.Row

    user = conn.execute(
        "SELECT role FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()

    if not user or user["role"] not in ("admin", "super_admin"):
        conn.close()
        return "Access denied", 403

    conn.execute(
        "DELETE FROM prayer_requests WHERE id = ?",
        (prayer_id,)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("admin_prayer_requests"))


ADMIN_PRAYER_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>Prayer Requests - Admin</title>

<style>
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f3f4f6;
}

.header {
    background: #111827;
    color: white;
    padding: 22px 15px;
    text-align: center;
}

.container {
    max-width: 850px;
    margin: 25px auto;
    padding: 0 15px;
}

.card {
    background: white;
    padding: 18px;
    margin-bottom: 18px;
    border-radius: 14px;
    box-shadow: 0 3px 10px rgba(0,0,0,.07);
}

.request {
    white-space: pre-wrap;
    background: #f9fafb;
    padding: 13px;
    border-radius: 9px;
    margin-top: 12px;
}

.meta {
    color: #555;
    font-size: 14px;
    line-height: 1.6;
}

button {
    margin-top: 12px;
    padding: 10px 15px;
    border: none;
    border-radius: 8px;
    background: #b91c1c;
    color: white;
    font-weight: bold;
}

.back {
    display: inline-block;
    margin-bottom: 18px;
    text-decoration: none;
    color: #111827;
    font-weight: bold;
}
</style>
</head>

<body>

<div class="header">
    <h1>🙏 Prayer Requests</h1>
    <p>Greater Grace Church Admin</p>
</div>

<div class="container">

<a class="back" href="{{ url_for('admin') }}">
← Back to Admin Dashboard
</a>

{% if prayers %}

    {% for prayer in prayers %}

    <div class="card">

        <h3>{{ prayer["full_name"] }}</h3>

        <div class="meta">
            📱 {{ prayer["whatsapp"] }}<br>
            📅 {{ prayer["created_at"] }}
        </div>

        <div class="request">
            {{ prayer["request"] }}
        </div>

        <form method="POST"
              action="{{ url_for('delete_prayer_request', prayer_id=prayer['id']) }}"
              onsubmit="return confirm('Delete this prayer request?');">

            <button type="submit">
                Delete Request
            </button>

        </form>

    </div>

    {% endfor %}

{% else %}

    <div class="card">
        <h3>No prayer requests yet.</h3>
        <p>New requests submitted by members will appear here.</p>
    </div>

{% endif %}

</div>

</body>
</html>
"""

# ============================================================
# PRAYER_SYSTEM_END
# ============================================================


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )

