from datetime import datetime
from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Dict, Any

Base = declarative_base()

class ClaimReadModel(Base):
    """Read Model pour les réclamations (CQRS Query Side)"""
    __tablename__ = 'claim_read_models'
    
    claim_id = Column(String(50), primary_key=True)
    customer_id = Column(String(50), nullable=False)
    claim_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    product_id = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False)
    assigned_agent = Column(String(50), nullable=True)
    resolution = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    assigned_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'claim_id': self.claim_id,
            'customer_id': self.customer_id,
            'claim_type': self.claim_type,
            'description': self.description,
            'product_id': self.product_id,
            'status': self.status,
            'assigned_agent': self.assigned_agent,
            'resolution': self.resolution,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None
        }

class CustomerStatsReadModel(Base):
    """Read Model pour les statistiques client"""
    __tablename__ = 'customer_stats_read_models'
    
    customer_id = Column(String(50), primary_key=True)
    total_claims = Column(Integer, default=0)
    active_claims = Column(Integer, default=0)
    resolved_claims = Column(Integer, default=0)
    closed_claims = Column(Integer, default=0)
    last_claim_date = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'customer_id': self.customer_id,
            'total_claims': self.total_claims,
            'active_claims': self.active_claims,
            'resolved_claims': self.resolved_claims,
            'closed_claims': self.closed_claims,
            'last_claim_date': self.last_claim_date.isoformat() if self.last_claim_date else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class AgentStatsReadModel(Base):
    """Read Model pour les statistiques agent"""
    __tablename__ = 'agent_stats_read_models'
    
    agent_id = Column(String(50), primary_key=True)
    total_assigned_claims = Column(Integer, default=0)
    active_claims = Column(Integer, default=0)
    resolved_claims = Column(Integer, default=0)
    last_assignment_date = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'agent_id': self.agent_id,
            'total_assigned_claims': self.total_assigned_claims,
            'active_claims': self.active_claims,
            'resolved_claims': self.resolved_claims,
            'last_assignment_date': self.last_assignment_date.isoformat() if self.last_assignment_date else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ClaimTypeStatsReadModel(Base):
    """Read Model pour les statistiques par type de réclamation"""
    __tablename__ = 'claim_type_stats_read_models'
    
    claim_type = Column(String(50), primary_key=True)
    total_claims = Column(Integer, default=0)
    created_claims = Column(Integer, default=0)
    assigned_claims = Column(Integer, default=0)
    in_progress_claims = Column(Integer, default=0)
    resolved_claims = Column(Integer, default=0)
    closed_claims = Column(Integer, default=0)
    updated_at = Column(DateTime, nullable=False)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'claim_type': self.claim_type,
            'total_claims': self.total_claims,
            'created_claims': self.created_claims,
            'assigned_claims': self.assigned_claims,
            'in_progress_claims': self.in_progress_claims,
            'resolved_claims': self.resolved_claims,
            'closed_claims': self.closed_claims,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ReadModelRepository:
    def __init__(self, postgres_url: str):
        self.engine = create_engine(postgres_url)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def upsert_claim(self, claim_data: Dict[str, Any]):
        """Met à jour ou insère une réclamation dans le read model"""
        claim = self.session.query(ClaimReadModel).filter_by(claim_id=claim_data['claim_id']).first()
        
        if claim:
            # Mettre à jour
            for key, value in claim_data.items():
                if hasattr(claim, key):
                    setattr(claim, key, value)
        else:
            # Créer nouveau
            claim = ClaimReadModel(**claim_data)
            self.session.add(claim)
        
        self.session.commit()
        return claim
    
    def update_customer_stats(self, customer_id: str, operation: str, claim_date: datetime):
        """Met à jour les statistiques client"""
        stats = self.session.query(CustomerStatsReadModel).filter_by(customer_id=customer_id).first()
        
        if not stats:
            stats = CustomerStatsReadModel(
                customer_id=customer_id,
                updated_at=datetime.utcnow()
            )
            self.session.add(stats)
        
        if operation == 'created':
            stats.total_claims += 1
            stats.active_claims += 1
            stats.last_claim_date = claim_date
        elif operation == 'resolved':
            stats.active_claims = max(0, stats.active_claims - 1)
            stats.resolved_claims += 1
        elif operation == 'closed':
            stats.resolved_claims = max(0, stats.resolved_claims - 1)
            stats.closed_claims += 1
        
        stats.updated_at = datetime.utcnow()
        self.session.commit()
    
    def update_agent_stats(self, agent_id: str, operation: str, assignment_date: datetime):
        """Met à jour les statistiques agent"""
        stats = self.session.query(AgentStatsReadModel).filter_by(agent_id=agent_id).first()
        
        if not stats:
            stats = AgentStatsReadModel(
                agent_id=agent_id,
                updated_at=datetime.utcnow()
            )
            self.session.add(stats)
        
        if operation == 'assigned':
            stats.total_assigned_claims += 1
            stats.active_claims += 1
            stats.last_assignment_date = assignment_date
        elif operation == 'resolved':
            stats.active_claims = max(0, stats.active_claims - 1)
            stats.resolved_claims += 1
        
        stats.updated_at = datetime.utcnow()
        self.session.commit()
    
    def update_claim_type_stats(self, claim_type: str, status: str, operation: str):
        """Met à jour les statistiques par type de réclamation"""
        stats = self.session.query(ClaimTypeStatsReadModel).filter_by(claim_type=claim_type).first()
        
        if not stats:
            stats = ClaimTypeStatsReadModel(
                claim_type=claim_type,
                updated_at=datetime.utcnow()
            )
            self.session.add(stats)
        
        if operation == 'created':
            stats.total_claims += 1
            stats.created_claims += 1
        elif operation == 'status_change':
            # Décrémenter l'ancien statut et incrémenter le nouveau
            if status == 'assigned':
                stats.created_claims = max(0, stats.created_claims - 1)
                stats.assigned_claims += 1
            elif status == 'in_progress':
                stats.assigned_claims = max(0, stats.assigned_claims - 1)
                stats.in_progress_claims += 1
            elif status == 'resolved':
                stats.in_progress_claims = max(0, stats.in_progress_claims - 1)
                stats.resolved_claims += 1
            elif status == 'closed':
                stats.resolved_claims = max(0, stats.resolved_claims - 1)
                stats.closed_claims += 1
        
        stats.updated_at = datetime.utcnow()
        self.session.commit()
    
    def get_all_claims(self, limit: int = 100, offset: int = 0):
        """Récupère toutes les réclamations"""
        return self.session.query(ClaimReadModel).offset(offset).limit(limit).all()
    
    def get_claims_by_customer(self, customer_id: str):
        """Récupère les réclamations d'un client"""
        return self.session.query(ClaimReadModel).filter_by(customer_id=customer_id).all()
    
    def get_claims_by_agent(self, agent_id: str):
        """Récupère les réclamations d'un agent"""
        return self.session.query(ClaimReadModel).filter_by(assigned_agent=agent_id).all()
    
    def get_claims_by_status(self, status: str):
        """Récupère les réclamations par statut"""
        return self.session.query(ClaimReadModel).filter_by(status=status).all()
    
    def get_customer_stats(self, customer_id: str = None):
        """Récupère les statistiques client"""
        if customer_id:
            return self.session.query(CustomerStatsReadModel).filter_by(customer_id=customer_id).first()
        return self.session.query(CustomerStatsReadModel).all()
    
    def get_agent_stats(self, agent_id: str = None):
        """Récupère les statistiques agent"""
        if agent_id:
            return self.session.query(AgentStatsReadModel).filter_by(agent_id=agent_id).first()
        return self.session.query(AgentStatsReadModel).all()
    
    def get_claim_type_stats(self, claim_type: str = None):
        """Récupère les statistiques par type"""
        if claim_type:
            return self.session.query(ClaimTypeStatsReadModel).filter_by(claim_type=claim_type).first()
        return self.session.query(ClaimTypeStatsReadModel).all()