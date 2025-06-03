from typing import List
from decimal import Decimal
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..persistence.database import get_db_session
from ..domain.services import ServiceProduit, ServiceVente
from ..persistence.repositories import RepositoryCaisse
from ..domain.entities import LigneVente, Produit

console = Console()


class ApplicationConsole:
    def __init__(self):
        self.session = get_db_session()
        self.service_produit = ServiceProduit(self.session)
        self.service_vente = ServiceVente(self.session)
        self.repo_caisse = RepositoryCaisse(self.session)
        self.id_caisse = None
        self.id_caissier = None
        self.panier: List[LigneVente] = []

    def selectionner_caisse_et_caissier(self):
        """Permettre à l'utilisateur de sélectionner sa caisse et son identité"""
        console.print(Panel.fit("🔧 Configuration de la caisse", style="bold yellow"))

        # Afficher les caisses disponibles
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
        """Afficher le menu principal"""
        caisse_nom = f"Caisse {self.id_caisse}"
        caissier_nom = {1: "Alice", 2: "Bob", 3: "Claire"}.get(self.id_caissier, "Inconnu")

        console.print(Panel.fit(f"Système POS - {caisse_nom} | Caissier: {caissier_nom}", style="bold blue"))
        console.print("1. Rechercher un produit")
        console.print("2. Ajouter au panier")
        console.print("3. Voir le panier")
        console.print("4. Finaliser la vente")
        console.print("5. Retourner une vente")
        console.print("6. Quitter")
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
                f"{produit.prix}€",
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
                f"{ligne.produit.prix}€",
                f"{sous_total}€"
            )

        console.print(table)
        console.print(f"[bold]Total: {total}€[/bold]")

    def finaliser_vente(self):
        """Finaliser la vente"""
        if not self.panier:
            console.print("[yellow]Panier vide[/yellow]")
            return

        try:
            vente = self.service_vente.creer_vente(self.panier, self.id_caisse, self.id_caissier)
            console.print(f"[green]✓ Vente #{vente.id} finalisée avec succès![/green]")
            console.print(f"[green]Total: {vente.total}€[/green]")
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
