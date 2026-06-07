-- mart_marketing_unified — poenoten marketinški pogled.
-- Združi porabo (Singular), installe (AppsFlyer) in prihodek (AppsFlyer events)
-- na skupnem zrnu: channel × campaign × geo × date.
--
-- FULL OUTER JOIN, ker se viri ne pokrivajo popolnoma (poraba brez installov,
-- organski installi brez porabe, prihodek na dan brez nove porabe ipd.).

with spend as (

    select
        spend_date          as activity_date,
        channel_key,
        campaign_key,
        country_code,
        sum(impressions)    as impressions,
        sum(clicks)         as clicks,
        sum(network_installs) as network_installs,
        sum(cost)           as cost
    from {{ ref('fct_spend') }}
    group by spend_date, channel_key, campaign_key, country_code

),

installs as (

    select
        install_date        as activity_date,
        channel_key,
        campaign_key,
        country_code,
        sum(install_count)  as installs
    from {{ ref('fct_installs') }}
    group by install_date, channel_key, campaign_key, country_code

),

revenue as (

    select
        event_date          as activity_date,
        channel_key,
        campaign_key,
        country_code,
        sum(event_revenue)  as revenue,
        sum(event_count)    as revenue_events,
        count(distinct appsflyer_id) as paying_users
    from {{ ref('fct_events') }}
    group by event_date, channel_key, campaign_key, country_code

),

unified as (

    select
        coalesce(s.activity_date, i.activity_date, r.activity_date) as activity_date,
        coalesce(s.channel_key,  i.channel_key,  r.channel_key)     as channel_key,
        coalesce(s.campaign_key, i.campaign_key, r.campaign_key)    as campaign_key,
        coalesce(s.country_code, i.country_code, r.country_code)    as country_code,
        coalesce(s.impressions, 0)      as impressions,
        coalesce(s.clicks, 0)           as clicks,
        coalesce(s.network_installs, 0) as network_installs,
        coalesce(s.cost, 0)             as cost,
        coalesce(i.installs, 0)         as installs,
        coalesce(r.revenue, 0)          as revenue,
        coalesce(r.revenue_events, 0)   as revenue_events,
        coalesce(r.paying_users, 0)     as paying_users
    from spend s
    full outer join installs i
        on  s.activity_date = i.activity_date
        and s.channel_key   = i.channel_key
        and s.campaign_key  = i.campaign_key
        and s.country_code  = i.country_code
    full outer join revenue r
        on  coalesce(s.activity_date, i.activity_date) = r.activity_date
        and coalesce(s.channel_key,  i.channel_key)    = r.channel_key
        and coalesce(s.campaign_key, i.campaign_key)   = r.campaign_key
        and coalesce(s.country_code, i.country_code)   = r.country_code

)

select
    *,
    -- Izvedene metrike na vrstici (osnova za Faza 5).
    case when installs > 0 then cast(cost / installs as decimal(12,2)) end as cpi,
    case when cost   > 0 then cast(revenue / cost   as decimal(12,4)) end as roas
from unified
