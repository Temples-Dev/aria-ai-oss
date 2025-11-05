#!/usr/bin/env python3
"""
Database management script for ARIA.
"""

import os
import sys
import argparse
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, text

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(__file__))

from app.database.database import DATABASE_URL, engine, SessionLocal
from app.database.models import *


def create_migration(message: str):
    """Create a new migration."""
    alembic_cfg = Config("alembic.ini")
    command.revision(alembic_cfg, autogenerate=True, message=message)
    print(f"Created migration: {message}")


def run_migrations():
    """Run all pending migrations."""
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    print("Migrations completed successfully")


def rollback_migration(revision: str = "-1"):
    """Rollback to a specific migration."""
    alembic_cfg = Config("alembic.ini")
    command.downgrade(alembic_cfg, revision)
    print(f"Rolled back to revision: {revision}")


def show_migration_history():
    """Show migration history."""
    alembic_cfg = Config("alembic.ini")
    command.history(alembic_cfg)


def show_current_revision():
    """Show current database revision."""
    alembic_cfg = Config("alembic.ini")
    command.current(alembic_cfg)


def reset_database():
    """Reset database (drop all tables and recreate)."""
    print("WARNING: This will drop all tables and data!")
    confirm = input("Are you sure? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Aborted.")
        return
    
    # Drop all tables
    from app.database.database import Base
    Base.metadata.drop_all(bind=engine)
    print("Dropped all tables")
    
    # Run migrations to recreate
    run_migrations()
    print("Database reset completed")


def seed_database():
    """Seed database with initial data."""
    db = SessionLocal()
    try:
        # Check if data already exists
        existing_context = db.query(UserContext).filter_by(user_id="default_user").first()
        if existing_context:
            print("Database already seeded")
            return
        
        # Insert initial user context data
        initial_contexts = [
            UserContext(
                user_id="default_user",
                context_key="voice_preference",
                context_value={"voice": "cmu_us_slt_cg", "rate": 150, "volume": 0.8},
                context_type="preference",
                importance_score=8
            ),
            UserContext(
                user_id="default_user",
                context_key="wake_words",
                context_value=["aria", "hey aria", "ok aria", "hello aria"],
                context_type="preference",
                importance_score=9
            ),
            UserContext(
                user_id="default_user",
                context_key="greeting_style",
                context_value={"formal": False, "time_aware": True, "context_aware": True},
                context_type="preference",
                importance_score=7
            ),
            UserContext(
                user_id="default_user",
                context_key="interaction_history",
                context_value={"total_conversations": 0, "favorite_topics": [], "common_times": []},
                context_type="memory",
                importance_score=6
            )
        ]
        
        for context in initial_contexts:
            db.add(context)
        
        db.commit()
        print("Database seeded successfully")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()


def check_database_connection():
    """Check database connection."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")
            print(f"Database URL: {DATABASE_URL}")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="ARIA Database Management")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Migration commands
    migrate_parser = subparsers.add_parser("migrate", help="Run migrations")
    
    create_parser = subparsers.add_parser("create-migration", help="Create new migration")
    create_parser.add_argument("message", help="Migration message")
    
    rollback_parser = subparsers.add_parser("rollback", help="Rollback migration")
    rollback_parser.add_argument("--revision", default="-1", help="Revision to rollback to")
    
    # History commands
    subparsers.add_parser("history", help="Show migration history")
    subparsers.add_parser("current", help="Show current revision")
    
    # Database commands
    subparsers.add_parser("reset", help="Reset database (drop all tables)")
    subparsers.add_parser("seed", help="Seed database with initial data")
    subparsers.add_parser("check", help="Check database connection")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute commands
    if args.command == "migrate":
        run_migrations()
    elif args.command == "create-migration":
        create_migration(args.message)
    elif args.command == "rollback":
        rollback_migration(args.revision)
    elif args.command == "history":
        show_migration_history()
    elif args.command == "current":
        show_current_revision()
    elif args.command == "reset":
        reset_database()
    elif args.command == "seed":
        seed_database()
    elif args.command == "check":
        check_database_connection()


if __name__ == "__main__":
    main()
