-- stg_appsflyer_events — očiščeni AppsFlyer in-app REVENUE dogodki.
-- MMP poročani prihodek po napravi/kanalu; osnova za reconciliation proti backendu.

with src as (

    select *
    from {{ source('raw', 'appsflyer') }}
    where event_name in ('af_purchase', 'af_subscribe')
      and event_revenue is not null

)

select
    appsflyer_id,
    {{ standardize_channel('media_source') }}   as channel,
    campaign,
    event_name,
    cast(event_revenue as decimal(12,2))        as event_revenue,
    cast(event_time as datetime2(0))            as event_time,
    cast(event_time as date)                    as event_date,
    cast(install_time as date)                  as install_date,
    upper(country_code)                         as country_code,
    lower(platform)                             as platform
from src
