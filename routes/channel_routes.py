from flask import Blueprint, request, jsonify
from extensions import db
from models.channel_account import ChannelAccount
from routes.auth_routes import token_required

channel_bp = Blueprint('channels', __name__)

@channel_bp.route('/api/channels/connect', methods=['POST'])
@token_required
def connect_channel(current_user):
    data = request.get_json()
    
    account = ChannelAccount(
        channel=data.get('channel'),
        account_name=data.get('account_name'),
        access_token=data.get('access_token'),
        credentials=data.get('credentials'), # JSON
        organization_id=current_user.organization_id,
        status='connected'
    )
    
    db.session.add(account)
    db.session.commit()
    
    return jsonify({'message': 'Channel connected', 'id': account.id}), 201

@channel_bp.route('/api/channels', methods=['GET'])
@token_required
def get_channels(current_user):
    accounts = ChannelAccount.query.filter_by(organization_id=current_user.organization_id).all()
    return jsonify([{
        "id": a.id,
        "channel": a.channel,
        "account_name": a.account_name,
        "status": a.status
    } for a in accounts]), 200