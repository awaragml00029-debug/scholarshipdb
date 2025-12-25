"""Database models for scholarships."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Scholarship(Base):
    """Scholarship model representing a PhD scholarship opportunity."""

    __tablename__ = "scholarships"

    id = Column(Integer, primary_key=True, index=True)

    # Basic Information
    title = Column(String(500), nullable=False, index=True)
    url = Column(String(1000), unique=True, nullable=False, index=True)
    university = Column(String(300), index=True)
    country = Column(String(100), index=True)
    location = Column(String(200))

    # Scholarship Details
    field_of_study = Column(String(200), index=True)
    degree_level = Column(String(50), index=True)  # PhD, Master's, etc.
    description = Column(Text)
    eligibility = Column(Text)
    benefits = Column(Text)

    # Financial Information
    funding_type = Column(String(100))  # Full funding, Partial, etc.
    amount = Column(String(200))  # Scholarship amount
    currency = Column(String(10))

    # Important Dates
    deadline = Column(DateTime, index=True)
    start_date = Column(DateTime)
    application_deadline_text = Column(String(200))  # Original text

    # Status
    is_active = Column(Boolean, default=True, index=True)
    is_verified = Column(Boolean, default=False)

    # Metadata
    source_id = Column(String(100), unique=True, index=True)  # Original ID from source
    scraped_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Additional fields
    requirements = Column(Text)
    application_url = Column(String(1000))
    contact_email = Column(String(200))
    tags = Column(String(500))  # Comma-separated tags

    def __repr__(self):
        return f"<Scholarship(id={self.id}, title='{self.title}', university='{self.university}')>"


class ScrapingLog(Base):
    """Log table for tracking scraping sessions."""

    __tablename__ = "scraping_logs"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime)
    status = Column(String(50))  # success, failed, partial
    total_pages = Column(Integer, default=0)
    total_scholarships = Column(Integer, default=0)
    new_scholarships = Column(Integer, default=0)
    updated_scholarships = Column(Integer, default=0)
    error_message = Column(Text)

    def __repr__(self):
        return f"<ScrapingLog(id={self.id}, status='{self.status}', total={self.total_scholarships})>"
