import os
from typing import List, Dict, Any

import structlog
from flask import Flask, request, jsonify
from flask_restx import Api, Resource
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy import create_engine, and_, or_
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from read_models import Base, ClaimReadModel, CustomerStatsReadModel, AgentStatsReadModel, ClaimTypeStatsReadModel

# Configuration de logging structuré
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Métriques Prometheus
QUERIES_EXECUTED = Counter('queries_executed_total', 'Total number of queries executed', ['query_type'])
QUERY_DURATION = Histogram('query_duration_seconds', 'Query execution duration', ['query_type'])

app = Flask(__name__)
api = Api(app, version='1.0', title='Query Service API',
          description='Service de requêtes CQRS pour read models',
          doc='/docs/')

# Configuration
postgres_url = os.getenv('POSTGRES_URL', 'postgresql://localhost:5439/read_models_db')

class QueryService:
    def __init__(self, postgres_url: str):
        self.engine = create_engine(postgres_url)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def get_all_claims(self, limit: int = 100, offset: int = 0, 
                      status: str = None, customer_id: str = None, 
                      agent_id: str = None, claim_type: str = None) -> List[Dict[str, Any]]:
        """Récupère toutes les réclamations avec filtres optionnels"""
        query = self.session.query(ClaimReadModel)
        
        if status:
            query = query.filter(ClaimReadModel.status == status)
        if customer_id:
            query = query.filter(ClaimReadModel.customer_id == customer_id)
        if agent_id:
            query = query.filter(ClaimReadModel.assigned_agent == agent_id)
        if claim_type:
            query = query.filter(ClaimReadModel.claim_type == claim_type)
        
        claims = query.order_by(ClaimReadModel.created_at.desc()).offset(offset).limit(limit).all()
        return [claim.to_dict() for claim in claims]
    
    def get_claim_by_id(self, claim_id: str) -> Dict[str, Any]:
        """Récupère une réclamation par ID"""
        claim = self.session.query(ClaimReadModel).filter_by(claim_id=claim_id).first()
        return claim.to_dict() if claim else None
    
    def get_claims_by_customer(self, customer_id: str) -> List[Dict[str, Any]]:
        """Récupère les réclamations d'un client"""
        claims = self.session.query(ClaimReadModel).filter_by(customer_id=customer_id).order_by(ClaimReadModel.created_at.desc()).all()
        return [claim.to_dict() for claim in claims]
    
    def get_claims_by_agent(self, agent_id: str) -> List[Dict[str, Any]]:
        """Récupère les réclamations d'un agent"""
        claims = self.session.query(ClaimReadModel).filter_by(assigned_agent=agent_id).order_by(ClaimReadModel.assigned_at.desc()).all()
        return [claim.to_dict() for claim in claims]
    
    def get_claims_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Récupère les réclamations par statut"""
        claims = self.session.query(ClaimReadModel).filter_by(status=status).order_by(ClaimReadModel.updated_at.desc()).all()
        return [claim.to_dict() for claim in claims]
    
    def get_customer_stats(self, customer_id: str = None) -> List[Dict[str, Any]]:
        """Récupère les statistiques client"""
        if customer_id:
            stats = self.session.query(CustomerStatsReadModel).filter_by(customer_id=customer_id).first()
            return [stats.to_dict()] if stats else []
        else:
            stats_list = self.session.query(CustomerStatsReadModel).order_by(CustomerStatsReadModel.total_claims.desc()).all()
            return [stats.to_dict() for stats in stats_list]
    
    def get_agent_stats(self, agent_id: str = None) -> List[Dict[str, Any]]:
        """Récupère les statistiques agent"""
        if agent_id:
            stats = self.session.query(AgentStatsReadModel).filter_by(agent_id=agent_id).first()
            return [stats.to_dict()] if stats else []
        else:
            stats_list = self.session.query(AgentStatsReadModel).order_by(AgentStatsReadModel.total_assigned_claims.desc()).all()
            return [stats.to_dict() for stats in stats_list]
    
    def get_claim_type_stats(self, claim_type: str = None) -> List[Dict[str, Any]]:
        """Récupère les statistiques par type"""
        if claim_type:
            stats = self.session.query(ClaimTypeStatsReadModel).filter_by(claim_type=claim_type).first()
            return [stats.to_dict()] if stats else []
        else:
            stats_list = self.session.query(ClaimTypeStatsReadModel).order_by(ClaimTypeStatsReadModel.total_claims.desc()).all()
            return [stats.to_dict() for stats in stats_list]
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Récupère un résumé pour tableau de bord"""
        try:
            # Statistiques générales
            total_claims = self.session.query(ClaimReadModel).count()
            active_claims = self.session.query(ClaimReadModel).filter(
                or_(
                    ClaimReadModel.status == 'created',
                    ClaimReadModel.status == 'assigned',
                    ClaimReadModel.status == 'in_progress'
                )
            ).count()
            resolved_claims = self.session.query(ClaimReadModel).filter_by(status='resolved').count()
            closed_claims = self.session.query(ClaimReadModel).filter_by(status='closed').count()
            
            # Réclamations récentes
            recent_claims = self.session.query(ClaimReadModel).order_by(ClaimReadModel.created_at.desc()).limit(5).all()
            
            # Top clients par nombre de réclamations
            top_customers = self.session.query(CustomerStatsReadModel).order_by(CustomerStatsReadModel.total_claims.desc()).limit(5).all()
            
            # Top agents par réclamations assignées
            top_agents = self.session.query(AgentStatsReadModel).order_by(AgentStatsReadModel.total_assigned_claims.desc()).limit(5).all()
            
            # Statistiques par type
            type_stats = self.session.query(ClaimTypeStatsReadModel).order_by(ClaimTypeStatsReadModel.total_claims.desc()).all()
            
            return {
                "summary": {
                    "total_claims": total_claims,
                    "active_claims": active_claims,
                    "resolved_claims": resolved_claims,
                    "closed_claims": closed_claims
                },
                "recent_claims": [claim.to_dict() for claim in recent_claims],
                "top_customers": [customer.to_dict() for customer in top_customers],
                "top_agents": [agent.to_dict() for agent in top_agents],
                "claim_type_breakdown": [stat.to_dict() for stat in type_stats]
            }
        except Exception as e:
            logger.error("Error getting dashboard summary", error=str(e))
            return {}
    
    def search_claims(self, search_term: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Recherche textuelle dans les réclamations"""
        try:
            claims = self.session.query(ClaimReadModel).filter(
                or_(
                    ClaimReadModel.description.ilike(f'%{search_term}%'),
                    ClaimReadModel.claim_id.ilike(f'%{search_term}%'),
                    ClaimReadModel.customer_id.ilike(f'%{search_term}%'),
                    ClaimReadModel.resolution.ilike(f'%{search_term}%')
                )
            ).order_by(ClaimReadModel.created_at.desc()).limit(limit).all()
            
            return [claim.to_dict() for claim in claims]
        except Exception as e:
            logger.error("Error searching claims", error=str(e), search_term=search_term)
            return []

# Initialiser le service de requêtes
query_service = QueryService(postgres_url)

@api.route('/claims')
class ClaimsQueryResource(Resource):
    @api.doc('query_claims')
    def get(self):
        """Récupérer les réclamations avec filtres optionnels"""
        with QUERY_DURATION.labels(query_type='claims_list').time():
            limit = int(request.args.get('limit', 100))
            offset = int(request.args.get('offset', 0))
            status = request.args.get('status')
            customer_id = request.args.get('customer_id')
            agent_id = request.args.get('agent_id')
            claim_type = request.args.get('claim_type')
            
            claims = query_service.get_all_claims(
                limit=limit,
                offset=offset,
                status=status,
                customer_id=customer_id,
                agent_id=agent_id,
                claim_type=claim_type
            )
            
            QUERIES_EXECUTED.labels(query_type='claims_list').inc()
            
            return {
                "claims": claims,
                "count": len(claims),
                "limit": limit,
                "offset": offset,
                "filters": {
                    "status": status,
                    "customer_id": customer_id,
                    "agent_id": agent_id,
                    "claim_type": claim_type
                }
            }

@api.route('/claims/<string:claim_id>')
class ClaimQueryResource(Resource):
    @api.doc('get_claim')
    def get(self, claim_id):
        """Récupérer une réclamation par ID"""
        with QUERY_DURATION.labels(query_type='claim_detail').time():
            claim = query_service.get_claim_by_id(claim_id)
            
            if not claim:
                return {"error": "Claim not found"}, 404
            
            QUERIES_EXECUTED.labels(query_type='claim_detail').inc()
            return claim

@api.route('/claims/customer/<string:customer_id>')
class CustomerClaimsResource(Resource):
    @api.doc('get_customer_claims')
    def get(self, customer_id):
        """Récupérer les réclamations d'un client"""
        with QUERY_DURATION.labels(query_type='customer_claims').time():
            claims = query_service.get_claims_by_customer(customer_id)
            
            QUERIES_EXECUTED.labels(query_type='customer_claims').inc()
            
            return {
                "customer_id": customer_id,
                "claims": claims,
                "count": len(claims)
            }

@api.route('/claims/agent/<string:agent_id>')
class AgentClaimsResource(Resource):
    @api.doc('get_agent_claims')
    def get(self, agent_id):
        """Récupérer les réclamations d'un agent"""
        with QUERY_DURATION.labels(query_type='agent_claims').time():
            claims = query_service.get_claims_by_agent(agent_id)
            
            QUERIES_EXECUTED.labels(query_type='agent_claims').inc()
            
            return {
                "agent_id": agent_id,
                "claims": claims,
                "count": len(claims)
            }

@api.route('/claims/status/<string:status>')
class StatusClaimsResource(Resource):
    @api.doc('get_claims_by_status')
    def get(self, status):
        """Récupérer les réclamations par statut"""
        with QUERY_DURATION.labels(query_type='status_claims').time():
            claims = query_service.get_claims_by_status(status)
            
            QUERIES_EXECUTED.labels(query_type='status_claims').inc()
            
            return {
                "status": status,
                "claims": claims,
                "count": len(claims)
            }

@api.route('/stats/customers')
class CustomerStatsResource(Resource):
    @api.doc('get_customer_stats')
    def get(self):
        """Récupérer les statistiques client"""
        with QUERY_DURATION.labels(query_type='customer_stats').time():
            customer_id = request.args.get('customer_id')
            stats = query_service.get_customer_stats(customer_id)
            
            QUERIES_EXECUTED.labels(query_type='customer_stats').inc()
            
            return {
                "customer_stats": stats,
                "count": len(stats)
            }

@api.route('/stats/agents')
class AgentStatsResource(Resource):
    @api.doc('get_agent_stats')
    def get(self):
        """Récupérer les statistiques agent"""
        with QUERY_DURATION.labels(query_type='agent_stats').time():
            agent_id = request.args.get('agent_id')
            stats = query_service.get_agent_stats(agent_id)
            
            QUERIES_EXECUTED.labels(query_type='agent_stats').inc()
            
            return {
                "agent_stats": stats,
                "count": len(stats)
            }

@api.route('/stats/claim-types')
class ClaimTypeStatsResource(Resource):
    @api.doc('get_claim_type_stats')
    def get(self):
        """Récupérer les statistiques par type"""
        with QUERY_DURATION.labels(query_type='claim_type_stats').time():
            claim_type = request.args.get('claim_type')
            stats = query_service.get_claim_type_stats(claim_type)
            
            QUERIES_EXECUTED.labels(query_type='claim_type_stats').inc()
            
            return {
                "claim_type_stats": stats,
                "count": len(stats)
            }

@api.route('/dashboard')
class DashboardResource(Resource):
    @api.doc('get_dashboard_summary')
    def get(self):
        """Récupérer le résumé pour tableau de bord"""
        with QUERY_DURATION.labels(query_type='dashboard').time():
            summary = query_service.get_dashboard_summary()
            
            QUERIES_EXECUTED.labels(query_type='dashboard').inc()
            
            return summary

@api.route('/search')
class SearchResource(Resource):
    @api.doc('search_claims')
    def get(self):
        """Recherche textuelle dans les réclamations"""
        with QUERY_DURATION.labels(query_type='search').time():
            search_term = request.args.get('q', '')
            limit = int(request.args.get('limit', 50))
            
            if not search_term:
                return {"error": "Search term required"}, 400
            
            claims = query_service.search_claims(search_term, limit)
            
            QUERIES_EXECUTED.labels(query_type='search').inc()
            
            return {
                "search_term": search_term,
                "claims": claims,
                "count": len(claims)
            }

@app.route('/health')
def health():
    """Endpoint de santé"""
    try:
        # Tester la connexion PostgreSQL
        query_service.session.execute('SELECT 1')
        return {"status": "healthy", "service": "query-service"}
    except SQLAlchemyError as e:
        return {"status": "unhealthy", "service": "query-service", "error": str(e)}, 503

@app.route('/metrics')
def metrics():
    """Endpoint pour les métriques Prometheus"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

if __name__ == '__main__':
    logger.info("Starting Query Service", port=8105)
    app.run(host='0.0.0.0', port=8105, debug=False)