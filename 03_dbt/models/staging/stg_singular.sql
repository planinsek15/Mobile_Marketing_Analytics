-- stg_singular — očiščeni dnevni agregati porabe (network-reported).
-- Standardiziramo kanal in geo; zrno ostane date × channel × campaign × country.

select
    cast([date] as date)                    as spend_date,
    {{ standardize_channel('source') }}     as channel,
    campaign,
    upper(country)                          as country_code,
    impressions,
    clicks,
    installs                                as network_installs,
    cast(cost as decimal(14,2))             as cost
from {{ source('raw', 'singular') }}
