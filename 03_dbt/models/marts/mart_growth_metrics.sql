-- mart_growth_metrics — ključne metrike rasti po kanalu × kampanji.
--
--   CPI       = cost / installs
--   CAC       = cost / paying_users          (strošek na plačujočega uporabnika)
--   ROAS_D7   = revenue_d7  / cost           (kohortni prihodek v 7 dneh po installu)
--   ROAS_D30  = revenue_d30 / cost           (kohortni prihodek v 30 dneh)
--   LTV       = preprosta napoved iz zgodnjih kohort (ARPU × naivni D30→D90 faktor)
--
-- BLENDED vs SKAN-only:
--   blended (deterministični) metrike slonijo na AppsFlyer atribuciji (vse platforme).
--   Ob njih postavimo SKAN-only signale (iOS postbacki, brez user-level joina) —
--   v dobi ATT je deterministična iOS atribucija nezanesljiva, SKAN pa agregaten.

{% set ltv_d30_to_d90 = 1.4 %}  -- naivni ekstrapolacijski faktor (dokumentiran približek)

with installs as (

    select channel_key, campaign_key, campaign, country_code, appsflyer_id, install_date, platform
    from {{ ref('fct_installs') }}

),

spend as (

    select
        channel_key,
        campaign_key,
        sum(cost)               as cost,
        sum(impressions)        as impressions,
        sum(clicks)             as clicks,
        sum(network_installs)   as network_installs
    from {{ ref('fct_spend') }}
    group by channel_key, campaign_key

),

inst_agg as (

    select
        channel_key,
        campaign_key,
        max(campaign)                                           as campaign,
        count(*)                                               as installs,
        sum(case when platform = 'ios' then 1 else 0 end)      as ios_installs
    from installs
    group by channel_key, campaign_key

),

-- Kohortni prihodek: dogodek pripišemo akvizicijski kohorti naprave in merimo
-- odmik dni od installa (za ROAS D7/D30).
ev_cohort as (

    select
        i.channel_key,
        i.campaign_key,
        e.appsflyer_id,
        e.event_revenue,
        datediff(day, i.install_date, e.event_date) as day_n
    from installs i
    join {{ ref('fct_events') }} e
        on i.appsflyer_id = e.appsflyer_id

),

rev as (

    select
        channel_key,
        campaign_key,
        sum(event_revenue)                                              as revenue_total,
        sum(case when day_n between 0 and 7  then event_revenue else 0 end) as revenue_d7,
        sum(case when day_n between 0 and 30 then event_revenue else 0 end) as revenue_d30,
        count(distinct appsflyer_id)                                   as paying_users
    from ev_cohort
    group by channel_key, campaign_key

),

-- SKAN-only signal po kampanji (iOS agregat, brez user-level povezave).
skan as (

    select
        campaign                                                       as campaign,
        count(*)                                                       as skan_postbacks,
        sum(case when cv_band in ('low','medium','high') then 1 else 0 end) as skan_conversions,
        sum(case when cv_band = 'high' then 1 else 0 end)              as skan_high_value,
        sum(is_crowd_anonymized)                                       as skan_null_cv
    from {{ ref('stg_skan') }}
    group by campaign

)

select
    ia.channel_key,
    ia.campaign_key,
    ia.campaign,
    -- Obseg
    coalesce(sp.cost, 0)                as cost,
    ia.installs,
    ia.ios_installs,
    coalesce(r.paying_users, 0)         as paying_users,
    coalesce(r.revenue_total, 0)        as revenue_total,
    coalesce(r.revenue_d7, 0)           as revenue_d7,
    coalesce(r.revenue_d30, 0)          as revenue_d30,

    -- Metrike učinkovitosti (NULL, kadar deljenje ni smiselno — npr. organic brez porabe)
    case when ia.installs > 0 and sp.cost > 0
         then cast(sp.cost / ia.installs as decimal(12,2)) end          as cpi,
    case when r.paying_users > 0 and sp.cost > 0
         then cast(sp.cost / r.paying_users as decimal(12,2)) end       as cac,
    case when sp.cost > 0
         then cast(r.revenue_d7  / sp.cost as decimal(12,4)) end        as roas_d7,
    case when sp.cost > 0
         then cast(r.revenue_d30 / sp.cost as decimal(12,4)) end        as roas_d30,

    -- LTV: ARPU (na install) in naivna napoved D90
    case when ia.installs > 0
         then cast(r.revenue_total * 1.0 / ia.installs as decimal(12,2)) end as arpu,
    case when r.paying_users > 0
         then cast(r.revenue_total * 1.0 / r.paying_users as decimal(12,2)) end as arppu,
    case when ia.installs > 0
         then cast(r.revenue_d30 * 1.0 / ia.installs * {{ ltv_d30_to_d90 }} as decimal(12,2)) end
                                                                        as predicted_ltv_d90,

    -- SKAN-only (iOS agregat) ob deterministični sliki
    coalesce(sk.skan_postbacks, 0)      as skan_postbacks,
    coalesce(sk.skan_conversions, 0)    as skan_conversions,
    coalesce(sk.skan_high_value, 0)     as skan_high_value,
    coalesce(sk.skan_null_cv, 0)        as skan_null_cv
from inst_agg ia
left join spend sp on ia.channel_key = sp.channel_key and ia.campaign_key = sp.campaign_key
left join rev   r  on ia.channel_key = r.channel_key  and ia.campaign_key = r.campaign_key
left join skan  sk on ia.campaign = sk.campaign
