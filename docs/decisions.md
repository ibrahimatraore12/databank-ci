# Journal des décisions de design — dataBank CI Customer 360

**Auteur :** Ibrahima TRAORÉ — Analytics Engineer

Format : Date | Décision | Raison | Alternative écartée

| Date | Décision | Raison | Alternative écartée |
|------|----------|--------|----------------------|
| 2026-07-14 | Environnement dédié `databank-ci-env` (pyenv, Python 3.11.9) isolé du projet `databank-customer360-ci` | Éviter tout conflit de dépendances entre les deux projets, même s'ils partagent la même source de données | Réutiliser l'environnement `databank-c360-env` existant |
| 2026-07-14 | Le score de désengagement est traité comme un scoring de règles métier en Phase 1, et comme une expérimentation ML sur label proxy en Phase 2 | Le dataset n'a pas de churn réel observé (voir `docs/ml_problem_definition.md`) ; présenter un score ML comme une vérité terrain serait trompeur | Entraîner directement un modèle supervisé sans étape de règles métier |
| 2026-07-14 | Génération d'un jeu de données synthétique (`is_synthetic=True`) pour porter le volume de 140 à ~540 clients | Le label naïf (1 critère) n'a que 2 positifs (1,4 %) ; même le label enrichi à 25,0 % reste petit en absolu sur 140 clients — un échantillon de test plus large est nécessaire pour une comparaison de modèles robuste | Entraîner uniquement sur les 140 clients réels et accepter des métriques non fiables |
| 2026-07-14 | Seuil du label enrichi fixé à >= 2 critères sur 4 (et non ajusté pour viser un taux de positifs précis) | Mesuré sur les données réelles : 1 critère = 70 % (trop permissif), 2 critères = 25,0 %, 3 critères = 0,7 % (trop strict). Le seuil à 2 est le compromis le plus défendable, documenté tel quel plutôt que retouché a posteriori pour coller à une cible | Chercher un seuil ou une pondération qui produirait artificiellement 12-15 % de positifs |
| 2026-07-14 | Toutes les données synthétiques restent marquées `is_synthetic=True` dans les tables Gold et dans le dashboard | Traçabilité : ne jamais laisser un utilisateur croire qu'une donnée générée est une donnée réelle | Fusionner silencieusement réel et synthétique |
| 2026-07-14 | Le NBI est estimé par formule UEMOA standard et marqué `estimated_nbi_flag=True` | Le NBI comptable réel n'est pas dans le dataset source | Ne pas produire de NBI du tout |
| 2026-07-14 | `seed=42` et `random_state=42` fixés partout (dbt seeds, split ML, génération synthétique) | Idempotence : rejouer le pipeline doit produire le même résultat à chaque exécution | Graine aléatoire non fixée |
| 2026-07-14 | Aucune classe Python (POO) dans le code métier ; uniquement des fonctions pures enchaînées | Lisibilité pour une relecture humaine rapide, cohérence avec le style de code demandé pour ce projet | Modélisation orientée objet classique (classes `Customer`, `Pipeline`, etc.) |
| 2026-07-14 | Couche sémantique stricte : aucun nom de colonne technique n'apparaît dans le dashboard, tout passe par `LABELS` (`dashboard/components/ui.py`) et les fichiers `i18n/*.json` | Le dashboard est destiné à des conseillers commerciaux, pas à des data engineers | Afficher directement les noms de colonnes SQL/pandas |
| 2026-07-14 | Seuil de retard de paiement (`days_past_due`) fixé à 15 jours pour la correction de statut prêt dans `stg_loans.sql` | Observé en EDA : les prêts `Watchlist`/`Delinquent` réels dépassent ce seuil, les `Current` restent en dessous | Utiliser le `status` brut du fichier source sans le confronter au DPD réel |
