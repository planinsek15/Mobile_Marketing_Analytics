-- KAKOVOST: retention mora biti monotono padajoč (D1 >= D7 >= D30).
-- Vrne kohorte, ki kršijo monotonost → napaka, če jih je kaj.

select
    channel,
    install_date,
    retained_d1,
    retained_d7,
    retained_d30
from {{ ref('mart_retention') }}
where retained_d1 < retained_d7
   or retained_d7 < retained_d30
