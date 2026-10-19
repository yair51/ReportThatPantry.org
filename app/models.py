from . import db
from flask import url_for
from flask_login import UserMixin
from sqlalchemy.sql import func
from sqlalchemy import event, inspect
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Fallback for pantries without coordinates - most pantries are in Oregon
DEFAULT_TIME_ZONE = 'America/Los_Angeles'
_timezone_finder = None


def time_zone_for_coordinates(latitude, longitude):
    """Return the IANA time zone name (e.g. 'America/Chicago') at a point, or None."""
    global _timezone_finder
    if latitude is None or longitude is None:
        return None
    try:
        if _timezone_finder is None:
            # Loaded on first use - it reads the bundled time zone boundary data
            from timezonefinder import TimezoneFinder
            _timezone_finder = TimezoneFinder()
        return _timezone_finder.timezone_at(lng=longitude, lat=latitude)
    except Exception as e:
        print(f"Time zone lookup failed for ({latitude}, {longitude}): {e}")
        return None


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    first_name = db.Column(db.String(150))
    last_name = db.Column(db.String(150))
    age = db.Column(db.Integer, nullable=True)
    user_type = db.Column(db.String(150))
    notifications = db.relationship('Notification', backref='user')
    locations = db.relationship('Location', backref='user')
    reports = db.relationship('Report', backref='user')


class Location(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    address = db.Column(db.String(150), unique=True)
    city = db.Column(db.String(150), nullable=True)
    state = db.Column(db.String(50), nullable=True)
    zip = db.Column(db.Integer, nullable=True)
    photo = db.Column(db.String(255), nullable=True)
    description = db.Column(db.String(250), nullable=True)
    contact_info = db.Column(db.String(250), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    reports = db.relationship('Report', backref='location')
    notifications = db.relationship('Notification', backref='location')

     # New fields for latitude and longitude
    latitude = db.Column(db.Float, nullable=True)  # Using Float for decimal precision
    longitude = db.Column(db.Float, nullable=True)
    
    # Email-only submission fields
    submitter_email = db.Column(db.String(150), nullable=True)  # Email for non-account users
    submitter_name = db.Column(db.String(150), nullable=True)   # Optional name
    verification_token = db.Column(db.String(50), nullable=True)  # Email verification token
    verified = db.Column(db.Boolean, default=False)  # Whether email is verified
    verified_at = db.Column(db.DateTime(timezone=True), nullable=True)  # When verified
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))
    # IANA time zone name, filled in from latitude/longitude on save. Report times stay stored in UTC;
    # this is only used to show and group them in the pantry's local time.
    time_zone = db.Column(db.String(50), nullable=True)

    def to_local(self, dt):
        """Convert a stored (UTC) datetime to this pantry's local time."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        try:
            zone = ZoneInfo(self.time_zone or DEFAULT_TIME_ZONE)
        except Exception:
            zone = ZoneInfo(DEFAULT_TIME_ZONE)
        return dt.astimezone(zone)


    def to_dict(self):
        return {
            'id': self.location_id,
            'location': f"{self.location_name}<br>{self.address}, {self.city}, {self.state}",
            'status': self.status,
            'time': self.time.strftime("%c")  # Format the datetime object
        }

@event.listens_for(Location, 'before_insert')
@event.listens_for(Location, 'before_update')
def set_location_time_zone(mapper, connection, location):
    # Covers every way a pantry is added or moved (add, edit, email-only submission)
    state = inspect(location)
    coordinates_changed = state.attrs.latitude.history.has_changes() or state.attrs.longitude.history.has_changes()
    if location.time_zone is None or coordinates_changed:
        location.time_zone = time_zone_for_coordinates(location.latitude, location.longitude) or location.time_zone


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pantry_fullness  = db.Column(db.Integer)
    time = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))
    photo = db.Column(db.String(150), nullable=True)
    description = db.Column(db.String(250), nullable=True)
    vision_analysis = db.Column(db.Text, nullable=True)  # Store Vision API results as JSON
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    submitted_by_email = db.Column(db.String(150), nullable=True)  # For non-account submissions

    # Return path to photo on server
    def get_photo_url(self):
        if self.photo:
            return url_for('views.uploaded_file', location_id=self.location_id, filename=self.photo)
        else:
            return None

    # Get interpretation of status based on pantry fullness
    def get_status(self):
        fullness = self.pantry_fullness
        if fullness is None:
            return "Unknown"
        elif fullness > 66:
            return "Full"
        elif fullness > 33:
            return "Half Full"
        else:
            return "Empty"

    # Get parsed Vision API analysis results
    def get_vision_analysis(self):
        if self.vision_analysis:
            try:
                import json
                return json.loads(self.vision_analysis)
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    # Get AI-detected food items as a list
    def get_detected_food_items(self):
        analysis = self.get_vision_analysis()
        if analysis and "food_items" in analysis:
            food_items = analysis["food_items"]
            # Handle both old format (dict with description) and new format (strings)
            if food_items:
                if isinstance(food_items[0], dict):
                    # Old format: list of objects with description field
                    return [item.get("description", str(item)) for item in food_items]
                else:
                    # New format: list of strings
                    return food_items
        return []

    # Get AI-suggested fullness
    def get_ai_fullness_estimate(self):
        analysis = self.get_vision_analysis()
        if analysis:
            return analysis.get("fullness_estimate")
        return None

    # Get organization score
    def get_organization_score(self):
        analysis = self.get_vision_analysis()
        if analysis:
            return analysis.get("organization_score")
        return None



class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    low_inventory = db.Column(db.Boolean, default=True)  # Unused - superseded by notify_on
    unsubscribe_token = db.Column(db.String(100), unique=True, nullable=True)  # Also used for the manage-subscription page
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))
    # When to email: 'empty' = only reports at or below 33% full, 'all' = every report
    notify_on = db.Column(db.String(10), nullable=False, default='empty', server_default='empty')

    NOTIFY_CHOICES = ('empty', 'all')

    def wants_report(self, report):
        return self.notify_on == 'all' or (report.pantry_fullness is not None and report.pantry_fullness <= 33)

    def ensure_token(self):
        # Older subscriptions were created without a token
        if not self.unsubscribe_token:
            import secrets
            self.unsubscribe_token = secrets.token_urlsafe(32)
        return self.unsubscribe_token

