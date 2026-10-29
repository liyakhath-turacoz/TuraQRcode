"""Project assignment shared by registration, bulk creation, and code editing."""
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from .models import Project, uid, now


def default_project(db, user_id):
    project = db.scalar(select(Project).where(Project.user_id == user_id, Project.is_default.is_(True)))
    if project:
        return project
    # The partial unique index also protects simultaneous first requests.
    db.execute(insert(Project).values(id=uid(), user_id=user_id, name='My project',
               color='#2563eb', is_default=True, created_at=now()).on_conflict_do_nothing(
                   index_elements=['user_id'], index_where=Project.is_default.is_(True)))
    return db.scalar(select(Project).where(Project.user_id == user_id, Project.is_default.is_(True)))
