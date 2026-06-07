-- stg_skan — SKAdNetwork postbacki (iOS, agregirano, brez user ID-ja).
-- OHRANIMO NULL conversion_value (crowd anonymity) in dodamo razlagalne pasove.
-- Ti podatki se modelirajo LOČENO — joina na ravni uporabnika ni mogoče izvesti.

select
    ad_network_id,
    source_identifier                       as campaign,
    conversion_value,
    case when conversion_value is null then 1 else 0 end   as is_crowd_anonymized,
    case
        when conversion_value is null            then 'unknown'   -- zadržano (k-anonimnost)
        when conversion_value = 0                then 'none'      -- ni post-install dogodka
        when conversion_value between 1 and 15   then 'low'
        when conversion_value between 16 and 39  then 'medium'
        else 'high'
    end                                     as cv_band,
    postback_sequence_index,
    redownload
from {{ source('raw', 'skan') }}
