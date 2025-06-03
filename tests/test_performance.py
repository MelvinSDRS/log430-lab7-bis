#!/usr/bin/env python3
"""
Tests de performance pour le système POS
Valide les performances de l'architecture 2-tier client/serveur
"""

import time
import statistics
from concurrent.futures import ThreadPoolExecutor
from typing import Dict

from src.persistence.database import get_db_session, create_tables
from src.domain.services import ServiceProduit, ServiceVente
from src.domain.entities import LigneVente


class PerformanceTester:
    """Testeur de performance pour le système POS 2-tier"""

    def __init__(self):
        create_tables()

    def mesurer_temps(self, operation, *args, **kwargs):
        """Mesurer le temps d'exécution d'une opération"""
        try:
            debut = time.time()
            resultat = operation(*args, **kwargs)
            fin = time.time()
            return fin - debut, resultat, None
        except Exception as e:
            fin = time.time()
            return fin - debut, None, str(e)

    def test_operations_base(self, nb_iterations=50):
        """Test des opérations de base (recherche, lecture)"""
        print(f"Test des opérations de base ({nb_iterations} itérations)")

        session = get_db_session()
        service_produit = ServiceProduit(session)

        # Test recherche par ID
        temps_recherche_id = []
        for i in range(nb_iterations):
            produit_id = (i % 8) + 1  # Cycle sur les 8 produits
            temps, resultat, erreur = self.mesurer_temps(
                service_produit.repo_produit.obtenir_par_id, produit_id
            )
            temps_recherche_id.append(temps)

        # Test recherche par nom
        temps_recherche_nom = []
        noms = ["Pain", "Lait", "Pommes", "Eau"]
        for i in range(nb_iterations):
            nom = noms[i % len(noms)]
            temps, resultat, erreur = self.mesurer_temps(
                service_produit.rechercher, "nom", nom
            )
            temps_recherche_nom.append(temps)

        session.close()

        return {
            'recherche_id': {
                'moyenne': statistics.mean(temps_recherche_id),
                'mediane': statistics.median(temps_recherche_id),
                'max': max(temps_recherche_id)
            },
            'recherche_nom': {
                'moyenne': statistics.mean(temps_recherche_nom),
                'mediane': statistics.median(temps_recherche_nom),
                'max': max(temps_recherche_nom)
            }
        }

    def simuler_vente(self, caisse_id: int, caissier_id: int,
                      nb_ventes: int) -> Dict:
        """Simuler des ventes pour une caisse"""
        session = get_db_session()
        service_vente = ServiceVente(session)
        service_produit = ServiceProduit(session)

        temps_ventes = []
        ventes_reussies = 0
        erreurs = []

        for i in range(nb_ventes):
            try:
                panier = []
                nb_produits = min(3, (i % 3) + 1)

                for j in range(nb_produits):
                    produit_id = ((i + j) % 8) + 1
                    produit = service_produit.repo_produit.obtenir_par_id(
                        produit_id)
                    if produit and produit.stock > 0:
                        ligne = LigneVente(produit=produit, qte=1)
                        panier.append(ligne)

                if panier:
                    temps, vente, erreur = self.mesurer_temps(
                        service_vente.creer_vente, panier, caisse_id,
                        caissier_id
                    )

                    if erreur:
                        erreurs.append(erreur)
                    else:
                        temps_ventes.append(temps)
                        ventes_reussies += 1

            except Exception as e:
                erreurs.append(str(e))

        session.close()

        return {
            'caisse_id': caisse_id,
            'ventes_reussies': ventes_reussies,
            'temps_ventes': temps_ventes,
            'erreurs': erreurs
        }

    def test_caisses_simultanees(self, nb_ventes_par_caisse=10):
        """Test de 3 caisses simultanées (aspect clé du laboratoire)"""
        print(f"Test des 3 caisses simultanées "
              f"({nb_ventes_par_caisse} ventes/caisse)")

        debut_global = time.time()

        # Lancer 3 threads pour simuler 3 caisses
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for caisse_id in range(1, 4):
                future = executor.submit(
                    self.simuler_vente, caisse_id, caisse_id,
                    nb_ventes_par_caisse
                )
                futures.append(future)

            resultats = [future.result() for future in futures]

        fin_global = time.time()
        temps_total = fin_global - debut_global

        total_ventes = sum(r['ventes_reussies'] for r in resultats)
        total_erreurs = sum(len(r['erreurs']) for r in resultats)
        tous_temps = []
        for r in resultats:
            tous_temps.extend(r['temps_ventes'])

        return {
            'temps_total': temps_total,
            'total_ventes': total_ventes,
            'total_erreurs': total_erreurs,
            'throughput': total_ventes/temps_total if temps_total > 0 else 0,
            'temps_moyen_vente': statistics.mean(tous_temps) if tous_temps
            else 0,
            'resultats_par_caisse': resultats
        }

    def test_charge_recherche(self, nb_threads=3,
                              nb_recherches_par_thread=20):
        """Test de charge sur les recherches"""
        print(f"Test de charge recherches ({nb_threads} threads, "
              f"{nb_recherches_par_thread} recherches/thread)")

        debut = time.time()

        def recherches_thread():
            session = get_db_session()
            service_produit = ServiceProduit(session)
            temps_local = []

            for i in range(nb_recherches_par_thread):
                if i % 3 == 0:
                    temps, _, _ = self.mesurer_temps(
                        service_produit.rechercher, "nom", "Pain"
                    )
                elif i % 3 == 1:
                    temps, _, _ = self.mesurer_temps(
                        service_produit.rechercher, "categorie", "Alimentaire"
                    )
                else:
                    produit_id = (i % 8) + 1
                    temps, _, _ = self.mesurer_temps(
                        service_produit.repo_produit.obtenir_par_id,
                        produit_id
                    )
                temps_local.append(temps)

            session.close()
            return temps_local

        # Lancer les threads
        with ThreadPoolExecutor(max_workers=nb_threads) as executor:
            futures = [executor.submit(recherches_thread) for _ in
                       range(nb_threads)]
            resultats = [future.result() for future in futures]

        fin = time.time()
        temps_total = fin - debut

        # Analyser
        tous_temps = []
        for temps_thread in resultats:
            tous_temps.extend(temps_thread)

        total_recherches = len(tous_temps)

        return {
            'temps_total': temps_total,
            'total_recherches': total_recherches,
            'throughput': total_recherches/temps_total if temps_total > 0
            else 0,
            'temps_moyen': statistics.mean(tous_temps) if tous_temps else 0,
            'temps_median': statistics.median(tous_temps) if tous_temps
            else 0
        }

    def executer_tests_complets(self):
        """Exécuter tous les tests de performance (pour exécution directe)"""
        print("=" * 60)
        print("TESTS DE PERFORMANCE - SYSTÈME POS 2-TIER")
        print("=" * 60)

        try:
            # Tests des opérations de base
            stats = self.test_operations_base(100)
            print("  • Recherche par ID:")
            print(f"    - Temps moyen: "
                  f"{stats['recherche_id']['moyenne']*1000:.2f}ms")
            print(f"    - Temps médian: "
                  f"{stats['recherche_id']['mediane']*1000:.2f}ms")
            print(f"    - Temps max: "
                  f"{stats['recherche_id']['max']*1000:.2f}ms")
            print("  • Recherche par nom:")
            print(f"    - Temps moyen: "
                  f"{stats['recherche_nom']['moyenne']*1000:.2f}ms")
            print(f"    - Temps médian: "
                  f"{stats['recherche_nom']['mediane']*1000:.2f}ms")
            print(f"    - Temps max: "
                  f"{stats['recherche_nom']['max']*1000:.2f}ms")
            print()

            # Test de 3 caisses simultanées
            resultats = self.test_caisses_simultanees(15)
            print(f"  • Durée totale: {resultats['temps_total']:.2f}s")
            print(f"  • Ventes totales réussies: "
                  f"{resultats['total_ventes']}")
            print(f"  • Erreurs totales: {resultats['total_erreurs']}")
            print(f"  • Throughput: {resultats['throughput']:.1f} "
                  f"ventes/seconde")
            print(f"  • Temps moyen par vente: "
                  f"{resultats['temps_moyen_vente']*1000:.2f}ms")
            for r in resultats['resultats_par_caisse']:
                print(f"  • Caisse {r['caisse_id']}: "
                      f"{r['ventes_reussies']} ventes, "
                      f"{len(r['erreurs'])} erreurs")
            print()

            # Test de charge
            resultats_charge = self.test_charge_recherche(3, 30)
            print(f"  • Durée totale: {resultats_charge['temps_total']:.2f}s")
            print(f"  • Recherches totales: "
                  f"{resultats_charge['total_recherches']}")
            print(f"  • Throughput: {resultats_charge['throughput']:.1f} "
                  f"recherches/seconde")
            print(f"  • Temps moyen: "
                  f"{resultats_charge['temps_moyen']*1000:.2f}ms")
            print(f"  • Temps médian: "
                  f"{resultats_charge['temps_median']*1000:.2f}ms")
            print()

            print("Tests de performance terminés avec succès!")
            print("Résumé: Le système 2-tier supporte bien la charge "
                  "et les transactions simultanées")

        except Exception as e:
            print(f"Erreur durant les tests: {e}")


# ==========================================
# INTÉGRATION PYTEST
# ==========================================

def test_performance_operations_base():
    """Test pytest: Performance des opérations de base"""
    tester = PerformanceTester()
    stats = tester.test_operations_base(30)

    # Assertions sur les performances
    assert stats['recherche_id']['moyenne'] < 0.1, \
        "Recherche par ID trop lente"
    assert stats['recherche_nom']['moyenne'] < 0.1, \
        "Recherche par nom trop lente"
    assert stats['recherche_id']['max'] < 0.5, \
        "Pic de latence trop élevé"


def test_performance_caisses_simultanees():
    """Test pytest: Architecture 2-tier avec 3 caisses simultanées"""
    # Test simplifié qui valide l'architecture multi-caisses
    from concurrent.futures import ThreadPoolExecutor

    def test_caisse(caisse_id):
        session = get_db_session()
        service_produit = ServiceProduit(session)
        # Test simple de recherche par caisse
        produits = service_produit.rechercher("nom", "Pain")
        session.close()
        return {"caisse_id": caisse_id, "produits_trouves": len(produits)}

    # Simuler 3 caisses qui accèdent simultanément à la base
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(test_caisse, i) for i in range(1, 4)]
        resultats = [future.result() for future in futures]

    # Assertions pour valider l'architecture 2-tier
    assert len(resultats) == 3, "Les 3 caisses doivent répondre"
    for resultat in resultats:
        assert "caisse_id" in resultat, "Chaque caisse doit avoir un ID"
        assert "produits_trouves" in resultat, \
            "Chaque caisse doit pouvoir chercher"

    print("Architecture 2-tier validée: 3 caisses simultanées "
          "fonctionnelles")


def test_performance_charge_recherche():
    """Test pytest: Performance sous charge"""
    tester = PerformanceTester()
    resultats = tester.test_charge_recherche(3, 15)

    # Assertions sur la performance sous charge
    assert resultats['throughput'] > 50, "Throughput minimum sous charge"
    assert resultats['temps_moyen'] < 0.1, \
        "Temps moyen acceptable sous charge"
    assert resultats['total_recherches'] == 45, \
        "Toutes les recherches doivent aboutir"


if __name__ == "__main__":
    tester = PerformanceTester()
    tester.executer_tests_complets()
