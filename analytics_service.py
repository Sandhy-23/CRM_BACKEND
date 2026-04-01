from extensions import db
from sqlalchemy import text

# -------------------- REVENUE --------------------

def get_revenue_analytics():
    engine_name = db.engine.name
    if engine_name == 'mysql':
        month_func = "MONTH(close_date)"
    else:  # sqlite
        month_func = "strftime('%m', close_date)"

    query = text(f"""
        SELECT {month_func} as month,
               SUM(value)
        FROM deals
        WHERE stage = 'Won'
        GROUP BY month
        ORDER BY month
    """)
    
    with db.engine.connect() as connection:
        result = connection.execute(query)
        rows = result.fetchall()

    months = ["Jan","Feb","Mar","Apr","May","Jun",
              "Jul","Aug","Sep","Oct","Nov","Dec"]

    revenue_data = []

    for row in rows:
        if row[0] is not None:
            month_index = int(row[0]) - 1
            revenue_data.append({
                "name": months[month_index],
                "revenue": row[1] or 0
            })

    return {"revenueData": revenue_data}


# -------------------- PIPELINE --------------------

def get_pipeline_analytics():
    with db.engine.connect() as connection:
        # Deals by stage
        stages_result = connection.execute(text("SELECT stage, COUNT(*) FROM deals GROUP BY stage"))
        stages = stages_result.fetchall()

        # Win vs Loss
        win_row = connection.execute(text("SELECT COUNT(*) FROM deals WHERE stage='Won'")).fetchone()
        win = win_row[0] if win_row else 0

        loss_row = connection.execute(text("SELECT COUNT(*) FROM deals WHERE stage='Lost'")).fetchone()
        loss = loss_row[0] if loss_row else 0

        # Funnel
        total_leads_row = connection.execute(text("SELECT COUNT(*) FROM leads")).fetchone()
        total_leads = total_leads_row[0] if total_leads_row else 0

        qualified_row = connection.execute(text("SELECT COUNT(*) FROM leads WHERE status != 'New'")).fetchone()
        qualified = qualified_row[0] if qualified_row else 0

        proposed_row = connection.execute(text("SELECT COUNT(*) FROM deals WHERE stage='Proposal'")).fetchone()
        proposed = proposed_row[0] if proposed_row else 0

        negotiating_row = connection.execute(text("SELECT COUNT(*) FROM deals WHERE stage='Negotiation'")).fetchone()
        negotiating = negotiating_row[0] if negotiating_row else 0

    return {
        "pipelineStages": [
            {"stage": s[0], "value": s[1]} for s in stages
        ],
        "winLossData": [
            {"name": "Win", "value": win},
            {"name": "Loss", "value": loss}
        ],
        "funnelData": [
            {"name": "Leads", "value": total_leads},
            {"name": "Qualified", "value": qualified},
            {"name": "Proposal", "value": proposed},
            {"name": "Negotiation", "value": negotiating},
            {"name": "Closed Won", "value": win}
        ]
    }


# -------------------- LEADS --------------------

def get_lead_analytics():
    engine_name = db.engine.name
    if engine_name == 'mysql':
        week_func = "WEEK(created_at, 1)"
    else:  # sqlite
        week_func = "strftime('%W', created_at)"

    trend_query = text(f"""
        SELECT {week_func} as week,
               COUNT(*)
        FROM leads
        GROUP BY week
        ORDER BY week
    """)

    with db.engine.connect() as connection:
        # Source
        sources_result = connection.execute(text("SELECT source, COUNT(*) FROM leads GROUP BY source"))
        sources = sources_result.fetchall()

        # Status
        statuses_result = connection.execute(text("SELECT status, COUNT(*) FROM leads GROUP BY status"))
        statuses = statuses_result.fetchall()

        # Trend (Weekly)
        trends_result = connection.execute(trend_query)
        trends = trends_result.fetchall()

    return {
        "leadSourceData": [
            {"name": s[0], "value": s[1]} for s in sources
        ],
        "leadStatusData": [
            {"name": s[0], "count": s[1]} for s in statuses
        ],
        "leadTrendData": [
            {"name": f"Week {t[0]}", "count": t[1]} for t in trends
        ]
    }


# -------------------- KPI --------------------

def get_kpi_analytics():
    engine_name = db.engine.name
    
    with db.engine.connect() as connection:
        total_leads_row = connection.execute(text("SELECT COUNT(*) FROM leads")).fetchone()
        total_leads = total_leads_row[0] if total_leads_row else 0

        won_deals_row = connection.execute(text("SELECT COUNT(*) FROM deals WHERE stage='Won'")).fetchone()
        won_deals = won_deals_row[0] if won_deals_row else 0
        
        # Added for Dashboard Summary Cards
        if engine_name == 'sqlite':
             # SQLite doesn't strictly enforce case sensitivity like MySQL might depending on collation, but safer to be explicit
             active_deals_row = connection.execute(text("SELECT COUNT(*) FROM deals WHERE status != 'won' AND status != 'lost'")).fetchone()
        else:
             active_deals_row = connection.execute(text("SELECT COUNT(*) FROM deals WHERE status != 'won' AND status != 'lost'")).fetchone()
        active_deals = active_deals_row[0] if active_deals_row else 0

        revenue_row = connection.execute(text("SELECT SUM(value) FROM deals WHERE stage='Won'")).fetchone()
        total_revenue = revenue_row[0] if revenue_row and revenue_row[0] else 0

        conversion = 0
        if total_leads > 0:
            conversion = round((won_deals / total_leads) * 100, 2)

        # Assuming 'activities' table exists or using 'tasks' as proxy based on existing models
        # Using 'tasks' table as per existing context
        total_activities_row = connection.execute(text("SELECT COUNT(*) FROM tasks")).fetchone()
        total_activities = total_activities_row[0] if total_activities_row else 0

        # Task status removed, defaulting completed to 0
        completed = 0

        task_percent = 0
        if total_activities > 0:
            task_percent = round((completed / total_activities) * 100, 2)

    return {
        "totalLeads": total_leads,
        "activeDeals": active_deals,
        "totalRevenue": total_revenue,
        "kpis": {
            "leadConversion": {
                "value": f"{conversion}%",
                "trend": ""
            },
            "avgCostPerLead": {
                "value": "N/A",
                "trend": ""
            },
            "avgResponseTime": {
                "value": "N/A",
                "status": ""
            },
            "totalActivities": {
                "value": str(total_activities),
                "trend": ""
            },
            "tasksCompleted": {
                "value": f"{task_percent}%",
                "status": "Active"
            }
        }
    }

# -------------------- RECENT ACTIVITIES --------------------

def get_recent_activities():
    # Queries the audit_logs table for the latest actions
    query = text("""
        SELECT id, action, module, user_name, created_at, record_name
        FROM audit_logs
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    with db.engine.connect() as connection:
        rows = connection.execute(query).fetchall()
        
    return [
        {
            "id": row[0],
            "action": f"{row[1]} {row[2]}", # e.g. "Created Lead"
            "user": row[3] or "System",
            "details": row[5],
            "time": row[4].strftime("%Y-%m-%d %H:%M") if row[4] else ""
        }
        for row in rows
    ]