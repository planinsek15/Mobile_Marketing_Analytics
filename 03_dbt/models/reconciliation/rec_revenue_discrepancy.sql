-- rec_revenue_discrepancy — dnevni prihodek MMP vs backend po kanalu, stran ob strani.
--
-- To je jedro reconciliation plasti: postavi AppsFlyer (MMP) poročani prihodek ob
-- backend (vir resnice) prihodek po channel × dan in izračuna razliko (% in absolutno).
-- Neskladja izvirajo iz: ~15 % razlike v revenue, poznih dogodkov (premik datuma),
-- odstranjenih dvojnikov in dogodkov, ki jih MMP ne vidi.
--
-- is_discrepancy_flag = 1, kadar |delta| > 5 % (prag za opozorilo).

with mmp as (

    select
        channel,
        event_date                 as activity_date,
        sum(event_revenue)         as mmp_revenue,
        count(*)                   as mmp_events
    from {{ ref('stg_appsflyer_events') }}
    group by channel, event_date

),

backend as (

    -- Le ATRIBUIRANI backend dogodki imajo kanal (neatribuirani → rec_attribution_gap).
    select
        channel,
        event_date                 as activity_date,
        sum(revenue)               as backend_revenue,
        count(*)                   as backend_events
    from {{ ref('stg_backend') }}
    where is_attributed = 1
    group by channel, event_date

),

joined as (

    select
        coalesce(m.channel, b.channel)              as channel,
        coalesce(m.activity_date, b.activity_date)  as activity_date,
        coalesce(m.mmp_revenue, 0)                  as mmp_revenue,
        coalesce(b.backend_revenue, 0)              as backend_revenue,
        coalesce(m.mmp_events, 0)                   as mmp_events,
        coalesce(b.backend_events, 0)               as backend_events
    from mmp m
    full outer join backend b
        on m.channel = b.channel
       and m.activity_date = b.activity_date

)

select
    channel,
    activity_date,
    mmp_revenue,
    backend_revenue,
    cast(backend_revenue - mmp_revenue as decimal(14,2))    as revenue_delta,
    case when mmp_revenue = 0 then null
         else cast(100.0 * (backend_revenue - mmp_revenue) / mmp_revenue as decimal(8,2))
    end                                                     as revenue_delta_pct,
    mmp_events,
    backend_events,
    case
        when mmp_revenue = 0 and backend_revenue > 0 then 1   -- backend vidi, MMP ne
        when mmp_revenue = 0 then 0
        when abs(backend_revenue - mmp_revenue) / mmp_revenue > 0.05 then 1
        else 0
    end                                                     as is_discrepancy_flag
from joined
