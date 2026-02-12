from extensions import db
from models.campaign import Campaign
from models.campaign_log import CampaignLog
from models.crm import Lead
from models.whatsapp_log import WhatsAppCampaignLog
from services.audience_service import AudienceService
from datetime import datetime
import time
import json

def replace_variables(message, lead):
    if not message: return ""
    message = message.replace("{{name}}", lead.name or "Customer")
    message = message.replace("{{company}}", lead.company or "")
    message = message.replace("{{owner}}", lead.owner or "")
    return message

def send_campaign(campaign_id):
    """
    Background job to execute a campaign.
    """
    # Import app inside function to avoid circular import
    from app import app

    with app.app_context():
        print(f"--- 🚀 STARTING CAMPAIGN {campaign_id} ---")
        
        campaign = Campaign.query.get(campaign_id)
        if not campaign:
            print(f"❌ Campaign {campaign_id} not found.")
            return

        # 1. Update Status to Running
        campaign.status = 'Running'
        db.session.commit()

        try:
            # 2. Fetch Audience (Mock logic: Fetch all leads for org)
            # In production, parse campaign.config['audience']
            config = json.loads(campaign.config) if campaign.config else {}
            audience_type = config.get('audience', 'all')
            
            leads = AudienceService.resolve_audience(audience_type, campaign.organization_id, branch_id=getattr(campaign, 'branch_id', None))
            
            print(f"   -> Found {len(leads)} leads for audience.")

            # 3. Execute Channel Logic
            for lead in leads:
                status = 'sent'
                error_msg = None
                
                try:
                    if campaign.channel.lower() == 'email':
                        # Mock Email Send
                        print(f"      📧 Sending Email to {lead.email}...")
                        time.sleep(0.1) # Simulate network delay
                    
                    elif campaign.channel.lower() == 'whatsapp':
                        # Mock WhatsApp Send
                        print(f"      💬 Sending WhatsApp to {lead.phone}...")
                        
                        # Template Replacement
                        message_body = config.get('message', '')
                        final_message = replace_variables(message_body, lead)
                        print(f"         Content: {final_message}")
                        time.sleep(0.1)
                        
                        # WhatsApp Specific Logging
                        wa_log = WhatsAppCampaignLog(
                            campaign_id=campaign.id, lead_id=lead.id, phone=lead.phone,
                            status='sent', organization_id=campaign.organization_id
                        )
                        db.session.add(wa_log)
                        # Continue to main log or replace? Keeping both for now as per prompt structure request

                    elif campaign.channel.lower() == 'social':
                        # Mock Social Post
                        print(f"      📱 Posting to Social Media...")
                        time.sleep(0.1)
                        # Social usually posts once, not per lead, but keeping structure for now
                        if leads.index(lead) > 0: break 

                except Exception as e:
                    status = 'failed'
                    error_msg = str(e)
                    print(f"      ❌ Failed: {e}")

                # 4. Log Result
                log = CampaignLog(
                    campaign_id=campaign.id,
                    contact_id=lead.id,
                    status=status,
                    channel=campaign.channel,
                    error_message=error_msg
                )
                db.session.add(log)
            
            # 5. Update Status to Completed
            campaign.status = 'Completed'
            db.session.commit()
            print(f"--- ✅ CAMPAIGN {campaign_id} COMPLETED ---")

        except Exception as e:
            print(f"❌ CRITICAL FAILURE IN CAMPAIGN {campaign_id}: {e}")
            campaign.status = 'Failed'
            db.session.commit()

def schedule_campaign_job(campaign_id, run_date):
    from services.scheduler_instance import scheduler
    # Add job to scheduler
    # ID ensures we don't duplicate jobs for the same campaign
    scheduler.add_job(
        func=send_campaign,
        trigger='date',
        run_date=run_date,
        args=[campaign_id],
        id=str(campaign_id),
        replace_existing=True
    )
    print(f"⏰ Job scheduled for Campaign {campaign_id} at {run_date}")