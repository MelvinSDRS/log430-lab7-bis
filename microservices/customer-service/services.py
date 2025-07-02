#!/usr/bin/env python3
"""
Services métier pour Customer Service
Logique métier pour clients, authentification, adresses
"""

import os
import jwt
from typing import List, Dict, Optional
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from database import CustomerModel, AddressModel


class CustomerService:
    """Service métier pour la gestion des clients"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_customers_paginated(self, page: int = 1, per_page: int = 20, search: str = '') -> List[Dict]:
        """Récupérer les clients avec pagination et recherche"""
        query = self.session.query(CustomerModel).filter(CustomerModel.actif == True)
        
        # Filtrage par recherche
        if search:
            search_filter = or_(
                CustomerModel.nom.ilike(f'%{search}%'),
                CustomerModel.prenom.ilike(f'%{search}%'),
                CustomerModel.email.ilike(f'%{search}%'),
                CustomerModel.telephone.ilike(f'%{search}%')
            )
            query = query.filter(search_filter)
        
        # Pagination
        offset = (page - 1) * per_page
        customers = query.offset(offset).limit(per_page).all()
        
        return [customer.to_dict() for customer in customers]
    
    def count_customers(self, search: str = '') -> int:
        """Compter le nombre total de clients"""
        query = self.session.query(CustomerModel).filter(CustomerModel.actif == True)
        
        if search:
            search_filter = or_(
                CustomerModel.nom.ilike(f'%{search}%'),
                CustomerModel.prenom.ilike(f'%{search}%'),
                CustomerModel.email.ilike(f'%{search}%'),
                CustomerModel.telephone.ilike(f'%{search}%')
            )
            query = query.filter(search_filter)
        
        return query.count()
    
    def get_customer_by_id(self, customer_id: int) -> Optional[Dict]:
        """Récupérer un client par son ID"""
        customer = self.session.query(CustomerModel).filter(
            and_(CustomerModel.id == customer_id, CustomerModel.actif == True)
        ).first()
        
        return customer.to_dict() if customer else None
    
    def get_customer_by_email(self, email: str) -> Optional[Dict]:
        """Récupérer un client par son email"""
        customer = self.session.query(CustomerModel).filter(
            and_(CustomerModel.email == email, CustomerModel.actif == True)
        ).first()
        
        return customer.to_dict(include_sensitive=True) if customer else None
    
    def update_customer(self, customer_id: int, update_data: Dict) -> Optional[Dict]:
        """Mettre à jour un client"""
        customer = self.session.query(CustomerModel).filter(
            and_(CustomerModel.id == customer_id, CustomerModel.actif == True)
        ).first()
        
        if not customer:
            return None
        
        # Champs autorisés à la mise à jour
        allowed_fields = ['nom', 'prenom', 'telephone', 'date_naissance']
        
        for field, value in update_data.items():
            if field in allowed_fields:
                if field == 'date_naissance' and isinstance(value, str):
                    try:
                        value = datetime.strptime(value, '%Y-%m-%d').date()
                    except ValueError:
                        raise ValueError(f"Format de date invalide pour {field}. Utilisez YYYY-MM-DD")
                
                setattr(customer, field, value)
        
        customer.updated_at = datetime.utcnow()
        self.session.commit()
        self.session.refresh(customer)
        
        return customer.to_dict()
    
    def deactivate_customer(self, customer_id: int) -> bool:
        """Désactiver un client (soft delete)"""
        customer = self.session.query(CustomerModel).filter(
            and_(CustomerModel.id == customer_id, CustomerModel.actif == True)
        ).first()
        
        if not customer:
            return False
        
        customer.actif = False
        customer.updated_at = datetime.utcnow()
        
        self.session.commit()
        return True


class AddressService:
    """Service métier pour la gestion des adresses clients"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_addresses_by_customer(self, customer_id: int) -> List[Dict]:
        """Récupérer toutes les adresses d'un client"""
        addresses = self.session.query(AddressModel).filter(
            AddressModel.customer_id == customer_id
        ).all()
        
        return [address.to_dict() for address in addresses]
    
    def create_address(self, address_data: Dict) -> Dict:
        """Créer une nouvelle adresse"""
        
        # Validation des données
        required_fields = ['customer_id', 'type', 'nom_complet', 'adresse_ligne1', 'ville', 'province', 'code_postal']
        for field in required_fields:
            if field not in address_data or not address_data[field]:
                raise ValueError(f"Le champ '{field}' est requis")
        
        # Vérifier que le client existe
        customer = self.session.query(CustomerModel).filter(
            and_(CustomerModel.id == address_data['customer_id'], CustomerModel.actif == True)
        ).first()
        if not customer:
            raise ValueError(f"Client {address_data['customer_id']} introuvable")
        
        # Validation du type d'adresse
        valid_types = ['livraison', 'facturation']
        if address_data['type'] not in valid_types:
            raise ValueError(f"Type d'adresse invalide. Valeurs autorisées: {valid_types}")
        
        # Si c'est marqué comme par défaut, retirer le flag des autres adresses du même type
        if address_data.get('par_defaut', False):
            self.session.query(AddressModel).filter(
                and_(
                    AddressModel.customer_id == address_data['customer_id'],
                    AddressModel.type == address_data['type']
                )
            ).update({'par_defaut': False})
        
        # Créer l'adresse
        address = AddressModel(
            customer_id=address_data['customer_id'],
            type=address_data['type'],
            nom_complet=address_data['nom_complet'],
            adresse_ligne1=address_data['adresse_ligne1'],
            adresse_ligne2=address_data.get('adresse_ligne2'),
            ville=address_data['ville'],
            province=address_data['province'],
            code_postal=address_data['code_postal'],
            pays=address_data.get('pays', 'Canada'),
            par_defaut=address_data.get('par_defaut', False)
        )
        
        self.session.add(address)
        self.session.commit()
        self.session.refresh(address)
        
        return address.to_dict()
    
    def update_address(self, address_id: int, customer_id: int, update_data: Dict) -> Optional[Dict]:
        """Mettre à jour une adresse"""
        address = self.session.query(AddressModel).filter(
            and_(AddressModel.id == address_id, AddressModel.customer_id == customer_id)
        ).first()
        
        if not address:
            return None
        
        # Champs autorisés à la mise à jour
        allowed_fields = ['type', 'nom_complet', 'adresse_ligne1', 'adresse_ligne2', 
                         'ville', 'province', 'code_postal', 'pays', 'par_defaut']
        
        # Si on change le flag par_defaut à True, retirer des autres adresses
        if update_data.get('par_defaut', False) and not address.par_defaut:
            self.session.query(AddressModel).filter(
                and_(
                    AddressModel.customer_id == customer_id,
                    AddressModel.type == address.type,
                    AddressModel.id != address_id
                )
            ).update({'par_defaut': False})
        
        for field, value in update_data.items():
            if field in allowed_fields:
                setattr(address, field, value)
        
        address.updated_at = datetime.utcnow()
        self.session.commit()
        self.session.refresh(address)
        
        return address.to_dict()
    
    def delete_address(self, address_id: int, customer_id: int) -> bool:
        """Supprimer une adresse"""
        address = self.session.query(AddressModel).filter(
            and_(AddressModel.id == address_id, AddressModel.customer_id == customer_id)
        ).first()
        
        if not address:
            return False
        
        self.session.delete(address)
        self.session.commit()
        return True
    
    def set_default_address(self, address_id: int, customer_id: int) -> bool:
        """Définir une adresse comme par défaut"""
        address = self.session.query(AddressModel).filter(
            and_(AddressModel.id == address_id, AddressModel.customer_id == customer_id)
        ).first()
        
        if not address:
            return False
        
        # Retirer le flag par défaut des autres adresses du même type
        self.session.query(AddressModel).filter(
            and_(
                AddressModel.customer_id == customer_id,
                AddressModel.type == address.type,
                AddressModel.id != address_id
            )
        ).update({'par_defaut': False})
        
        # Définir cette adresse comme par défaut
        address.par_defaut = True
        address.updated_at = datetime.utcnow()
        
        self.session.commit()
        return True


class AuthService:
    """Service d'authentification pour les clients"""
    
    def __init__(self, session: Session):
        self.session = session
        self.jwt_secret = os.getenv('JWT_SECRET', 'jwt-customer-secret-2025')
        self.jwt_algorithm = 'HS256'
        self.jwt_expiration_hours = 24
    
    def register_customer(self, customer_data: Dict) -> Dict:
        """Enregistrer un nouveau client"""
        
        # Validation des données
        required_fields = ['email', 'password', 'nom', 'prenom']
        for field in required_fields:
            if field not in customer_data or not customer_data[field]:
                raise ValueError(f"Le champ '{field}' est requis")
        
        # Validation email
        email = customer_data['email'].lower().strip()
        if '@' not in email or '.' not in email:
            raise ValueError("Format d'email invalide")
        
        # Vérifier l'unicité de l'email
        existing = self.session.query(CustomerModel).filter(
            CustomerModel.email == email
        ).first()
        if existing:
            raise ValueError(f"Un compte avec l'email '{email}' existe déjà")
        
        # Validation mot de passe
        password = customer_data['password']
        if len(password) < 6:
            raise ValueError("Le mot de passe doit contenir au moins 6 caractères")
        
        # Validation date de naissance si fournie
        date_naissance = None
        if 'date_naissance' in customer_data and customer_data['date_naissance']:
            if isinstance(customer_data['date_naissance'], str):
                try:
                    date_naissance = datetime.strptime(customer_data['date_naissance'], '%Y-%m-%d').date()
                except ValueError:
                    raise ValueError("Format de date invalide. Utilisez YYYY-MM-DD")
            else:
                date_naissance = customer_data['date_naissance']
        
        # Créer le client
        customer = CustomerModel(
            email=email,
            password_hash=CustomerModel.hash_password(password),
            nom=customer_data['nom'].strip(),
            prenom=customer_data['prenom'].strip(),
            telephone=customer_data.get('telephone', '').strip() or None,
            date_naissance=date_naissance
        )
        
        self.session.add(customer)
        self.session.commit()
        self.session.refresh(customer)
        
        return customer.to_dict()
    
    def authenticate_customer(self, email: str, password: str) -> Optional[Dict]:
        """Authentifier un client et retourner un token JWT"""
        
        # Récupérer le client
        customer = self.session.query(CustomerModel).filter(
            and_(CustomerModel.email == email.lower().strip(), CustomerModel.actif == True)
        ).first()
        
        if not customer or not customer.verify_password(password):
            return None
        
        # Mettre à jour la dernière connexion
        customer.derniere_connexion = datetime.utcnow()
        self.session.commit()
        
        # Générer le token JWT
        payload = {
            'customer_id': customer.id,
            'email': customer.email,
            'nom': customer.nom,
            'prenom': customer.prenom,
            'exp': datetime.utcnow() + timedelta(hours=self.jwt_expiration_hours),
            'iat': datetime.utcnow()
        }
        
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        return {
            'token': token,
            'token_type': 'Bearer',
            'expires_in': self.jwt_expiration_hours * 3600,  # en secondes
            'customer': customer.to_dict()
        }
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Vérifier et décoder un token JWT"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            # Vérifier que le client existe toujours et est actif
            customer = self.session.query(CustomerModel).filter(
                and_(CustomerModel.id == payload['customer_id'], CustomerModel.actif == True)
            ).first()
            
            if not customer:
                return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def refresh_token(self, token: str) -> Optional[Dict]:
        """Rafraîchir un token JWT"""
        payload = self.verify_token(token)
        if not payload:
            return None
        
        # Générer un nouveau token
        customer = self.session.query(CustomerModel).filter(
            CustomerModel.id == payload['customer_id']
        ).first()
        
        if not customer:
            return None
        
        new_payload = {
            'customer_id': customer.id,
            'email': customer.email,
            'nom': customer.nom,
            'prenom': customer.prenom,
            'exp': datetime.utcnow() + timedelta(hours=self.jwt_expiration_hours),
            'iat': datetime.utcnow()
        }
        
        new_token = jwt.encode(new_payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        return {
            'token': new_token,
            'token_type': 'Bearer',
            'expires_in': self.jwt_expiration_hours * 3600,
            'customer': customer.to_dict()
        }
    
    def change_password(self, customer_id: int, old_password: str, new_password: str) -> bool:
        """Changer le mot de passe d'un client"""
        
        customer = self.session.query(CustomerModel).filter(
            and_(CustomerModel.id == customer_id, CustomerModel.actif == True)
        ).first()
        
        if not customer:
            return False
        
        # Vérifier l'ancien mot de passe
        if not customer.verify_password(old_password):
            raise ValueError("Ancien mot de passe incorrect")
        
        # Validation du nouveau mot de passe
        if len(new_password) < 6:
            raise ValueError("Le nouveau mot de passe doit contenir au moins 6 caractères")
        
        # Mettre à jour le mot de passe
        customer.password_hash = CustomerModel.hash_password(new_password)
        customer.updated_at = datetime.utcnow()
        
        self.session.commit()
        return True 