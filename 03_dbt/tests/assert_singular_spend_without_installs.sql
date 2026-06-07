-- KAKOVOST (opozorilo): poraba > 0 ob 0 installih — sumljiva učinkovitost kampanje.
-- severity = warn, ker je v simuliranih podatkih to legitimen (a opozorilu vreden) pojav.
{{ config(severity='warn') }}

select
    spend_date,
    channel,
    campaign,
    country_code,
    cost,
    network_installs
from {{ ref('stg_singular') }}
where cost > 0
  and network_installs = 0
