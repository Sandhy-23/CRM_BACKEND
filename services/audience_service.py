from models.crm import Lead
from extensions import db

class AudienceService:
    @staticmethod
    def resolve_audience(audience_config, organization_id, branch_id=None):
        """
        Resolves leads based on audience configuration.
        audience_config: dict or string (e.g., "all", "hot", or {"tag": "custom"})
        """
        query = Lead.query.filter_by(organization_id=organization_id, is_deleted=False)

        if branch_id:
            # Filter by branch if the column exists (handled in app.py migration)
            if hasattr(Lead, 'branch_id'):
                query = query.filter_by(branch_id=branch_id)

        if audience_config == 'all':
            pass
        elif audience_config == 'hot':
            query = query.filter(Lead.score == 'Hot')
        elif isinstance(audience_config, dict) and audience_config.get('tag'):
            # Placeholder for tag filtering
            pass
        
        return query.all()