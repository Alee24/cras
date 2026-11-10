#!/usr/bin/env python
"""
COMPLIANCE RISK ANALYTICS SYSTEM (CRAS)
Unified Runner & Universal Database Migration Manager

Usage:
  python run.py                     # Starts the app, seeds demo data, and opens browser
  python run.py --migrate           # Migrates/creates schema on active database
  python run.py --seed              # Populates live demonstration data for 4 Kenyan SMEs
  python run.py --db "<URL>"        # Runs against any database URI (SQLite or PostgreSQL)
  python run.py --port 5000         # Runs server on a custom port
"""

import sys
import os
import argparse
import webbrowser
import threading
import time
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))


def open_browser(url: str, delay: float = 1.5):
    """Opens browser after server starts."""
    time.sleep(delay)
    try:
        webbrowser.open(url)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="CRAS Runner & Universal Database Migration Tool")
    parser.add_argument("--migrate", action="store_true", help="Run database migrations and seed regulatory content")
    parser.add_argument("--seed", action="store_true", help="Populate 4 Kenyan SME live demo scenarios")
    parser.add_argument("--db", type=str, help="Override database connection URI (e.g. sqlite:///custom.db or postgresql://...)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind server (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000, help="Port to bind server (default: 5000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open web browser")
    args = parser.parse_args()

    # If custom database URI provided, set it in environment before loading app
    if args.db:
        os.environ["DATABASE_URL"] = args.db
        print(f"[CRAS] Target Database: {args.db}")

    # Ensure required directories exist
    (ROOT_DIR / "instance").mkdir(parents=True, exist_ok=True)
    (ROOT_DIR / "uploads").mkdir(parents=True, exist_ok=True)

    from app import create_app, db
    from app.services.seed_data import seed_roles_and_permissions, seed_scoring_policy, seed_regulatory_content
    from app.services.live_demo_generator import populate_comprehensive_live_data

    app = create_app(os.environ.get("FLASK_ENV", "default"))

    with app.app_context():
        # Handle --migrate only
        if args.migrate:
            print("=" * 60)
            print("  CRAS UNIVERSAL DATABASE MIGRATION ENGINE")
            print("=" * 60)
            db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
            print(f"Target Database URI: {db_uri}")
            print("Step 1/3: Verifying tables, foreign keys, indexes, and constraints...")
            db.create_all()
            print("Step 2/3: Synchronizing statutory scoring policy and user roles...")
            seed_roles_and_permissions()
            seed_scoring_policy()
            print("Step 3/3: Synchronizing 43 Kenya statutory regulatory obligations...")
            seed_regulatory_content()
            print("\n[SUCCESS] Database migration completed successfully on target database!")
            return

        # Handle --seed only
        if args.seed:
            print("=" * 60)
            print("  CRAS LIVE DEMONSTRATION DATA SEEDER")
            print("=" * 60)
            stats = populate_comprehensive_live_data(app.config.get("UPLOAD_FOLDER", "uploads"))
            print(f"[SUCCESS] Seeded {stats['organizations']} Kenyan SMEs, {stats['assessments']} assessments, and {stats['gaps']} compliance gaps.")
            return

        # Default action: Full Startup with Auto-Migration and Seeder
        print("=" * 60)
        print("  COMPLIANCE RISK ANALYTICS SYSTEM (CRAS)")
        print("  Regulatory Compliance and Risk Intelligence for SMEs in Kenya")
        print("=" * 60)
        print(f"Active Database: {app.config.get('SQLALCHEMY_DATABASE_URI', '')}")
        print("Initializing database schema...")
        db.create_all()
        seed_roles_and_permissions()
        seed_scoring_policy()
        seed_regulatory_content()
        print("Populating Kenyan SME demonstration records...")
        populate_comprehensive_live_data(app.config.get("UPLOAD_FOLDER", "uploads"))

        app_url = f"http://{args.host}:{args.port}"
        print(f"\n[READY] Server running at: {app_url}")
        print(f"[AUTH]  Default Super Admin: admin@cras.ke / Admin@CRAS2026!")

        if not args.no_browser:
            print("Opening web browser...")
            threading.Thread(target=open_browser, args=(app_url,), daemon=True).start()

        app.run(host=args.host, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
