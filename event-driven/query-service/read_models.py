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