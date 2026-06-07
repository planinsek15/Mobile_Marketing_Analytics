-- KAKOVOST: conversion_value mora biti med 0 in 63 (6-bitni) ali NULL (crowd anonymity).
-- Vrne vrstice IZVEN razpona → napaka, če jih je kaj.

select
    ad_network_id,
    campaign,
    conversion_value
from {{ ref('stg_skan') }}
where conversion_value is not null
  and (conversion_value < 0 or conversion_value > 63)
