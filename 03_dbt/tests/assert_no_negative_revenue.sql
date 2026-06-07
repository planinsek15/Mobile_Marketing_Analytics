-- KAKOVOST: prihodek ne sme biti negativen (ne v MMP ne v backendu).
-- Vrne vrstice z negativnim prihodkom → napaka, če jih je kaj.

select 'appsflyer' as vir, appsflyer_id as id, event_revenue as revenue
from {{ ref('stg_appsflyer_events') }}
where event_revenue < 0

union all

select 'backend' as vir, user_id as id, revenue
from {{ ref('stg_backend') }}
where revenue < 0
