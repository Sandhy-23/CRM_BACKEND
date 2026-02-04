import random
from datetime import date, timedelta
from app import app
from extensions import db
from models.crm import Deal
from sqlalchemy import func

def seed_deals_for_analytics():
    """
    Seeds the database with specific sample deals required by the frontend.
    This script will clear existing deals to ensure the final analytics match the target.
    """
    
    deals_data = [
        # Deals pipeline
        {'title': 'CRM Setup', 'pipeline': 'Deals', 'company': 'Acme Corp', 'stage': 'Proposal', 'value': 120000, 'owner': 'Varshini', 'close_date': date(2026, 2, 12)},
        {'title': 'Website Redesign', 'pipeline': 'Deals', 'company': 'Nova Labs', 'stage': 'Won', 'value': 85000, 'owner': 'Ravi', 'close_date': date(2026, 2, 5)},
        # Sales pipeline
        {'title': 'SEO Retainer', 'pipeline': 'Sales', 'company': 'Rankly', 'stage': 'Negotiation', 'value': 60000, 'owner': 'Anu', 'close_date': date(2026, 2, 28)},
        {'title': 'Dashboard Revamp', 'pipeline': 'Sales', 'company': 'Finova', 'stage': 'Won', 'value': 180000, 'owner': 'Ravi', 'close_date': date(2026, 2, 10)},
        # Partnership pipeline
        {'title': 'Agency Tie-up', 'pipeline': 'Partnership', 'company': 'DesignHub', 'stage': 'Proposal', 'value': 0, 'owner': 'Varshini', 'close_date': date(2026, 2, 10)},
        {'title': 'Tech Partner', 'pipeline': 'Partnership', 'company': 'CloudNine', 'stage': 'Negotiation', 'value': 0, 'owner': 'Anu', 'close_date': date(2026, 2, 10)},
        {'title': 'Referral Partner', 'pipeline': 'Partnership', 'company': 'GrowthX', 'stage': 'Won', 'value': 0, 'owner': 'Ravi', 'close_date': date(2026, 2, 10)},
        # Enterprise pipeline
        {'title': 'ERP System', 'pipeline': 'Enterprise', 'company': 'MegaCorp', 'stage': 'Proposal', 'value': 1200000, 'owner': 'Varshini', 'close_date': date(2026, 3, 1)},
        {'title': 'Internal CRM', 'pipeline': 'Enterprise', 'company': 'Axis Group', 'stage': 'Negotiation', 'value': 850000, 'owner': 'Anu', 'close_date': date(2026, 4, 1)},
        {'title': 'AI Platform', 'pipeline': 'Enterprise', 'company': 'OmniTech', 'stage': 'Won', 'value': 1800000, 'owner': 'Ravi', 'close_date': date(2026, 1, 15)},
    ]

    with app.app_context():
        try:
            print("🔥 Clearing existing deals table...")
            db.session.query(Deal).delete()
            
            print(f"🌱 Seeding database with {len(deals_data)} new deals...")
            for deal_data in deals_data:
                db.session.add(Deal(**deal_data))
            
            db.session.commit()
            print("✅ Database seeded successfully with required frontend data!")

            # Verification: Print counts by stage
            print("\n📊 Verification - Current Deal Counts by Stage:")
            stage_counts = db.session.query(Deal.stage, func.count(Deal.id)).group_by(Deal.stage).all()
            for stage, count in stage_counts:
                print(f"   👉 {stage}: {count}")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Error seeding database: {e}")

if __name__ == "__main__":
    seed_deals_for_analytics()