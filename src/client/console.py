from typing import List
from decimal import Decimal
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..persistence.database import get_db_session
from ..domain.services import ServiceProduit, ServiceVente, ServiceInventaire, ServiceApprovisionnement, ServiceRapport
from ..persistence.repositories import RepositoryCaisse, RepositoryEntite
from ..domain.entities import LigneVente, Produit, TypeEntite

console = Console()


class ApplicationConsole:
    def __init__(self):
        self.session = get_db_session()
        self.service_produit = ServiceProduit(self.session)
        self.service_vente = ServiceVente(self.session)
        self.service_inventaire = ServiceInventaire(self.session)
        self.service_approvisionnement = ServiceApprovisionnement(self.session)
        self.service_rapport = ServiceRapport(self.session)
        self.repo_caisse = RepositoryCaisse(self.session)
        self.repo_entite = RepositoryEntite(self.session)
        self.id_caisse = None
        self.id_caissier = None
        self.id_entite = None  # ID de l'entité (magasin) courante
        self.entite = None  # Entité courante
        self.panier: List[LigneVente] = []

    def selectionner_caisse_et_caissier(self):
        """Permettre à l'utilisateur de sélectionner sa caisse et son identité"""
        console.print(Panel.fit("🔧 Configuration de la caisse", style="bold yellow"))

        # Déterminer l'entité (magasin) en fonction de la variable d'environnement
        import os
        id_entite = os.environ.get('ENTITE_ID')
        if id_entite:
            self.id_entite = int(id_entite)
            self.entite = self.repo_entite.obtenir_par_id(self.id_entite)
            console.print(f"[cyan]📍 Magasin: {self.entite.nom}[/cyan]")
            
            # Afficher seulement les caisses de ce magasin
            caisses = self.repo_caisse.lister_par_entite(self.id_entite)
        else:
            # Fallback : afficher toutes les caisses (pour compatibilité)
            caisses = self.repo_caisse.lister_actives()
            
        if not caisses:
            console.print("[red]Aucune caisse active disponible![/red]")
            return False

        table_caisses = Table(title="Caisses disponibles")
        table_caisses.add_column("ID", style="cyan")
        table_caisses.add_column("Nom", style="green")
        table_caisses.add_column("Statut", style="blue")

        for caisse in caisses:
            table_caisses.add_row(str(caisse.id), caisse.nom, caisse.statut)

        console.print(table_caisses)

        # Sélection de la caisse
        while True:
            try:
                caisse_id = int(console.input("Sélectionnez votre caisse (ID): "))
                if any(c.id == caisse_id for c in caisses):
                    self.id_caisse = caisse_id
                    caisse_nom = next(c.nom for c in caisses if c.id == caisse_id)
                    console.print(f"[green]✓ Caisse sélectionnée: {caisse_nom}[/green]")
                    
                    if not self.id_entite:
                        caisse_selectionnee = next(c for c in caisses if c.id == caisse_id)
                        self.id_entite = caisse_selectionnee.id_entite
                        self.entite = self.repo_entite.obtenir_par_id(self.id_entite)
                        console.print(f"[green]✓ Magasin: {self.entite.nom}[/green]")
                    break
                else:
                    console.print("[red]ID de caisse invalide[/red]")
            except ValueError:
                console.print("[red]Veuillez entrer un nombre valide[/red]")

        # Sélection du caissier
        console.print("\n[bold]Caissiers disponibles:[/bold]")
        console.print("1. Alice Dupont")
        console.print("2. Bob Martin")
        console.print("3. Claire Dubois")

        while True:
            try:
                caissier_id = int(console.input("Sélectionnez votre identité (1-3): "))
                if 1 <= caissier_id <= 3:
                    self.id_caissier = caissier_id
                    noms = {1: "Alice Dupont", 2: "Bob Martin", 3: "Claire Dubois"}
                    console.print(f"[green]✓ Caissier: {noms[caissier_id]}[/green]")
                    break
                else:
                    console.print("[red]ID de caissier invalide (1-3)[/red]")
            except ValueError:
                console.print("[red]Veuillez entrer un nombre valide[/red]")

        console.input("\nAppuyez sur Entrée pour continuer...")
        console.clear()
        return True

    def afficher_menu_principal(self):
        """Afficher le menu principal selon le type d'entité"""
        caisse_nom = f"Caisse {self.id_caisse}"
        caissier_nom = {1: "Alice", 2: "Bob", 3: "Claire"}.get(self.id_caissier, "Inconnu")

        console.print(Panel.fit(f"Système POS - {caisse_nom} | Caissier: {caissier_nom} | {self.entite.nom}", style="bold blue"))
        
        if self.entite.type_entite == TypeEntite.MAGASIN:
            # Menu pour magasins
            console.print("1. Rechercher un produit")
            console.print("2. Ajouter au panier")
            console.print("3. Voir le panier")
            console.print("4. Finaliser la vente")
            console.print("5. Retourner une vente")
            console.print("6. Consulter stock central")
            console.print("7. Demander approvisionnement")
            console.print("8. Quitter")
        
        elif self.entite.type_entite == TypeEntite.MAISON_MERE:
            # Menu pour maison mère
            console.print("1. Rechercher un produit")
            console.print("2. Ajouter au panier")
            console.print("3. Voir le panier") 
            console.print("4. Finaliser la vente")
            console.print("5. Retourner une vente")
            console.print("6. Générer rapport consolidé des ventes (UC1)")
            console.print("7. Générer rapport des stocks (UC1)")
            console.print("8. Gestion des produits (UC4)")
            console.print("9. Quitter")
            
        elif self.entite.type_entite == TypeEntite.CENTRE_LOGISTIQUE:
            # Menu pour centre logistique
            console.print("1. Rechercher un produit")
            console.print("2. Voir les stocks")
            console.print("3. Traiter demandes d'approvisionnement (UC6)")
            console.print("4. Quitter")
        
        console.print()

    def rechercher_produit(self):
        """Rechercher un produit"""
        console.print("[bold]Recherche de produit[/bold]")
        critere = console.input("Critère (id/nom/categorie): ").strip().lower()
        valeur = console.input("Valeur: ").strip()

        if critere not in ["id", "nom", "categorie"]:
            console.print("[red]Critère invalide[/red]")
            return

        try:
            produits = self.service_produit.rechercher(critere, valeur)
            self.afficher_produits(produits)
        except Exception as e:
            console.print(f"[red]Erreur: {e}[/red]")

    def afficher_produits(self, produits: List[Produit]):
        """Afficher une liste de produits"""
        if not produits:
            console.print("[yellow]Aucun produit trouvé[/yellow]")
            return

        table = Table(title="Produits trouvés")
        table.add_column("ID", style="cyan")
        table.add_column("Nom", style="green")
        table.add_column("Prix", style="yellow")
        table.add_column("Stock", style="blue")
        table.add_column("Catégorie", style="magenta")

        for produit in produits:
            table.add_row(
                str(produit.id),
                produit.nom,
                f"{produit.prix}$",
                str(produit.stock),
                produit.categorie.nom if produit.categorie else "N/A"
            )

        console.print(table)

    def ajouter_au_panier(self):
        """Ajouter un produit au panier"""
        try:
            produit_id = int(console.input("ID du produit: "))
            quantite = int(console.input("Quantité: "))

            produit = self.service_produit.repo_produit.obtenir_par_id(produit_id)
            if not produit:
                console.print("[red]Produit introuvable[/red]")
                return

            if quantite <= 0:
                console.print("[red]Quantité invalide[/red]")
                return

            ligne = LigneVente(produit=produit, qte=quantite)
            self.panier.append(ligne)
            console.print(f"[green]✓ {quantite}x {produit.nom} ajouté(s) au panier[/green]")

        except ValueError:
            console.print("[red]Valeurs invalides[/red]")
        except Exception as e:
            console.print(f"[red]Erreur: {e}[/red]")

    def afficher_panier(self):
        """Afficher le contenu du panier"""
        if not self.panier:
            console.print("[yellow]Panier vide[/yellow]")
            return

        table = Table(title="Panier actuel")
        table.add_column("Produit", style="green")
        table.add_column("Quantité", style="blue")
        table.add_column("Prix unitaire", style="yellow")
        table.add_column("Sous-total", style="cyan")

        total = Decimal('0')
        for ligne in self.panier:
            sous_total = ligne.sous_total
            total += sous_total
            table.add_row(
                ligne.produit.nom,
                str(ligne.qte),
                f"{ligne.produit.prix}$",
                f"{sous_total}$"
            )

        console.print(table)
        console.print(f"[bold]Total: {total}$[/bold]")

    def finaliser_vente(self):
        """Finaliser la vente"""
        if not self.panier:
            console.print("[yellow]Panier vide[/yellow]")
            return

        try:
            vente = self.service_vente.creer_vente(self.panier, self.id_caisse, self.id_caissier, self.id_entite)
            console.print(f"[green]✓ Vente #{vente.id} finalisée avec succès![/green]")
            console.print(f"[green]Total: {vente.total}$[/green]")
            self.panier.clear()

        except Exception as e:
            console.print(f"[red]Erreur lors de la vente: {e}[/red]")

    def retourner_vente(self):
        """Retourner une vente"""
        try:
            vente_id = int(console.input("ID de la vente à retourner: "))

            if self.service_vente.retourner_vente(vente_id):
                console.print(f"[green]✓ Vente #{vente_id} retournée avec succès![/green]")
            else:
                console.print("[red]Impossible de retourner cette vente[/red]")

        except ValueError:
            console.print("[red]ID invalide[/red]")
        except Exception as e:
            console.print(f"[red]Erreur: {e}[/red]")

    def consulter_stock_central(self):
        """Consulter le stock du centre logistique - UC2"""
        console.print("[bold]Consultation du Stock Central[/bold]")
        
        try:
            centre_logistique = self.repo_entite.obtenir_centre_logistique()
            if not centre_logistique:
                console.print("[red]Centre logistique non configuré[/red]")
                return

            console.print(f"[cyan]Centre: {centre_logistique.nom}[/cyan]\n")

            stocks_centraux = self.service_inventaire.obtenir_stocks_par_entite(centre_logistique.id)
            
            if not stocks_centraux:
                console.print("[yellow]Aucun stock disponible au centre logistique[/yellow]")
                return

            table = Table(title="Stock Central Disponible")
            table.add_column("ID", style="cyan")
            table.add_column("Produit", style="green")
            table.add_column("Quantité", style="blue")
            table.add_column("Seuil alerte", style="yellow")
            table.add_column("Statut", style="magenta")

            for stock in stocks_centraux:
                statut = "OK" if stock.quantite > stock.seuil_alerte else "Faible" if stock.quantite > 0 else "Rupture"
                
                table.add_row(
                    str(stock.produit.id),
                    stock.produit.nom,
                    str(stock.quantite),
                    str(stock.seuil_alerte),
                    statut
                )

            console.print(table)

            total_produits = len(stocks_centraux)
            produits_faibles = len([s for s in stocks_centraux if 0 < s.quantite <= s.seuil_alerte])
            produits_rupture = len([s for s in stocks_centraux if s.quantite == 0])

            console.print(f"\n[bold]Résumé:[/bold]")
            console.print(f"- Total produits: {total_produits}")
            console.print(f"- Stock faible: {produits_faibles}")
            console.print(f"- En rupture: {produits_rupture}")

        except Exception as e:
            console.print(f"[red]Erreur lors de la consultation: {e}[/red]")

    def demander_approvisionnement(self):
        """Créer une demande d'approvisionnement - UC2"""
        console.print("[bold]Demande d'Approvisionnement[/bold]")
        
        try:
            centre_logistique = self.repo_entite.obtenir_centre_logistique()
            if not centre_logistique:
                console.print("[red]Centre logistique non configuré[/red]")
                return

            console.print(f"[cyan]Demande depuis votre magasin vers: {centre_logistique.nom}[/cyan]\n")
            
            produit_id = int(console.input("ID du produit à commander: "))
            
            produit = self.service_produit.repo_produit.obtenir_par_id(produit_id)
            if not produit:
                console.print("[red]Produit introuvable[/red]")
                return

            console.print(f"[green]Produit sélectionné: {produit.nom}[/green]")
            
            quantite = int(console.input("Quantité demandée: "))
            if quantite <= 0:
                console.print("[red]Quantité invalide[/red]")
                return
            
            commentaire = console.input("Commentaire (optionnel): ").strip()
            if not commentaire:
                commentaire = f"Demande depuis caisse {self.id_caisse}"

            demande = self.service_approvisionnement.creer_demande_approvisionnement(
                id_entite_demandeur=self.id_entite,
                id_entite_fournisseur=centre_logistique.id,
                id_produit=produit_id,
                quantite=quantite
            )

            self.session.commit()

            console.print(f"[green]✓ Demande d'approvisionnement créée![/green]")
            console.print(f"[green]- ID de la demande: {demande.id}[/green]")
            console.print(f"[green]- Produit: {produit.nom}[/green]")
            console.print(f"[green]- Quantité: {quantite}[/green]")
            console.print(f"[green]- Statut: {demande.statut}[/green]")
            console.print(f"[cyan]→ La demande sera traitée par le centre logistique[/cyan]")

        except ValueError:
            console.print("[red]Valeurs invalides[/red]")
        except Exception as e:
            self.session.rollback()
            console.print(f"[red]Erreur lors de la demande: {e}[/red]")

    def generer_rapport_ventes(self):
        """UC1 - Générer rapport consolidé des ventes"""
        console.print("[bold]Génération du rapport consolidé des ventes[/bold]")
        
        try:
            from datetime import datetime, timedelta
            
            # Demander les dates
            console.print("Période du rapport:")
            jours = int(console.input("Nombre de jours (ex: 7 pour la semaine dernière): "))
            
            date_fin = datetime.now()
            date_debut = date_fin - timedelta(days=jours)
            
            console.print(f"Génération du rapport du {date_debut.strftime('%Y-%m-%d')} au {date_fin.strftime('%Y-%m-%d')}...")
            
            # Générer le rapport
            rapport = self.service_rapport.generer_rapport_ventes_consolide(
                date_debut, date_fin, self.id_caissier
            )
            
            self.session.commit()
            
            console.print(f"[green]✓ Rapport généré avec succès - ID: {rapport.id}[/green]")
            console.print(f"[green]Titre: {rapport.titre}[/green]")
            
            # Afficher un résumé du contenu
            import json
            donnees = json.loads(rapport.contenu_json)
            
            table = Table(title="Résumé du rapport de ventes")
            table.add_column("Magasin", style="green")
            table.add_column("Nombre de ventes", style="blue") 
            table.add_column("Chiffre d'affaires", style="yellow")
            
            for vente_data in donnees.get('ventes_par_magasin', []):
                table.add_row(
                    vente_data['magasin'],
                    str(vente_data['nombre_ventes']),
                    f"{vente_data['chiffre_affaires']}$"
                )
            
            console.print(table)
            
        except Exception as e:
            self.session.rollback()
            console.print(f"[red]Erreur lors de la génération: {e}[/red]")
            
        console.input("\nAppuyez sur Entrée pour continuer...")

    def generer_rapport_stocks(self):
        """UC1 - Générer rapport des stocks"""
        console.print("[bold]Génération du rapport des stocks[/bold]")
        
        try:
            # Générer le rapport
            rapport = self.service_rapport.generer_rapport_stocks(self.id_caissier)
            self.session.commit()
            
            console.print(f"[green]✓ Rapport généré avec succès - ID: {rapport.id}[/green]")
            console.print(f"[green]Titre: {rapport.titre}[/green]")
            
            # Afficher un résumé du contenu
            import json
            donnees = json.loads(rapport.contenu_json)
            
            table = Table(title="Résumé du rapport de stocks")
            table.add_column("Entité", style="green")
            table.add_column("Nb produits", style="blue")
            table.add_column("Produits en rupture", style="red")
            
            for stock_data in donnees.get('stocks_par_entite', []):
                table.add_row(
                    stock_data['nom'],
                    str(stock_data['nombre_produits']),
                    str(stock_data['produits_en_rupture'])
                )
            
            console.print(table)
            
            # Afficher les alertes de rupture
            alertes = donnees.get('alertes_rupture', [])
            if alertes:
                console.print(f"\n[red]⚠️  {len(alertes)} alertes de rupture détectées[/red]")
                for alerte in alertes[:5]:  # Afficher les 5 premières
                    console.print(f"[red]• {alerte['entite']}: {alerte['produit']} (stock: {alerte['stock_actuel']})[/red]")
            
        except Exception as e:
            self.session.rollback()
            console.print(f"[red]Erreur lors de la génération: {e}[/red]")
            
        console.input("\nAppuyez sur Entrée pour continuer...")

    def gestion_produits(self):
        """UC4 - Gestion des produits depuis la maison mère"""
        while True:
            console.print("[bold]Gestion des produits (UC4)[/bold]")
            console.print("1. Lister tous les produits")
            console.print("2. Ajouter un nouveau produit")
            console.print("3. Modifier un produit")
            console.print("4. Rechercher un produit")
            console.print("5. Retour au menu principal")
            
            choix = console.input("Votre choix: ").strip()
            
            if choix == "1":
                self.lister_tous_produits()
            elif choix == "2":
                self.ajouter_nouveau_produit()
            elif choix == "3":
                self.modifier_produit()
            elif choix == "4":
                self.rechercher_produit()
            elif choix == "5":
                break
            else:
                console.print("[red]Choix invalide[/red]")

    def lister_tous_produits(self):
        """Lister tous les produits"""
        try:
            produits = self.service_produit.repo_produit.lister_tous()
            
            if not produits:
                console.print("[yellow]Aucun produit trouvé[/yellow]")
                return
                
            table = Table(title="Catalogue des produits")
            table.add_column("ID", style="cyan")
            table.add_column("Nom", style="green")
            table.add_column("Prix", style="yellow")
            table.add_column("Description", style="white")
            table.add_column("Seuil alerte", style="blue")
            table.add_column("Catégorie", style="magenta")
            
            for produit in produits:
                description = produit.description[:30] + "..." if produit.description and len(produit.description) > 30 else produit.description or "N/A"
                table.add_row(
                    str(produit.id),
                    produit.nom,
                    f"{produit.prix}$",
                    description,
                    str(produit.seuil_alerte),
                    produit.categorie.nom if produit.categorie else "N/A"
                )
            
            console.print(table)
            
        except Exception as e:
            console.print(f"[red]Erreur: {e}[/red]")
        
        console.input("\nAppuyez sur Entrée pour continuer...")

    def ajouter_nouveau_produit(self):
        """Ajouter un nouveau produit"""
        console.print("[bold]Ajout d'un nouveau produit[/bold]")
        
        try:
            nom = console.input("Nom du produit: ").strip()
            prix = float(console.input("Prix ($): "))
            description = console.input("Description (optionnel): ").strip()
            seuil_alerte = int(console.input("Seuil d'alerte: "))
            
            # Afficher les catégories disponibles
            from ..persistence.models import CategorieModel
            categories = self.session.query(CategorieModel).all()
            
            console.print("\nCatégories disponibles:")
            for cat in categories:
                console.print(f"{cat.id}. {cat.nom}")
            
            id_categorie = int(console.input("ID de la catégorie: "))
            
            # Créer le produit
            from ..persistence.models import ProduitModel
            nouveau_produit = ProduitModel(
                nom=nom,
                prix=prix,
                stock=0,
                description=description if description else None,
                seuil_alerte=seuil_alerte,
                id_categorie=id_categorie
            )
            
            self.session.add(nouveau_produit)
            self.session.commit()
            
            console.print(f"[green]✓ Produit '{nom}' ajouté avec succès (ID: {nouveau_produit.id})[/green]")
            
        except ValueError:
            console.print("[red]Erreur: valeurs numériques invalides[/red]")
        except Exception as e:
            self.session.rollback()
            console.print(f"[red]Erreur: {e}[/red]")
        
        console.input("\nAppuyez sur Entrée pour continuer...")

    def modifier_produit(self):
        """Modifier un produit existant"""
        console.print("[bold]Modification d'un produit[/bold]")
        
        try:
            produit_id = int(console.input("ID du produit à modifier: "))
            
            # Récupérer le produit
            from ..persistence.models import ProduitModel
            produit = self.session.query(ProduitModel).filter(ProduitModel.id == produit_id).first()
            
            if not produit:
                console.print("[red]Produit introuvable[/red]")
                return
            
            console.print(f"\nProduit actuel: {produit.nom}")
            console.print(f"Prix actuel: {produit.prix}$")
            console.print(f"Description actuelle: {produit.description or 'Aucune'}")
            console.print(f"Seuil actuel: {produit.seuil_alerte}")
            
            # Demander les nouvelles valeurs
            console.print("\n[yellow]Laissez vide pour conserver la valeur actuelle[/yellow]")
            
            nouveau_nom = console.input(f"Nouveau nom [{produit.nom}]: ").strip()
            if nouveau_nom:
                produit.nom = nouveau_nom
                
            nouveau_prix = console.input(f"Nouveau prix [{produit.prix}]: ").strip()
            if nouveau_prix:
                produit.prix = float(nouveau_prix)
                
            nouvelle_desc = console.input(f"Nouvelle description [{produit.description or 'Aucune'}]: ").strip()
            if nouvelle_desc:
                produit.description = nouvelle_desc
                
            nouveau_seuil = console.input(f"Nouveau seuil [{produit.seuil_alerte}]: ").strip()
            if nouveau_seuil:
                produit.seuil_alerte = int(nouveau_seuil)
            
            self.session.commit()
            console.print(f"[green]✓ Produit modifié avec succès[/green]")
            
        except ValueError:
            console.print("[red]Erreur: valeurs invalides[/red]")
        except Exception as e:
            self.session.rollback()
            console.print(f"[red]Erreur: {e}[/red]")
        
        console.input("\nAppuyez sur Entrée pour continuer...")

    def traiter_demandes_approvisionnement(self):
        """UC6 - Traiter les demandes d'approvisionnement (centre logistique)"""
        console.print("[bold]Traitement des demandes d'approvisionnement (UC6)[/bold]")
        
        try:
            # Lister les demandes en attente
            from ..domain.entities import StatutDemande
            demandes = self.service_approvisionnement.lister_demandes_par_statut(StatutDemande.EN_ATTENTE)
            
            if not demandes:
                console.print("[yellow]Aucune demande en attente[/yellow]")
                console.input("\nAppuyez sur Entrée pour continuer...")
                return
            
            table = Table(title="Demandes d'approvisionnement en attente")
            table.add_column("ID", style="cyan")
            table.add_column("Magasin demandeur", style="green")
            table.add_column("Produit", style="yellow") 
            table.add_column("Quantité demandée", style="blue")
            table.add_column("Date demande", style="white")
            
            for demande in demandes:
                table.add_row(
                    str(demande.id),
                    demande.entite_demandeur.nom if demande.entite_demandeur else "N/A",
                    demande.produit.nom if demande.produit else "N/A",
                    str(demande.quantite_demandee),
                    demande.date_demande.strftime('%Y-%m-%d %H:%M')
                )
            
            console.print(table)
            
            # Traiter une demande
            demande_id = int(console.input("\nID de la demande à traiter (0 pour annuler): "))
            if demande_id == 0:
                return
                
            demande = next((d for d in demandes if d.id == demande_id), None)
            if not demande:
                console.print("[red]Demande introuvable[/red]")
                return
            
            console.print(f"\nTraitement de la demande #{demande.id}")
            console.print(f"Magasin: {demande.entite_demandeur.nom}")
            console.print(f"Produit: {demande.produit.nom}")
            console.print(f"Quantité demandée: {demande.quantite_demandee}")
            
            action = console.input("\nAction (a=approuver, r=rejeter): ").strip().lower()
            
            if action == "a":
                quantite_approuvee = int(console.input("Quantité à approuver: "))
                commentaire = console.input("Commentaire (optionnel): ").strip()
                
                self.service_approvisionnement.approuver_demande(
                    demande.id, quantite_approuvee, commentaire
                )
                
                # Effectuer le transfert
                transfert = self.service_approvisionnement.effectuer_transfert(
                    demande.id, self.id_caissier
                )
                
                console.print(f"[green]✓ Demande approuvée et transfert effectué (ID: {transfert.id})[/green]")
                
            elif action == "r":
                commentaire = console.input("Raison du rejet: ").strip()
                self.service_approvisionnement.rejeter_demande(demande.id, commentaire)
                console.print(f"[yellow]Demande rejetée[/yellow]")
            else:
                console.print("[red]Action invalide[/red]")
                
        except Exception as e:
            console.print(f"[red]Erreur: {e}[/red]")
        
        console.input("\nAppuyez sur Entrée pour continuer...")

    def executer(self):
        """Boucle principale de l'application"""
        max_retries = 10
        retry_count = 0

        while retry_count < max_retries:
            if self.selectionner_caisse_et_caissier():
                break

            retry_count += 1
            console.print(f"[yellow]Tentative {retry_count}/{max_retries} - "
                         f"Aucune caisse disponible. Nouvelle tentative dans 5 secondes...[/yellow]")

            if retry_count < max_retries:
                import time
                time.sleep(5)

        if retry_count >= max_retries:
            console.print("[red]Impossible de configurer la caisse après plusieurs tentatives. Arrêt.[/red]")
            return

        while True:
            try:
                self.afficher_menu_principal()
                choix = console.input("Votre choix: ").strip()

                if self.entite.type_entite == TypeEntite.MAGASIN:
                    # Logique pour magasins
                    if choix == "1":
                        self.rechercher_produit()
                    elif choix == "2":
                        self.ajouter_au_panier()
                    elif choix == "3":
                        self.afficher_panier()
                    elif choix == "4":
                        self.finaliser_vente()
                    elif choix == "5":
                        self.retourner_vente()
                    elif choix == "6":
                        self.consulter_stock_central()
                    elif choix == "7":
                        self.demander_approvisionnement()
                    elif choix == "8":
                        console.print("[blue]Au revoir![/blue]")
                        break
                    else:
                        console.print("[red]Choix invalide[/red]")
                        
                elif self.entite.type_entite == TypeEntite.MAISON_MERE:
                    # Logique pour maison mère - UC1 et UC4
                    if choix == "1":
                        self.rechercher_produit()
                    elif choix == "2":
                        self.ajouter_au_panier()
                    elif choix == "3":
                        self.afficher_panier()
                    elif choix == "4":
                        self.finaliser_vente()
                    elif choix == "5":
                        self.retourner_vente()
                    elif choix == "6":
                        self.generer_rapport_ventes()
                    elif choix == "7":
                        self.generer_rapport_stocks()
                    elif choix == "8":
                        self.gestion_produits()
                    elif choix == "9":
                        console.print("[blue]Au revoir![/blue]")
                        break
                    else:
                        console.print("[red]Choix invalide[/red]")
                        
                elif self.entite.type_entite == TypeEntite.CENTRE_LOGISTIQUE:
                    # Logique pour centre logistique - UC6
                    if choix == "1":
                        self.rechercher_produit()
                    elif choix == "2":
                        self.lister_tous_produits()
                    elif choix == "3":
                        self.traiter_demandes_approvisionnement()
                    elif choix == "4":
                        console.print("[blue]Au revoir![/blue]")
                        break
                    else:
                        console.print("[red]Choix invalide[/red]")

                console.input("\nAppuyez sur Entrée pour continuer...")
                console.clear()

            except KeyboardInterrupt:
                console.print("\n[blue]Au revoir![/blue]")
                break
            except Exception as e:
                console.print(f"[red]Erreur inattendue: {e}[/red]")

    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()
