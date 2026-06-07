-- KAKOVOST: po deduplikaciji ne sme ostati noben dvojnik (user_id+event+event_time).
-- Vrne kombinacije, ki se pojavijo večkrat → napaka, če jih je kaj.

select
    user_id,
    event,
    event_time,
    count(*) as cnt
from {{ ref('stg_backend') }}
group by user_id, event, event_time
having count(*) > 1
