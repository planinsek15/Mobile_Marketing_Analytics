-- dim_date — koledarska dimenzija, zgrajena iz dejanskega razpona aktivnosti.
-- SQL Server 2019 nima GENERATE_SERIES, zato datumsko os ustvarimo iz tally
-- tabele (sys.all_objects) — brez prepovedanih funkcij in brez rekurzije.

with bounds as (

    select
        cast(min(d) as date) as min_d,
        cast(max(d) as date) as max_d
    from (
        select install_time      as d from {{ ref('stg_appsflyer') }}
        union all select event_time from {{ ref('stg_appsflyer_events') }}
        union all select event_time from {{ ref('stg_backend') }}
        union all select cast(spend_date as datetime2) from {{ ref('stg_singular') }}
    ) all_dates

),

tally as (

    select row_number() over (order by (select null)) - 1 as num
    from sys.all_objects

),

spine as (

    select dateadd(day, t.num, b.min_d) as date_day
    from tally t
    cross join bounds b
    where t.num <= datediff(day, b.min_d, b.max_d)

)

select
    date_day,
    year(date_day)                              as year,
    datepart(quarter, date_day)                 as quarter,
    month(date_day)                             as month,
    datename(month, date_day)                   as month_name,
    day(date_day)                               as day_of_month,
    datepart(weekday, date_day)                 as day_of_week,
    datename(weekday, date_day)                 as day_name,
    datepart(week, date_day)                    as week_of_year,
    case when datepart(weekday, date_day) in (1, 7) then 1 else 0 end as is_weekend
from spine
