# Schéma des données (ERD) - dataBank CI Customer 360

> *[English version: [erd_diagram_en.md](erd_diagram_en.md)]*

**Auteur :** Ibrahima TRAORÉ - Analytics Engineer
**Date :** Juillet 2026

Ce diagramme montre comment les 10 tables sources sont reliées entre elles,
au niveau de l'étape "staging" (`dbt_project/models/staging/`) : un modèle
par table source, chacun gardant le même niveau de détail ("grain") que la
table brute d'origine. `customer_id` (identifiant client) est la clé qui
relie tout le portefeuille de clients. `account_id` (identifiant de compte)
et `channel_id` (identifiant de canal) sont les deux autres clés utilisées
pour relier les tables entre elles dans les modèles "intermediate".

## 1. Schéma relationnel

```mermaid
erDiagram
    CUSTOMERS ||--o{ ACCOUNTS : "detient"
    CUSTOMERS ||--o{ LOANS : "souscrit"
    CUSTOMERS ||--o{ CARDS : "detient"
    CUSTOMERS ||--o{ TRANSACTIONS : "emet"
    CUSTOMERS ||--o{ COMPLAINTS : "depose"
    CUSTOMERS ||--o{ INTERACTIONS : "a"
    CUSTOMERS ||--o{ OFFERS : "recoit"
    CUSTOMERS }o--|| BRANCHES : "agence principale"
    ACCOUNTS ||--o{ TRANSACTIONS : "enregistre"
    ACCOUNTS ||--o{ CARDS : "lie a"
    ACCOUNTS ||--o{ LOANS : "compte de remboursement"
    ACCOUNTS }o--|| BRANCHES : "ouvert a"
    TRANSACTIONS }o--|| CHANNELS : "via"

    CUSTOMERS {
        varchar customer_id PK
        varchar segment
        varchar risk_band
        date onboarding_date
        varchar preferred_channel
        boolean is_synthetic
    }
    ACCOUNTS {
        varchar account_id PK
        varchar customer_id FK
        varchar account_type
        decimal current_balance_xof
        decimal avg_balance_90d_xof
        boolean salary_domiciled_flag
    }
    TRANSACTIONS {
        varchar txn_id PK
        varchar account_id FK
        varchar customer_id FK
        varchar channel_id FK
        timestamp txn_datetime
        decimal amount_xof
    }
    LOANS {
        varchar loan_id PK
        varchar customer_id FK
        varchar repayment_account_id FK
        integer days_past_due
        varchar status
    }
    CARDS {
        varchar card_id PK
        varchar customer_id FK
        varchar account_id FK
        varchar card_type
        varchar status
    }
    COMPLAINTS {
        varchar complaint_id PK
        varchar customer_id FK
        varchar severity
        varchar status
    }
    INTERACTIONS {
        varchar interaction_id PK
        varchar customer_id FK
        varchar sentiment
        boolean resolved_flag
    }
    OFFERS {
        varchar offer_id PK
        varchar customer_id FK
        varchar offer_type
        boolean accepted_flag
    }
    BRANCHES {
        varchar branch_id PK
        varchar city
    }
    CHANNELS {
        varchar channel_id PK
        varchar channel_name
        varchar channel_group
    }
```

Note de lecture : `PK` signifie "clé primaire" (l'identifiant unique de
chaque ligne de la table). `FK` signifie "clé étrangère" (une colonne qui
pointe vers l'identifiant d'une autre table, pour créer le lien entre les
deux).

## 2. Niveau de détail de chaque table

| Table | Niveau de détail (une ligne =) | Modèle staging correspondant |
|-------|-------|-----------------|
| Customers (clients) | 1 client | `stg_customers.sql` |
| Accounts (comptes) | 1 compte (un client peut avoir plusieurs comptes) | `stg_accounts.sql` |
| Transactions | 1 transaction | `stg_transactions.sql` |
| Loans (prêts) | 1 prêt | `stg_loans.sql` |
| Cards (cartes) | 1 carte | `stg_cards.sql` |
| Complaints (réclamations) | 1 réclamation | `stg_complaints.sql` |
| Interactions | 1 échange avec un conseiller | `stg_interactions.sql` |
| Offers (offres) | 1 offre proposée à un client | `stg_offers.sql` |
| Branches (agences) | 1 agence (donnée de référence, réelle uniquement) | `stg_branches.sql` |
| Channels (canaux) | 1 canal de contact (donnée de référence, réelle uniquement) | `stg_channels.sql` |

Deux tables (`Branches` et `Channels`) sont des données de référence
fixes : elles n'ont pas de version synthétique dans `_sources.yml`,
contrairement aux 8 autres tables, qui possèdent chacune une table
`bronze_synthetic_*` associée, fusionnée dès l'étape Bronze.

## 3. Comment ce schéma devient la table finale `customer_360`

Toutes les tables détaillées au niveau "transaction / compte / prêt" sont
d'abord regroupées au niveau "client" dans
`dbt_project/models/intermediate/` (un modèle par sujet : récence,
tendance, réclamations, score numérique, produits, solde, revenu généré,
canal, prêts). Elles sont ensuite réunies en une seule ligne par client
dans `dbt_project/models/marts/customer_360.sql`. Le détail de chaque
colonne de cette table finale est expliqué dans
`docs/data_dictionary.md`.
