-- mart_privacy_roas_gap — privacy-aware plast (senior diferenciator).
--
-- Postavi tri merilne perspektive ene kampanje drug ob drugega:
--   1) MMP (AppsFlyer)  — deterministična atribucija, kar poroča MMP,
--   2) BACKEND          — vir resnice (potrjen prihodek atribuiranih uporabnikov),
--   3) SKAN             — agregirani iOS postbacki (privacy-safe, brez user joina).
--
-- ROAS GAP = MMP ROAS − backend potrjeni ROAS. Pozitiven gap pomeni, da MMP
-- precenjuje donosnost glede na to, kar backend dejansko potrdi.
--
-- has_crowd_anonymity = 1, kadar ima kampanja SKAN postbacke z NULL conversion_value
-- (Apple zadrži vrednost zaradi k-anonimnosti) — takrat je SKAN signal nezanesljiv,
-- deterministična iOS atribucija pa ob nizkem ATT opt-inu prav tako.

with gm as (

    select
        channel_key,
        campaign_key,
        campaign,
        cost,
        installs,
        ios_installs,
        revenue_d30                 as mmp_revenue_d30,
        roas_d30                    as mmp_roas_d30,
        skan_postbacks,
        skan_conversions,
        skan_high_value,
        skan_null_cv
    from {{ ref('mart_growth_metrics') }}

),

-- Backend potrjeni kohortni prihodek (D30) po kanalu × kampanji.
backend as (

    select
        channel                             as channel_key,
        concat(channel, '|', campaign)      as campaign_key,
        sum(case when datediff(day, install_time, event_time) between 0 and 30
                 then revenue else 0 end)   as backend_revenue_d30,
        count(distinct user_id)             as backend_paying_users
    from {{ ref('stg_backend') }}
    where is_attributed = 1
      and install_time is not null
    group by channel, campaign

)

select
    gm.channel_key,
    gm.campaign_key,
    gm.campaign,
    gm.cost,
    gm.installs,
    gm.ios_installs,

    -- Tri perspektive prihodka
    gm.mmp_revenue_d30,
    coalesce(b.backend_revenue_d30, 0)                          as backend_revenue_d30,

    -- ROAS po perspektivi
    gm.mmp_roas_d30,
    case when gm.cost > 0
         then cast(coalesce(b.backend_revenue_d30, 0) / gm.cost as decimal(12,4)) end as backend_roas_d30,

    -- ROAS GAP (MMP − backend)
    case when gm.cost > 0
         then cast((gm.mmp_revenue_d30 - coalesce(b.backend_revenue_d30, 0)) / gm.cost as decimal(12,4)) end
                                                                as roas_gap,
    case when gm.mmp_revenue_d30 > 0
         then cast(100.0 * (gm.mmp_revenue_d30 - coalesce(b.backend_revenue_d30, 0)) / gm.mmp_revenue_d30 as decimal(8,2)) end
                                                                as revenue_overstatement_pct,

    -- SKAN pokritost in zasebnostni signal
    gm.skan_postbacks,
    gm.skan_conversions,
    gm.skan_high_value,
    gm.skan_null_cv,
    case when gm.skan_null_cv > 0 then 1 else 0 end             as has_crowd_anonymity,
    case when gm.skan_postbacks > 0
         then cast(100.0 * gm.skan_null_cv / gm.skan_postbacks as decimal(6,2)) end as skan_null_cv_pct
from gm
left join backend b
    on gm.channel_key = b.channel_key
   and gm.campaign_key = b.campaign_key
