-- mart_retention — D1 / D7 / D30 retention po akvizicijskih kohortah (install_date × kanal).
--
-- OPOMBA o definiciji: ker simulirani podatki nimajo splošnih "app open" dogodkov,
-- retention temelji na PRIHODKOVNI aktivnosti (backend purchase/subscribe). Uporabnik
-- šteje kot zadržan ob DN, če ima kakršenkoli dogodek vsaj N dni po installu
-- (max_day >= N → monotono padajoče). V produkciji bi denominator slonel na sejah.

with activity as (

    -- Atribuirani backend dogodki z odmikom dni od installa.
    select
        user_id,
        channel,
        cast(install_time as date)                      as install_date,
        datediff(day, install_time, event_time)         as day_n
    from {{ ref('stg_backend') }}
    where is_attributed = 1
      and install_time is not null

),

per_user as (

    select
        user_id,
        channel,
        install_date,
        max(day_n) as max_day
    from activity
    group by user_id, channel, install_date

),

cohort as (

    -- Denominator = VSI installi (tudi neplačniki brez dogodkov).
    select
        i.appsflyer_id,
        i.channel_key       as channel,
        i.install_date,
        pu.max_day
    from {{ ref('fct_installs') }} i
    left join per_user pu
        on i.appsflyer_id = pu.user_id

)

select
    channel,
    install_date,
    count(*)                                                    as cohort_size,
    sum(case when max_day >= 1  then 1 else 0 end)              as retained_d1,
    sum(case when max_day >= 7  then 1 else 0 end)              as retained_d7,
    sum(case when max_day >= 30 then 1 else 0 end)              as retained_d30,
    cast(100.0 * sum(case when max_day >= 1  then 1 else 0 end) / count(*) as decimal(6,2)) as retention_d1_pct,
    cast(100.0 * sum(case when max_day >= 7  then 1 else 0 end) / count(*) as decimal(6,2)) as retention_d7_pct,
    cast(100.0 * sum(case when max_day >= 30 then 1 else 0 end) / count(*) as decimal(6,2)) as retention_d30_pct
from cohort
group by channel, install_date
