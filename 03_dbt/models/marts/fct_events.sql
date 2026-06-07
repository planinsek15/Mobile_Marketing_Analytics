-- fct_events — dejstvo prihodkovnih dogodkov (zrno: en in-app dogodek).
-- Vir je MMP (AppsFlyer) poročani prihodek; ključi na dimenzije.

select
    e.appsflyer_id,
    e.channel                           as channel_key,
    concat(e.channel, '|', e.campaign)  as campaign_key,
    e.country_code,
    e.event_date,
    e.event_name,
    e.platform,
    e.event_revenue,
    1                                   as event_count,
    case when e.event_name = 'af_purchase'  then 1 else 0 end as is_purchase,
    case when e.event_name = 'af_subscribe' then 1 else 0 end as is_subscribe
from {{ ref('stg_appsflyer_events') }} e
