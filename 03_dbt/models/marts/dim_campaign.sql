-- dim_campaign — dimenzija kampanj (kanal × kampanja).
-- Surogatni ključ je kombinacija kanala in kampanje (campaign je unikaten znotraj kanala).

with campaigns as (

    select channel, campaign from {{ ref('stg_appsflyer') }}
    union
    select channel, campaign from {{ ref('stg_singular') }}

)

select
    concat(channel, '|', campaign)  as campaign_key,
    channel,
    campaign,
    case when channel = 'organic' then 0 else 1 end as is_paid
from campaigns
where campaign is not null
