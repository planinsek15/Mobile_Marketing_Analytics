{#
    Privzeto dbt sestavi shemo kot <target.schema>_<custom> (npr. staging_marts).
    Tu jo prepišemo: če je custom shema podana, jo uporabi DOBESEDNO
    (raw / staging / marts), sicer privzeta iz profila. Tako modeli pristanejo
    natanko v shemah medallion arhitekture.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
