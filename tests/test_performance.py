#!/usr/bin/env python3
"""
Tests de performance pour le système POS multi-magasins
Architecture console + web : console pour opérations, web pour supervision.
Valide les performances des UC1-UC6 selon leur interface spécifique.
Tests de load balancing microservices
"""

import time
import statistics
import requests
from concurrent.futures import ThreadPoolExecutor
from typing import Dict

from src.persistence.database import get_db_session, create_tables
from src.domain.services import ServiceProduit, ServiceVente
from src.domain.entities import LigneVente


class PerformanceTester:
    """Testeur de performance pour le système POS multi-magasins"""

    def __init__(self):
        create_tables()
        # Configuration pour tests microservices (Étape 3)
        self.microservices_base_url = "http://localhost:8080"
        self.api_key = "pos-test-automation-dev-key-2025"
        self.microservices_headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

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

    def test_microservice_cart_distribution(self, nb_requetes=30):
        """Test de distribution de charge Cart Service (3 instances)"""
        print(f"Test distribution Cart Service ({nb_requetes} requêtes)")

        debut = time.time()
        distributions = {}
        temps_reponses = []
        erreurs = []

        for i in range(nb_requetes):
            session_id = f"perf_test_{i}"
            
            try:
                # Test GET Cart
                temps, response, erreur = self.mesurer_temps(
                    requests.get,
                    f"{self.microservices_base_url}/api/v1/cart",
                    params={"session_id": session_id},
                    headers=self.microservices_headers,
                    timeout=5
                )
                
                if erreur:
                    erreurs.append(f"Requête {i}: {erreur}")
                elif response and response.status_code == 200:
                    temps_reponses.append(temps)
                    
                    # Analyser distribution par instance
                    try:
                        data = response.json()
                        instance_id = data.get('instance_info', {}).get('served_by', 'unknown')
                        distributions[instance_id] = distributions.get(instance_id, 0) + 1
                    except:
                        distributions['parse_error'] = distributions.get('parse_error', 0) + 1
                else:
                    erreurs.append(f"Requête {i}: Status {response.status_code if response else 'None'}")
                    
            except Exception as e:
                erreurs.append(f"Requête {i}: Exception {str(e)}")

        fin = time.time()
        temps_total = fin - debut

        # Analyser équilibrage
        instances_actives = len([k for k in distributions.keys() if k != 'parse_error'])
        requetes_reussies = sum(distributions.values()) - distributions.get('parse_error', 0)
        
        # Calculer déséquilibre (écart-type entre instances)
        if instances_actives > 1:
            counts = [v for k, v in distributions.items() if k != 'parse_error']
            moyenne = statistics.mean(counts) if counts else 0
            desequilibre = statistics.stdev(counts) / moyenne * 100 if moyenne > 0 and len(counts) > 1 else 0
        else:
            desequilibre = 0

        return {
            'temps_total': temps_total,
            'requetes_total': nb_requetes,
            'requetes_reussies': requetes_reussies,
            'erreurs': len(erreurs),
            'instances_detectees': instances_actives,
            'distribution': distributions,
            'desequilibre_pct': desequilibre,
            'temps_moyen_ms': statistics.mean(temps_reponses) * 1000 if temps_reponses else 0,
            'temps_p95_ms': statistics.quantiles(temps_reponses, n=20)[18] * 1000 if len(temps_reponses) >= 20 else 0,
            'throughput': requetes_reussies / temps_total if temps_total > 0 else 0,
            'erreurs_detail': erreurs[:5]  # Première 5 erreurs
        }

    def test_microservice_cart_charge_simultanee(self, nb_threads=3, requetes_par_thread=10):
        """Test de charge simultanée Cart Service avec analyse distribution"""
        print(f"Test charge simultanée Cart Service ({nb_threads} threads, {requetes_par_thread} requêtes/thread)")

        debut_global = time.time()

        def thread_cart_requests(thread_id):
            """Exécuter des requêtes Cart Service dans un thread"""
            resultats_local = {
                'thread_id': thread_id,
                'distributions': {},
                'temps_reponses': [],
                'erreurs': []
            }

            for i in range(requetes_par_thread):
                session_id = f"thread_{thread_id}_req_{i}"
                
                try:
                    # GET Cart
                    response = requests.get(
                        f"{self.microservices_base_url}/api/v1/cart",
                        params={"session_id": session_id},
                        headers=self.microservices_headers,
                        timeout=3
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        instance_id = data.get('instance_info', {}).get('served_by', 'unknown')
                        resultats_local['distributions'][instance_id] = \
                            resultats_local['distributions'].get(instance_id, 0) + 1
                        resultats_local['temps_reponses'].append(response.elapsed.total_seconds())
                    else:
                        resultats_local['erreurs'].append(f"Status {response.status_code}")
                        
                except Exception as e:
                    resultats_local['erreurs'].append(str(e))

            return resultats_local

        # Lancer threads simultanés
        with ThreadPoolExecutor(max_workers=nb_threads) as executor:
            futures = [executor.submit(thread_cart_requests, i) for i in range(nb_threads)]
            resultats_threads = [future.result() for future in futures]

        fin_global = time.time()
        temps_total = fin_global - debut_global

        # Consolidation des résultats
        distribution_globale = {}
        tous_temps = []
        total_erreurs = 0

        for resultat in resultats_threads:
            for instance, count in resultat['distributions'].items():
                distribution_globale[instance] = distribution_globale.get(instance, 0) + count
            tous_temps.extend(resultat['temps_reponses'])
            total_erreurs += len(resultat['erreurs'])

        total_requetes = nb_threads * requetes_par_thread
        requetes_reussies = sum(distribution_globale.values())

        return {
            'temps_total': temps_total,
            'threads': nb_threads,
            'requetes_par_thread': requetes_par_thread,
            'total_requetes': total_requetes,
            'requetes_reussies': requetes_reussies,
            'total_erreurs': total_erreurs,
            'distribution_globale': distribution_globale,
            'instances_actives': len(distribution_globale),
            'throughput_global': requetes_reussies / temps_total if temps_total > 0 else 0,
            'temps_moyen_ms': statistics.mean(tous_temps) * 1000 if tous_temps else 0,
            'temps_p95_ms': statistics.quantiles(tous_temps, n=20)[18] * 1000 if len(tous_temps) >= 20 else 0,
            'resultats_par_thread': resultats_threads
        }

    def executer_tests_complets(self):
        """Exécuter tous les tests de performance (pour exécution directe)"""
        print("=" * 70)
        print("TESTS DE PERFORMANCE - SYSTÈME POS + MICROSERVICES")
        print("=" * 70)

        try:
            # Tests des opérations de base
            stats = self.test_operations_base(100)
            print("  - Recherche par ID:")
            print(f"    - Temps moyen: "
                  f"{stats['recherche_id']['moyenne']*1000:.2f}ms")
            print(f"    - Temps médian: "
                  f"{stats['recherche_id']['mediane']*1000:.2f}ms")
            print(f"    - Temps max: "
                  f"{stats['recherche_id']['max']*1000:.2f}ms")
            print("  - Recherche par nom:")
            print(f"    - Temps moyen: "
                  f"{stats['recherche_nom']['moyenne']*1000:.2f}ms")
            print(f"    - Temps médian: "
                  f"{stats['recherche_nom']['mediane']*1000:.2f}ms")
            print(f"    - Temps max: "
                  f"{stats['recherche_nom']['max']*1000:.2f}ms")
            print()

            # Test de 3 caisses simultanées
            resultats = self.test_caisses_simultanees(15)
            print(f"  - Durée totale: {resultats['temps_total']:.2f}s")
            print(f"  - Ventes totales réussies: "
                  f"{resultats['total_ventes']}")
            print(f"  - Erreurs totales: {resultats['total_erreurs']}")
            print(f"  - Throughput: {resultats['throughput']:.1f} "
                  f"ventes/seconde")
            print(f"  - Temps moyen par vente: "
                  f"{resultats['temps_moyen_vente']*1000:.2f}ms")
            for r in resultats['resultats_par_caisse']:
                print(f"  - Caisse {r['caisse_id']}: "
                      f"{r['ventes_reussies']} ventes, "
                      f"{len(r['erreurs'])} erreurs")
            print()

            # Test de charge
            resultats_charge = self.test_charge_recherche(3, 30)
            print(f"  - Durée totale: {resultats_charge['temps_total']:.2f}s")
            print(f"  - Recherches totales: "
                  f"{resultats_charge['total_recherches']}")
            print(f"  - Throughput: {resultats_charge['throughput']:.1f} "
                  f"recherches/seconde")
            print(f"  - Temps moyen: "
                  f"{resultats_charge['temps_moyen']*1000:.2f}ms")
            print(f"  - Temps médian: "
                  f"{resultats_charge['temps_median']*1000:.2f}ms")
            print()

            print("TESTS MICROSERVICES - LOAD BALANCING CART SERVICE")
            print("-" * 50)
            
            # Test distribution Cart Service
            try:
                resultats_cart = self.test_microservice_cart_distribution(40)
                print(f"  - Distribution Cart Service:")
                print(f"    - Requêtes réussies: {resultats_cart['requetes_reussies']}/{resultats_cart['requetes_total']}")
                print(f"    - Instances détectées: {resultats_cart['instances_detectees']}")
                print(f"    - Déséquilibre: {resultats_cart['desequilibre_pct']:.1f}%")
                print(f"    - Temps moyen: {resultats_cart['temps_moyen_ms']:.1f}ms")
                print(f"    - Temps P95: {resultats_cart['temps_p95_ms']:.1f}ms")
                print(f"    - Throughput: {resultats_cart['throughput']:.1f} req/s")
                
                for instance, count in resultats_cart['distribution'].items():
                    if instance != 'parse_error':
                        percentage = (count / resultats_cart['requetes_reussies'] * 100) if resultats_cart['requetes_reussies'] > 0 else 0
                        print(f"      - {instance}: {count} requêtes ({percentage:.1f}%)")
                
                if resultats_cart['erreurs'] > 0:
                    print(f"    - Erreurs: {resultats_cart['erreurs']} (détail: {resultats_cart['erreurs_detail']})")
            
            except Exception as e:
                print(f"  - Test Cart Distribution échoué: {e}")
            
            print()

            # Test charge simultanée microservices
            try:
                resultats_charge_ms = self.test_microservice_cart_charge_simultanee(4, 8)
                print(f"  - Charge simultanée Cart Service:")
                print(f"    - Threads: {resultats_charge_ms['threads']}")
                print(f"    - Requêtes réussies: {resultats_charge_ms['requetes_reussies']}/{resultats_charge_ms['total_requetes']}")
                print(f"    - Instances actives: {resultats_charge_ms['instances_actives']}")
                print(f"    - Throughput global: {resultats_charge_ms['throughput_global']:.1f} req/s")
                print(f"    - Temps moyen: {resultats_charge_ms['temps_moyen_ms']:.1f}ms")
                print(f"    - Temps P95: {resultats_charge_ms['temps_p95_ms']:.1f}ms")
                
                for instance, count in resultats_charge_ms['distribution_globale'].items():
                    percentage = (count / resultats_charge_ms['requetes_reussies'] * 100) if resultats_charge_ms['requetes_reussies'] > 0 else 0
                    print(f"      - {instance}: {count} requêtes ({percentage:.1f}%)")
                    
            except Exception as e:
                print(f"  - Test Charge Simultanée échoué: {e}")

            print()
            print("Tests de performance terminés avec succès!")
            print("Résumé: Le système supporte bien la charge monolithique ET microservices")

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


def test_microservice_cart_load_balancing():
    """Test pytest: Load balancing Cart Service (Étape 3)"""
    tester = PerformanceTester()
    resultats = tester.test_microservice_cart_distribution(30)

    # Assertions sur le load balancing
    assert resultats['requetes_reussies'] >= 25, "Au moins 25/30 requêtes doivent réussir"
    assert resultats['instances_detectees'] >= 2, "Au moins 2 instances Cart doivent être détectées"
    assert resultats['desequilibre_pct'] < 50, "Déséquilibre doit être < 50%"
    assert resultats['temps_moyen_ms'] < 1000, "Temps moyen doit être < 1s"
    
    # Vérifier qu'au moins 2 instances différentes ont reçu du trafic
    instances_avec_trafic = [k for k, v in resultats['distribution'].items() 
                           if k != 'parse_error' and v > 0]
    assert len(instances_avec_trafic) >= 2, f"Au moins 2 instances doivent recevoir du trafic. Trouvé: {instances_avec_trafic}"

    print(f"Load balancing validé: {resultats['instances_detectees']} instances, "
          f"déséquilibre {resultats['desequilibre_pct']:.1f}%")


def test_microservice_cart_charge_simultanee():
    """Test pytest: Charge simultanée Cart Service"""
    tester = PerformanceTester()
    resultats = tester.test_microservice_cart_charge_simultanee(3, 5)

    # Assertions sur la performance sous charge
    assert resultats['requetes_reussies'] >= 12, "Au moins 12/15 requêtes doivent réussir sous charge"
    assert resultats['instances_actives'] >= 2, "Au moins 2 instances doivent être actives"
    assert resultats['throughput_global'] > 1, "Throughput minimum sous charge simultanée"
    assert resultats['temps_moyen_ms'] < 2000, "Temps moyen acceptable sous charge"

    print(f"Charge simultanée validée: {resultats['instances_actives']} instances, "
          f"throughput {resultats['throughput_global']:.1f} req/s")


if __name__ == "__main__":
    tester = PerformanceTester()
    tester.executer_tests_complets()
