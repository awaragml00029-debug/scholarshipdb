"""Data storage and management."""
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from loguru import logger

from models import Scholarship, ScrapingLog
from database import get_db


class ScholarshipStorage:
    """Handle storage and retrieval of scholarship data."""

    @staticmethod
    def save_scholarship(db: Session, data: Dict) -> Scholarship:
        """Save or update a scholarship record."""
        # Check if scholarship already exists
        existing = db.query(Scholarship).filter(
            Scholarship.source_id == data.get('source_id')
        ).first()

        if existing:
            # Update existing record
            for key, value in data.items():
                if hasattr(existing, key) and value is not None:
                    setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
            logger.debug(f"Updated scholarship: {existing.title}")
            return existing
        else:
            # Create new record
            scholarship = Scholarship(**data)
            db.add(scholarship)
            logger.debug(f"Created new scholarship: {scholarship.title}")
            return scholarship

    @staticmethod
    def save_scholarships_batch(scholarships_data: List[Dict]) -> Dict[str, int]:
        """Save multiple scholarships in a batch."""
        stats = {'new': 0, 'updated': 0, 'errors': 0}

        with get_db() as db:
            for data in scholarships_data:
                try:
                    # Prepare data
                    data['scraped_at'] = datetime.utcnow()

                    # Check if exists
                    source_id = data.get('source_id')
                    if not source_id:
                        logger.warning(f"Scholarship missing source_id: {data.get('title')}")
                        stats['errors'] += 1
                        continue

                    existing = db.query(Scholarship).filter(
                        Scholarship.source_id == source_id
                    ).first()

                    if existing:
                        # Update
                        for key, value in data.items():
                            if hasattr(existing, key) and value is not None:
                                setattr(existing, key, value)
                        existing.updated_at = datetime.utcnow()
                        stats['updated'] += 1
                    else:
                        # Create
                        scholarship = Scholarship(**data)
                        db.add(scholarship)
                        stats['new'] += 1

                    # Commit every 50 records
                    if (stats['new'] + stats['updated']) % 50 == 0:
                        db.commit()

                except Exception as e:
                    logger.error(f"Error saving scholarship: {e}")
                    stats['errors'] += 1
                    db.rollback()

            # Final commit
            db.commit()

        logger.info(f"Saved scholarships - New: {stats['new']}, Updated: {stats['updated']}, Errors: {stats['errors']}")
        return stats

    @staticmethod
    def create_scraping_log() -> int:
        """Create a new scraping log entry."""
        with get_db() as db:
            log = ScrapingLog(
                started_at=datetime.utcnow(),
                status='running'
            )
            db.add(log)
            db.commit()
            db.refresh(log)
            return log.id

    @staticmethod
    def update_scraping_log(log_id: int, **kwargs):
        """Update a scraping log entry."""
        with get_db() as db:
            log = db.query(ScrapingLog).filter(ScrapingLog.id == log_id).first()
            if log:
                for key, value in kwargs.items():
                    if hasattr(log, key):
                        setattr(log, key, value)
                db.commit()

    @staticmethod
    def get_active_scholarships(limit: int = 100) -> List[Scholarship]:
        """Get active scholarships."""
        with get_db() as db:
            scholarships = db.query(Scholarship).filter(
                Scholarship.is_active == True
            ).order_by(
                Scholarship.scraped_at.desc()
            ).limit(limit).all()
            return scholarships

    @staticmethod
    def get_statistics() -> Dict:
        """Get database statistics."""
        with get_db() as db:
            total = db.query(func.count(Scholarship.id)).scalar()
            active = db.query(func.count(Scholarship.id)).filter(
                Scholarship.is_active == True
            ).scalar()

            recent_scrapes = db.query(ScrapingLog).order_by(
                ScrapingLog.started_at.desc()
            ).limit(5).all()

            stats = {
                'total_scholarships': total,
                'active_scholarships': active,
                'recent_scrapes': [
                    {
                        'id': log.id,
                        'started_at': log.started_at.isoformat() if log.started_at else None,
                        'status': log.status,
                        'total': log.total_scholarships,
                        'new': log.new_scholarships,
                    }
                    for log in recent_scrapes
                ]
            }

            return stats

    @staticmethod
    def search_scholarships(
        query: Optional[str] = None,
        country: Optional[str] = None,
        field: Optional[str] = None,
        limit: int = 50
    ) -> List[Scholarship]:
        """Search scholarships with filters."""
        with get_db() as db:
            q = db.query(Scholarship).filter(Scholarship.is_active == True)

            if query:
                q = q.filter(
                    Scholarship.title.ilike(f'%{query}%') |
                    Scholarship.description.ilike(f'%{query}%')
                )

            if country:
                q = q.filter(Scholarship.country.ilike(f'%{country}%'))

            if field:
                q = q.filter(Scholarship.field_of_study.ilike(f'%{field}%'))

            scholarships = q.order_by(Scholarship.scraped_at.desc()).limit(limit).all()
            return scholarships
