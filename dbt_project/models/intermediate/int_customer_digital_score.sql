-- Score digital brut 0-3 : nombre de canaux digitaux activés par le client
-- Raw 0-3 digital score: number of digital channels activated by the customer

select
    customer_id,
    (case when mobile_app_active then 1 else 0 end
     + case when internet_banking_active then 1 else 0 end
     + case when mobile_money_linked then 1 else 0 end) as score_digital
from {{ ref('stg_customers') }}
