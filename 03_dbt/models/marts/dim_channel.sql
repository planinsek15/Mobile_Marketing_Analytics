-- dim_channel — dimenzija marketinških kanalov (media_source).
-- Zbere vse kanale iz atribucije in porabe; označi plačane vs organske.

with channels as (

    select channel from {{ ref('stg_appsflyer') }}
    union
    select channel from {{ ref('stg_singular') }}

)

select
    channel                                                 as channel_key,
    channel,
    case when channel = 'organic' then 0 else 1 end         as is_paid,
    case
        when channel = 'organic'                then 'Organic'
        when channel = 'Apple Search Ads'       then 'Search'
        when channel = 'Google Ads'             then 'Search/Display'
        when channel in ('Meta', 'TikTok')      then 'Social'
        else 'Other'
    end                                                     as channel_type
from channels
where channel is not null
