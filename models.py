from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    datasets = db.relationship("Dataset", backref="owner", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Dataset(db.Model):
    __tablename__ = "datasets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    original_name = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)

    n_rows = db.Column(db.Integer, default=0)
    n_columns = db.Column(db.Integer, default=0)
    file_size_kb = db.Column(db.Float, default=0.0)

    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    # small human note / description user can add
    description = db.Column(db.String(500), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "original_name": self.original_name,
            "n_rows": self.n_rows,
            "n_columns": self.n_columns,
            "file_size_kb": round(self.file_size_kb, 2),
            "uploaded_at": self.uploaded_at.strftime("%d %b %Y, %I:%M %p"),
            "description": self.description or "",
        }


class QueryHistory(db.Model):
    """Keeps a short history of filter/group queries a user runs on a dataset."""
    __tablename__ = "query_history"

    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("datasets.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    query_summary = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
