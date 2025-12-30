
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from dubwizard_shared.models.job import Job
from dubwizard_shared.config import shared_settings

engine = create_engine(shared_settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

print("--- Current Jobs ---")
jobs = session.query(Job).all()
for job in jobs:
    print(f"ID: {job.id}, Status: {job.status}, Created: {job.created_at}")

session.close()
