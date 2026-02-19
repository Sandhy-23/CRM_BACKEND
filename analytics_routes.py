from flask import Blueprint, jsonify
import analytics_service

analytics_bp = Blueprint("analytics", __name__)

@analytics_bp.route("/api/analytics/revenue")
def revenue():
    return jsonify(analytics_service.get_revenue_analytics())

@analytics_bp.route("/api/analytics/pipeline")
def pipeline():
    return jsonify(analytics_service.get_pipeline_analytics())

@analytics_bp.route("/api/analytics/leads")
def leads():
    return jsonify(analytics_service.get_lead_analytics())

@analytics_bp.route("/api/analytics/kpi")
def kpi():
    return jsonify(analytics_service.get_kpi_analytics())