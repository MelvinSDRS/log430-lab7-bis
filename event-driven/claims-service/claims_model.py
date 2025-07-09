from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional

class ClaimStatus(Enum):
    CREATED = "created"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

class ClaimType(Enum):
    PRODUCT_DEFECT = "product_defect"
    DELIVERY_ISSUE = "delivery_issue"
    BILLING_ERROR = "billing_error"
    SERVICE_COMPLAINT = "service_complaint"

class Claim:
    def __init__(self, claim_id: str, customer_id: str, claim_type: ClaimType, 
                 description: str, product_id: Optional[str] = None):
        self.claim_id = claim_id
        self.customer_id = customer_id
        self.claim_type = claim_type
        self.description = description
        self.product_id = product_id
        self.status = ClaimStatus.CREATED
        self.assigned_agent = None
        self.resolution = None
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'objet en dictionnaire pour sérialisation"""
        return {
            "claim_id": self.claim_id,
            "customer_id": self.customer_id,
            "claim_type": self.claim_type.value,
            "description": self.description,
            "product_id": self.product_id,
            "status": self.status.value,
            "assigned_agent": self.assigned_agent,
            "resolution": self.resolution,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Claim':
        """Crée un objet Claim à partir d'un dictionnaire"""
        claim = cls(
            claim_id=data["claim_id"],
            customer_id=data["customer_id"],
            claim_type=ClaimType(data["claim_type"]),
            description=data["description"],
            product_id=data.get("product_id")
        )
        
        claim.status = ClaimStatus(data["status"])
        claim.assigned_agent = data.get("assigned_agent")
        claim.resolution = data.get("resolution")
        claim.created_at = datetime.fromisoformat(data["created_at"])
        claim.updated_at = datetime.fromisoformat(data["updated_at"])
        
        return claim
    
    def assign_to_agent(self, agent_id: str):
        """Assigne la réclamation à un agent"""
        self.assigned_agent = agent_id
        self.status = ClaimStatus.ASSIGNED
        self.updated_at = datetime.utcnow()
    
    def start_processing(self):
        """Commence le traitement de la réclamation"""
        if self.status != ClaimStatus.ASSIGNED:
            raise ValueError("Claim must be assigned before processing")
        
        self.status = ClaimStatus.IN_PROGRESS
        self.updated_at = datetime.utcnow()
    
    def resolve(self, resolution: str):
        """Résout la réclamation"""
        if self.status != ClaimStatus.IN_PROGRESS:
            raise ValueError("Claim must be in progress to be resolved")
        
        self.resolution = resolution
        self.status = ClaimStatus.RESOLVED
        self.updated_at = datetime.utcnow()
    
    def close(self):
        """Ferme la réclamation"""
        if self.status != ClaimStatus.RESOLVED:
            raise ValueError("Claim must be resolved before closing")
        
        self.status = ClaimStatus.CLOSED
        self.updated_at = datetime.utcnow()