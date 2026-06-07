-- dim_geo — geografska dimenzija (države iz atribucije in porabe).

with geos as (

    select country_code from {{ ref('stg_appsflyer') }}
    union
    select country_code from {{ ref('stg_singular') }}

)

select
    country_code,
    case country_code
        when 'SI' then 'Slovenija'
        when 'DE' then 'Nemčija'
        when 'AT' then 'Avstrija'
        when 'HR' then 'Hrvaška'
        when 'IT' then 'Italija'
        else country_code
    end                 as country_name,
    'EU'                as region
from geos
where country_code is not null
