-- stg_backend — backend dogodki: DEDUPLIKACIJA + obogatitev z atribucijo + late flag.
--
--  1) DEDUP: ROW_NUMBER() po (user_id, event, event_time) — odstrani ~3 % popolnih dvojnikov.
--  2) ATRIBUCIJA: LEFT JOIN na stg_appsflyer (user_id == appsflyer_id) →
--     pridobi kanal/kampanjo/geo/install_time. is_attributed = 0 za neatribuirane.
--  3) POZNI DOGODKI: is_late_event = event_time > 21 dni po installu
--     (dogodek izven tipičnega atribucijskega okna).

with deduped as (

    select
        user_id,
        event,
        revenue,
        cast(event_time as datetime2(0)) as event_time,
        row_number() over (
            partition by user_id, event, cast(event_time as datetime2(0))
            order by revenue desc
        ) as rn
    from {{ source('raw', 'backend') }}

),

clean as (

    select user_id, event, revenue, event_time
    from deduped
    where rn = 1

),

attribution as (

    select
        appsflyer_id,
        channel,
        campaign,
        country_code,
        platform,
        install_time
    from {{ ref('stg_appsflyer') }}

)

select
    c.user_id,
    c.event,
    c.revenue,
    c.event_time,
    cast(c.event_time as date)                          as event_date,
    a.channel,
    a.campaign,
    a.country_code,
    a.platform,
    a.install_time,
    case when a.appsflyer_id is null then 0 else 1 end  as is_attributed,
    case
        when a.install_time is not null
             and c.event_time > dateadd(day, 21, a.install_time)
        then 1 else 0
    end                                                 as is_late_event
from clean c
left join attribution a
    on c.user_id = a.appsflyer_id
