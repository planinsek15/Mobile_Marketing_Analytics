-- KAKOVOST (opozorilo): installi > 0 ob 0 porabi — manjkajoč strošek / napaka poročanja.
-- severity = warn: zaželeno je opozoriti, a ne ustaviti pipeline-a.
{{ config(severity='warn') }}

select
    spend_date,
    channel,
    campaign,
    country_code,
    cost,
    network_installs
from {{ ref('stg_singular') }}
where network_installs > 0
  and (cost is null or cost <= 0)
