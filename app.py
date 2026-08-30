import os
import uuid
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, Response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)
# Read secrets from environment variables (set these in .env on the server).
# Fallbacks are for local development only.
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///floors.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = os.path.join(app.static_folder, "uploads")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max upload

# Admin credentials (set these via environment variables in production)
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "svg", "webp"}

db = SQLAlchemy(app)

# Ensure upload folder exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


# --- Models ---

class Floor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, default="")
    order = db.Column(db.Integer, default=0)
    images = db.relationship("Image", backref="floor", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Floor {self.name}>"


class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(255), default="")
    floor_id = db.Column(db.Integer, db.ForeignKey("floor.id"), nullable=False)

    def __repr__(self):
        return f"<Image {self.original_name}>"


class Slide(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    subtitle = db.Column(db.String(300), default="")
    image_filename = db.Column(db.String(255), default="")
    order = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<Slide {self.title}>"


class Offer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    image_filename = db.Column(db.String(255), default="")
    is_active = db.Column(db.Boolean, default=True)
    whatsapp_message = db.Column(db.String(300), default="Hi, I'm interested in your offer")

    def __repr__(self):
        return f"<Offer {self.title}>"


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, default="")
    image_filename = db.Column(db.String(255), default="")
    is_active = db.Column(db.Boolean, default=True)
    order = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<Post {self.title}>"


class VisitorCount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    count = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<VisitorCount {self.count}>"


class BookingInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), default="")
    cab_phone = db.Column(db.String(20), default="")
    heading = db.Column(db.String(200), default="Book Your Stay")
    subtext = db.Column(db.String(300), default="Call us now to reserve your room!")

    def __repr__(self):
        return f"<BookingInfo {self.phone}>"


# --- Helpers ---

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# --- Public Routes ---

@app.before_request
def count_visitor():
    # Skip counting for static files, SEO files, and dashboard
    if request.endpoint in ("static", "robots_txt", "sitemap_xml") or (request.path or "").startswith("/dashboard"):
        return
    # Only count unique visits per session
    if not session.get("counted"):
        visitor = VisitorCount.query.first()
        if visitor:
            visitor.count += 1
        else:
            visitor = VisitorCount(count=1)
            db.session.add(visitor)
        db.session.commit()
        session["counted"] = True


@app.context_processor
def inject_visitor_count():
    visitor = VisitorCount.query.first()
    booking = BookingInfo.query.first()
    return dict(
        visitor_count=visitor.count if visitor else 0,
        booking_info=booking
    )

@app.route("/")
def home():
    floors = Floor.query.order_by(Floor.order).all()
    slides = Slide.query.order_by(Slide.order).all()
    active_offer = Offer.query.filter_by(is_active=True).first()
    posts = Post.query.filter_by(is_active=True).order_by(Post.order).all()
    return render_template("home.html", floors=floors, slides=slides, active_offer=active_offer, posts=posts)


@app.route("/about")
def about():
    active_offer = Offer.query.filter_by(is_active=True).first()
    return render_template("about.html", active_offer=active_offer)


@app.route("/services")
def services():
    active_offer = Offer.query.filter_by(is_active=True).first()
    return render_template("services.html", active_offer=active_offer)


@app.route("/contact")
def contact():
    active_offer = Offer.query.filter_by(is_active=True).first()
    return render_template("contact.html", active_offer=active_offer)


@app.route("/floor/<int:floor_id>")
def floor_detail(floor_id):
    floor = Floor.query.get_or_404(floor_id)
    return render_template("floor.html", floor=floor)


@app.route("/post/<int:post_id>")
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    active_offer = Offer.query.filter_by(is_active=True).first()
    return render_template("post.html", post=post, active_offer=active_offer)


# --- SEO Routes ---

@app.route("/robots.txt")
def robots_txt():
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /dashboard",
        "Disallow: /login",
        "Disallow: /logout",
        f"Sitemap: {request.url_root}sitemap.xml",
    ]
    return Response("\n".join(lines), mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap_xml():
    pages = []
    base = request.url_root.rstrip("/")

    # Static pages
    for endpoint in ["home", "about", "services", "contact"]:
        pages.append({"loc": base + url_for(endpoint), "priority": "0.8"})

    # Floor pages
    for floor in Floor.query.all():
        pages.append({"loc": base + url_for("floor_detail", floor_id=floor.id), "priority": "0.6"})

    # Active post pages
    for post in Post.query.filter_by(is_active=True).all():
        pages.append({"loc": base + url_for("post_detail", post_id=post.id), "priority": "0.5"})

    xml = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for page in pages:
        xml.append("  <url>")
        xml.append(f"    <loc>{page['loc']}</loc>")
        xml.append(f"    <changefreq>weekly</changefreq>")
        xml.append(f"    <priority>{page['priority']}</priority>")
        xml.append("  </url>")
    xml.append("</urlset>")

    return Response("\n".join(xml), mimetype="application/xml")


# --- Auth ---

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            flash("Please log in to access the dashboard.", "error")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Both username and password are required.", "error")
            return render_template("login.html")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["logged_in"] = True
            session["username"] = username
            flash(f"Welcome back, {username}!", "success")
            next_url = request.args.get("next") or url_for("dashboard")
            return redirect(next_url)
        else:
            flash("Invalid username or password.", "error")
            return render_template("login.html")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# --- Dashboard Routes ---

@app.route("/dashboard")
@login_required
def dashboard():
    floors = Floor.query.order_by(Floor.order).all()
    slides = Slide.query.order_by(Slide.order).all()
    offers = Offer.query.all()
    posts = Post.query.order_by(Post.order).all()
    booking = BookingInfo.query.first()
    return render_template("dashboard/index.html", floors=floors, slides=slides, offers=offers, posts=posts, booking=booking)


@app.route("/dashboard/floor/add", methods=["GET", "POST"])
@login_required
def dashboard_add_floor():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        order = request.form.get("order", 0, type=int)

        if not name:
            flash("Floor name is required.", "error")
            return render_template("dashboard/floor_form.html", floor=None)

        floor = Floor(name=name, description=description, order=order)
        db.session.add(floor)
        db.session.commit()
        flash(f"Floor '{name}' created successfully!", "success")
        return redirect(url_for("dashboard"))

    return render_template("dashboard/floor_form.html", floor=None)


@app.route("/dashboard/floor/<int:floor_id>/edit", methods=["GET", "POST"])
@login_required
def dashboard_edit_floor(floor_id):
    floor = Floor.query.get_or_404(floor_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        order = request.form.get("order", 0, type=int)

        if not name:
            flash("Floor name is required.", "error")
            return render_template("dashboard/floor_form.html", floor=floor)

        floor.name = name
        floor.description = description
        floor.order = order
        db.session.commit()
        flash(f"Floor '{name}' updated successfully!", "success")
        return redirect(url_for("dashboard"))

    return render_template("dashboard/floor_form.html", floor=floor)


@app.route("/dashboard/floor/<int:floor_id>/delete", methods=["POST"])
@login_required
def dashboard_delete_floor(floor_id):
    floor = Floor.query.get_or_404(floor_id)

    # Delete all associated image files
    for image in floor.images:
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], image.filename)
        if os.path.exists(filepath):
            os.remove(filepath)

    db.session.delete(floor)
    db.session.commit()
    flash(f"Floor '{floor.name}' deleted successfully!", "success")
    return redirect(url_for("dashboard"))


@app.route("/dashboard/floor/<int:floor_id>/images", methods=["GET"])
@login_required
def dashboard_images(floor_id):
    floor = Floor.query.get_or_404(floor_id)
    # If requested via AJAX, return partial HTML
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render_template("dashboard/images_partial.html", floor=floor)
    return render_template("dashboard/images.html", floor=floor)


@app.route("/dashboard/floor/<int:floor_id>/images/upload", methods=["POST"])
@login_required
def dashboard_upload_image(floor_id):
    floor = Floor.query.get_or_404(floor_id)

    if "images" not in request.files:
        flash("No files selected.", "error")
        return redirect(url_for("dashboard_images", floor_id=floor_id))

    files = request.files.getlist("images")
    uploaded_count = 0

    for file in files:
        if file and file.filename and allowed_file(file.filename):
            original_name = secure_filename(file.filename)
            # Generate unique filename to avoid conflicts
            ext = original_name.rsplit(".", 1)[1].lower()
            unique_name = f"{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
            file.save(filepath)

            image = Image(filename=unique_name, original_name=original_name, floor_id=floor_id)
            db.session.add(image)
            uploaded_count += 1

    db.session.commit()

    if uploaded_count > 0:
        flash(f"{uploaded_count} image(s) uploaded successfully!", "success")
    else:
        flash("No valid images were uploaded. Allowed: png, jpg, jpeg, gif, svg, webp", "error")

    return redirect(url_for("dashboard", show_images=floor_id))


@app.route("/dashboard/image/<int:image_id>/delete", methods=["POST"])
@login_required
def dashboard_delete_image(image_id):
    image = Image.query.get_or_404(image_id)
    floor_id = image.floor_id

    # Delete file from disk
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], image.filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    db.session.delete(image)
    db.session.commit()
    flash("Image deleted successfully!", "success")
    return redirect(url_for("dashboard", show_images=floor_id))


@app.route("/dashboard/image/<int:image_id>/caption", methods=["POST"])
@login_required
def dashboard_update_image_caption(image_id):
    image = Image.query.get_or_404(image_id)
    caption = request.form.get("caption", "").strip()
    image.caption = caption
    db.session.commit()
    flash("Image name updated!", "success")
    return redirect(url_for("dashboard", show_images=image.floor_id))


# --- Slider Management Routes ---

@app.route("/dashboard/slide/add", methods=["POST"])
@login_required
def dashboard_add_slide():
    title = request.form.get("title", "").strip()
    subtitle = request.form.get("subtitle", "").strip()
    order = request.form.get("order", 0, type=int)

    if not title:
        flash("Slide title is required.", "error")
        return redirect(url_for("dashboard", tab="slider"))

    # Handle image upload
    image_filename = ""
    if "slide_image" in request.files:
        file = request.files["slide_image"]
        if file and file.filename and allowed_file(file.filename):
            ext = secure_filename(file.filename).rsplit(".", 1)[1].lower()
            unique_name = f"slide_{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
            file.save(filepath)
            image_filename = unique_name

    slide = Slide(title=title, subtitle=subtitle, image_filename=image_filename, order=order)
    db.session.add(slide)
    db.session.commit()
    flash(f"Slide '{title}' added successfully!", "success")
    return redirect(url_for("dashboard", tab="slider"))


@app.route("/dashboard/slide/<int:slide_id>/edit", methods=["POST"])
@login_required
def dashboard_edit_slide(slide_id):
    slide = Slide.query.get_or_404(slide_id)

    title = request.form.get("title", "").strip()
    subtitle = request.form.get("subtitle", "").strip()
    order = request.form.get("order", 0, type=int)

    if not title:
        flash("Slide title is required.", "error")
        return redirect(url_for("dashboard", tab="slider"))

    slide.title = title
    slide.subtitle = subtitle
    slide.order = order

    # Handle image upload (replace existing)
    if "slide_image" in request.files:
        file = request.files["slide_image"]
        if file and file.filename and allowed_file(file.filename):
            # Delete old image if exists
            if slide.image_filename:
                old_path = os.path.join(app.config["UPLOAD_FOLDER"], slide.image_filename)
                if os.path.exists(old_path):
                    os.remove(old_path)

            ext = secure_filename(file.filename).rsplit(".", 1)[1].lower()
            unique_name = f"slide_{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
            file.save(filepath)
            slide.image_filename = unique_name

    db.session.commit()
    flash(f"Slide '{title}' updated successfully!", "success")
    return redirect(url_for("dashboard", tab="slider"))


@app.route("/dashboard/slide/<int:slide_id>/delete", methods=["POST"])
@login_required
def dashboard_delete_slide(slide_id):
    slide = Slide.query.get_or_404(slide_id)

    # Delete image file
    if slide.image_filename:
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], slide.image_filename)
        if os.path.exists(filepath):
            os.remove(filepath)

    db.session.delete(slide)
    db.session.commit()
    flash("Slide deleted successfully!", "success")
    return redirect(url_for("dashboard", tab="slider"))


# --- Offer Management Routes ---

@app.route("/dashboard/offer/add", methods=["POST"])
@login_required
def dashboard_add_offer():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    whatsapp_message = request.form.get("whatsapp_message", "Hi, I'm interested in your offer").strip()

    if not title:
        flash("Offer title is required.", "error")
        return redirect(url_for("dashboard", tab="offers"))

    # Handle image upload
    image_filename = ""
    if "offer_image" in request.files:
        file = request.files["offer_image"]
        if file and file.filename and allowed_file(file.filename):
            ext = secure_filename(file.filename).rsplit(".", 1)[1].lower()
            unique_name = f"offer_{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
            file.save(filepath)
            image_filename = unique_name

    offer = Offer(title=title, description=description, image_filename=image_filename, whatsapp_message=whatsapp_message, is_active=True)
    db.session.add(offer)
    db.session.commit()
    flash(f"Offer '{title}' added successfully!", "success")
    return redirect(url_for("dashboard", tab="offers"))


@app.route("/dashboard/offer/<int:offer_id>/edit", methods=["POST"])
@login_required
def dashboard_edit_offer(offer_id):
    offer = Offer.query.get_or_404(offer_id)

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    whatsapp_message = request.form.get("whatsapp_message", "").strip()

    if not title:
        flash("Offer title is required.", "error")
        return redirect(url_for("dashboard", tab="offers"))

    offer.title = title
    offer.description = description
    offer.whatsapp_message = whatsapp_message

    # Handle image upload (replace existing)
    if "offer_image" in request.files:
        file = request.files["offer_image"]
        if file and file.filename and allowed_file(file.filename):
            # Delete old image if exists
            if offer.image_filename:
                old_path = os.path.join(app.config["UPLOAD_FOLDER"], offer.image_filename)
                if os.path.exists(old_path):
                    os.remove(old_path)

            ext = secure_filename(file.filename).rsplit(".", 1)[1].lower()
            unique_name = f"offer_{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
            file.save(filepath)
            offer.image_filename = unique_name

    db.session.commit()
    flash(f"Offer '{title}' updated successfully!", "success")
    return redirect(url_for("dashboard", tab="offers"))


@app.route("/dashboard/offer/<int:offer_id>/toggle", methods=["POST"])
@login_required
def dashboard_toggle_offer(offer_id):
    offer = Offer.query.get_or_404(offer_id)
    offer.is_active = not offer.is_active
    db.session.commit()
    status = "activated" if offer.is_active else "deactivated"
    flash(f"Offer '{offer.title}' {status}!", "success")
    return redirect(url_for("dashboard", tab="offers"))


@app.route("/dashboard/offer/<int:offer_id>/delete", methods=["POST"])
@login_required
def dashboard_delete_offer(offer_id):
    offer = Offer.query.get_or_404(offer_id)

    # Delete image file
    if offer.image_filename:
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], offer.image_filename)
        if os.path.exists(filepath):
            os.remove(filepath)

    db.session.delete(offer)
    db.session.commit()
    flash("Offer deleted successfully!", "success")
    return redirect(url_for("dashboard", tab="offers"))


# --- Post Management Routes ---

@app.route("/dashboard/post/add", methods=["POST"])
@login_required
def dashboard_add_post():
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    order = request.form.get("order", 0, type=int)

    if not title:
        flash("Post title is required.", "error")
        return redirect(url_for("dashboard", tab="posts"))

    # Handle image upload
    image_filename = ""
    if "post_image" in request.files:
        file = request.files["post_image"]
        if file and file.filename and allowed_file(file.filename):
            ext = secure_filename(file.filename).rsplit(".", 1)[1].lower()
            unique_name = f"post_{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
            file.save(filepath)
            image_filename = unique_name

    post = Post(title=title, content=content, image_filename=image_filename, order=order, is_active=True)
    db.session.add(post)
    db.session.commit()
    flash(f"Post '{title}' added successfully!", "success")
    return redirect(url_for("dashboard", tab="posts"))


@app.route("/dashboard/post/<int:post_id>/edit", methods=["POST"])
@login_required
def dashboard_edit_post(post_id):
    post = Post.query.get_or_404(post_id)

    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    order = request.form.get("order", 0, type=int)

    if not title:
        flash("Post title is required.", "error")
        return redirect(url_for("dashboard", tab="posts"))

    post.title = title
    post.content = content
    post.order = order

    # Handle image upload (replace existing)
    if "post_image" in request.files:
        file = request.files["post_image"]
        if file and file.filename and allowed_file(file.filename):
            # Delete old image if exists
            if post.image_filename:
                old_path = os.path.join(app.config["UPLOAD_FOLDER"], post.image_filename)
                if os.path.exists(old_path):
                    os.remove(old_path)

            ext = secure_filename(file.filename).rsplit(".", 1)[1].lower()
            unique_name = f"post_{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
            file.save(filepath)
            post.image_filename = unique_name

    db.session.commit()
    flash(f"Post '{title}' updated successfully!", "success")
    return redirect(url_for("dashboard", tab="posts"))


@app.route("/dashboard/post/<int:post_id>/toggle", methods=["POST"])
@login_required
def dashboard_toggle_post(post_id):
    post = Post.query.get_or_404(post_id)
    post.is_active = not post.is_active
    db.session.commit()
    status = "enabled" if post.is_active else "disabled"
    flash(f"Post '{post.title}' {status}!", "success")
    return redirect(url_for("dashboard", tab="posts"))


@app.route("/dashboard/post/<int:post_id>/delete", methods=["POST"])
@login_required
def dashboard_delete_post(post_id):
    post = Post.query.get_or_404(post_id)

    # Delete image file
    if post.image_filename:
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], post.image_filename)
        if os.path.exists(filepath):
            os.remove(filepath)

    db.session.delete(post)
    db.session.commit()
    flash("Post deleted successfully!", "success")
    return redirect(url_for("dashboard", tab="posts"))


# --- Booking Info Route ---

@app.route("/dashboard/booking/update", methods=["POST"])
@login_required
def dashboard_update_booking():
    phone = request.form.get("phone", "").strip()
    cab_phone = request.form.get("cab_phone", "").strip()
    heading = request.form.get("heading", "").strip()
    subtext = request.form.get("subtext", "").strip()

    booking = BookingInfo.query.first()
    if not booking:
        booking = BookingInfo()
        db.session.add(booking)

    booking.phone = phone
    booking.cab_phone = cab_phone
    booking.heading = heading or "Book Your Stay"
    booking.subtext = subtext or "Call us now to reserve your room!"
    db.session.commit()
    flash("Booking info updated successfully!", "success")
    return redirect(url_for("dashboard", tab="booking"))


# --- Initialize Database ---

with app.app_context():
    db.create_all()

    # Seed default floors if database is empty
    if Floor.query.count() == 0:
        default_floors = [
            Floor(name="First Floor", description="First floor images", order=1),
            Floor(name="Second Floor", description="Second floor images", order=2),
            Floor(name="Third Floor", description="Third floor images", order=3),
        ]
        db.session.add_all(default_floors)
        db.session.commit()

    # Seed default slides if database is empty
    if Slide.query.count() == 0:
        default_slides = [
            Slide(title="Welcome to Our Website", subtitle="We provide the best solutions for your business needs", order=1),
            Slide(title="Professional Services", subtitle="Expert team delivering quality results every time", order=2),
            Slide(title="Get In Touch", subtitle="Contact us today to discuss your next project", order=3),
        ]
        db.session.add_all(default_slides)
        db.session.commit()

    # Initialize visitor counter
    if VisitorCount.query.count() == 0:
        db.session.add(VisitorCount(count=0))
        db.session.commit()

    # Initialize booking info
    if BookingInfo.query.count() == 0:
        db.session.add(BookingInfo(phone="+91-9439139083", cab_phone="+91-9776177794", heading="Book Your Stay", subtext="Call us now to reserve your room!"))
        db.session.commit()


if __name__ == "__main__":
    # Debug is OFF by default. Enable locally with FLASK_DEBUG=True.
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    app.run(debug=debug_mode)
