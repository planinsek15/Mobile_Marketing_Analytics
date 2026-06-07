-- stg_appsflyer — očiščeni AppsFlyer INSTALL zapisi (en na napravo).
-- Standardiziramo media_source v kanonični kanal in normaliziramo geo/platformo.
-- Ta model služi kot atribucijski "imenik naprav" za obogatitev backenda.

with src as (

    select *
    from {{ source('raw', 'appsflyer') }}
    where event_name = 'install'

)

select
    appsflyer_id,
    {{ standardize_channel('media_source') }}            as channel,
    campaign,
    af_adset,
    af_ad,
    cast(install_time as datetime2(0))                   as install_time,
    cast(install_time as date)                           as install_date,
    attributed_touch_time,
    attributed_touch_type,
    upper(country_code)                                  as country_code,
    lower(platform)                                      as platform,
    case when {{ standardize_channel('media_source') }} = 'organic'
         then 0 else 1 end                               as is_paid
from src
