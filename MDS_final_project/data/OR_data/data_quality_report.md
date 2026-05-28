# Data Quality Report

Generated in `OR資料` using UTF-8 with BOM (`utf-8-sig`). Original raw CSV files were not overwritten.

## Current Model Stage
At the current stage, we are preparing static reference data for the OR model. Actual user-selected attractions, stay time, start time, end time, trip date, budget, and preference weights will be provided later by the frontend or API request when the web application is integrated.

Development-stage request simulation files and model-run node inputs are no longer part of the current output layer. This report does not treat them as required outputs.

## Attraction Catalog Update
- `attractions.csv` was regenerated from `景點資料（含對車站的壅擠壓力）/tokyo_tourism_poi_pressure_candidates_500_1000_clean.csv`.
- New `attractions.csv` rows: 801.
- New `attraction_station_access.csv` rows: 801.
- The previous 68-row representative attraction source was not used as the main attraction database for this update.
- No raw CSV files were modified.

## Required Column Mapping
- `attraction_id` <- `poi_id`
- `attraction_name` <- `attraction_name_en`
- `nearest_station_id` <- `nearest_station_code`
- `nearest_station_name` <- `nearest_station_name`
- `distance_to_station_m` <- `distance_to_station_m`
- `pressure_score` <- `tourism_pressure_index`

## Preserved Optional Column Mapping
- `lat` <- `latitude`
- `lon` <- `longitude`
- `category` <- `category`
- `type` <- `attraction_type with google_types fallback`
- `popularity_score` <- `google_popularity_score`
- `rating` <- `google_rating`
- `review_count` <- `google_user_rating_count`
- `source_name` <- `poi_source`
- `original_name` <- `attraction_name_ja`

## Missing Columns Filled With NA
- No required attraction columns were missing from the mapped output schema.
- Required attraction fields contain 0 `NA` rows after mapping.
- Optional preserved field NA counts: rating: 53 NA rows; review_count: 53 NA rows.
- `attraction_station_access.csv` contains 0 `NA` rows in its required fields.

## Access Walk Time
- `access_walk_time_min = distance_to_station_m / 60`.
- Walking speed is assumed to be 1 meter per second, so 60 meters equals 1 minute.
- `distance_to_station_m` missing rows: 0.

## Pressure Score Explanation
- `pressure_score` was directly mapped from `tourism_pressure_index`; it was not recomputed in this output step.
- `pressure_score` is a relative proxy for how much a POI may contribute to crowd pressure around its nearest station. It is not an actual visitor count and is not passenger count data.
- The raw file contains related fields such as `visitor_count_score`, `google_popularity_score`, `google_rating`, `google_user_rating_count`, `official_recognition_score`, `attraction_scale_score`, `metro_access_score`, `opening_availability_score`, `mapping_confidence_score`, `penalty_score`, `attraction_score`, `distance_to_station_m`, and `scoring_note`.
- Because the exact authoritative original formula is not separately documented in the file metadata, this update preserves the existing POI pressure candidate score instead of inventing or recalculating a formula.
- No fake `visitor_count` field was created.

## Unchanged Reference Files
- `station_edges_by_time.csv`: unchanged by this attraction-only update; 131200 rows currently present.
- `station_info.csv`: unchanged by this attraction-only update; 186 rows currently present.
- `station_crowd_by_time.csv`: unchanged by this attraction-only update; 5082 rows currently present.
- `train_frequency_by_time.csv`: unchanged by this attraction-only update; 28421 rows currently present.
- `weather_daily.csv`: unchanged by this attraction-only update; 731 rows currently present.
- `daily_weight_adjustment.csv`: unchanged by this attraction-only update; 731 rows currently present.

## Weather Scope
- No `weather_penalty_by_time.csv` or `or_input_weather.csv` was created, because the available weather data is daily-level, not hourly.

## Crowd Data Scope
- Station crowd values are only a crowd risk proxy based on official heatmap scores from 1 to 6 and normalized scores from 0 to 1. They are not actual passenger counts or actual hourly passenger counts.
