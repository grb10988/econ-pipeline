select
    series_id
    , observation_date
    , value
    , fetched_at
from {{ source('fred_raw', 'raw_fred_observations') }}