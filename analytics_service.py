import sqlite3
from flask import current_app


def get_connection():
    return sqlite3.connect("crm.db")


# -------------------- REVENUE --------------------

def get_revenue_analytics():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT strftime('%m', closed_at) as month,
               SUM(value)
        FROM deals
        WHERE stage = 'Won'
        GROUP BY month
        ORDER BY month
    """)

    rows = cursor.fetchall()
    conn.close()

    months = ["Jan","Feb","Mar","Apr","May","Jun",
              "Jul","Aug","Sep","Oct","Nov","Dec"]

    revenue_data = []

    for row in rows:
        if row[0] is not None:
            month_index = int(row[0]) - 1
            revenue_data.append({
                "name": months[month_index],
                "revenue": row[1]
            })

    return {"revenueData": revenue_data}


# -------------------- PIPELINE --------------------

def get_pipeline_analytics():
    conn = get_connection()
    cursor = conn.cursor()

    # Deals by stage
    cursor.execute("SELECT stage, COUNT(*) FROM deals GROUP BY stage")
    stages = cursor.fetchall()

    # Win vs Loss
    cursor.execute("SELECT COUNT(*) FROM deals WHERE stage='Won'")
    win = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM deals WHERE stage='Lost'")
    loss = cursor.fetchone()[0]

    # Funnel
    cursor.execute("SELECT COUNT(*) FROM leads")
    total_leads = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM leads WHERE status != 'New'")
    qualified = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM deals WHERE stage='Proposal'")
    proposed = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM deals WHERE stage='Negotiation'")
    negotiating = cursor.fetchone()[0]

    conn.close()

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
    conn = get_connection()
    cursor = conn.cursor()

    # Source
    cursor.execute("SELECT source, COUNT(*) FROM leads GROUP BY source")
    sources = cursor.fetchall()

    # Status
    cursor.execute("SELECT status, COUNT(*) FROM leads GROUP BY status")
    statuses = cursor.fetchall()

    # Trend (Weekly)
    cursor.execute("""
        SELECT strftime('%W', created_at) as week,
               COUNT(*)
        FROM leads
        GROUP BY week
        ORDER BY week
    """)
    trends = cursor.fetchall()

    conn.close()

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
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM leads")
    total_leads = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM deals WHERE stage='Won'")
    won_deals = cursor.fetchone()[0]

    conversion = 0
    if total_leads > 0:
        conversion = round((won_deals / total_leads) * 100, 2)

    # Assuming 'activities' table exists or using 'tasks' as proxy based on existing models
    # Using 'tasks' table as per existing context
    cursor.execute("SELECT COUNT(*) FROM tasks")
    total_activities = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status='Completed'")
    completed = cursor.fetchone()[0]

    task_percent = 0
    if total_activities > 0:
        task_percent = round((completed / total_activities) * 100, 2)

    conn.close()

    return {
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