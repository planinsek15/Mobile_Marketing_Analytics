-- fct_spend — dejstvo porabe (zrno: dan × kanal × kampanja × država, kot v Singular).

select
    s.spend_date,
    s.channel                           as channel_key,
    concat(s.channel, '|', s.campaign)  as campaign_key,
    s.country_code,
    s.impressions,
    s.clicks,
    s.network_installs,
    s.cost
from {{ ref('stg_singular') }} s
