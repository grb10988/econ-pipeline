with staged as (
    select *
    from {{ ref('stg_fred_observations') }}
)

select
    series_id
    , observation_date
    , value
    , lag(value) over (
        partition by series_id
        order by observation_date
    ) as prior_value
    , value - lag(value) over (
        partition by series_id
        order by observation_date
    ) as period_change
    , avg(value) over (
        partition by series_id
        order by observation_date
        rows between 2 preceding and current row
    ) as rolling_3_period_avg
from staged
order by series_id, observation_date