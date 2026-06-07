-- fct_installs — dejstvo installov (zrno: ena naprava = en install).
-- Ključi povezujejo na dim_channel / dim_campaign / dim_geo / dim_date.

select
    af.appsflyer_id,
    af.channel                          as channel_key,
    concat(af.channel, '|', af.campaign) as campaign_key,
    af.country_code,
    af.install_date,
    af.platform,
    af.is_paid,
    1                                   as install_count
from {{ ref('stg_appsflyer') }} af
