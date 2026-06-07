-- rec_attribution_gap — backend dogodki BREZ AppsFlyer atribucije.
--
-- ~10 % backend dogodkov pripada uporabnikom, ki jih MMP sploh ne pozna
-- (organski/ITP/ATT-opt-out, ali server-to-server dogodki brez device matcha).
-- Ti prihodki obstajajo v viru resnice, a jih noben kanal ne more prevzeti —
-- to je "attribution gap", ki popači ROAS, če ga ignoriramo.

with backend as (

    select *
    from {{ ref('stg_backend') }}
    where is_attributed = 0

)

select
    event_date,
    event,
    count(*)                                as unattributed_events,
    cast(sum(revenue) as decimal(14,2))     as unattributed_revenue,
    sum(case when is_late_event = 1 then 1 else 0 end) as late_among_unattributed
from backend
group by event_date, event
