{#
    Standardizacija imena kanala (media_source) na kanonično obliko.
    V realnih MMP podatkih isti kanal prihaja v različnih zapisih
    (facebook / Facebook Ads / fb → Meta). Tu jih poenotimo.
#}
{% macro standardize_channel(col) -%}
    case
        when lower(trim({{ col }})) in ('meta', 'facebook', 'facebook ads', 'fb', 'instagram')
            then 'Meta'
        when lower(trim({{ col }})) in ('google ads', 'googleadwords', 'google', 'adwords', 'uac')
            then 'Google Ads'
        when lower(trim({{ col }})) in ('tiktok', 'tiktok ads', 'bytedance')
            then 'TikTok'
        when lower(trim({{ col }})) in ('apple search ads', 'asa', 'apple')
            then 'Apple Search Ads'
        when lower(trim({{ col }})) in ('organic', '', 'none') or {{ col }} is null
            then 'organic'
        else {{ col }}
    end
{%- endmacro %}
