from datetime import datetime, timedelta
from extensions import db
from drip_campaign import DripEnrollment, DripStep
from services.email_service import send_email

def process_drip_emails():
    """
    Background job to process and send drip emails.
    This function is intended to be run within a Flask app context.
    """
    print(f"[{datetime.utcnow()}] Running drip email scheduler...")
    
    now = datetime.utcnow()
    active_enrollments = DripEnrollment.query.filter(
        DripEnrollment.status == 'active',
        DripEnrollment.next_send_at <= now
    ).all()

    if not active_enrollments:
        print("No drip emails to send at this time.")
        return

    print(f"Found {len(active_enrollments)} emails to send.")

    for enrollment in active_enrollments:
        lead = enrollment.lead
        current_step_details = DripStep.query.filter_by(
            campaign_id=enrollment.campaign_id,
            step_number=enrollment.current_step
        ).first()

        if not lead or not current_step_details:
            enrollment.status = 'stopped'
            print(f"Stopping enrollment {enrollment.id} due to missing lead or step.")
            continue

        if lead.email:
            send_email(
                to_email=lead.email,
                subject=current_step_details.subject,
                body=current_step_details.body
            )

        next_step_details = DripStep.query.filter_by(
            campaign_id=enrollment.campaign_id,
            step_number=enrollment.current_step + 1
        ).first()

        if next_step_details:
            enrollment.current_step += 1
            enrollment.next_send_at = datetime.utcnow() + timedelta(days=next_step_details.delay_days)
        else:
            enrollment.status = 'completed'

    db.session.commit()
    print("Drip email scheduler finished.")