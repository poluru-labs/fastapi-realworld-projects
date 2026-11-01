from app.core.exceptions import ConflictError, NotFoundError
from app.repositories.weather_repository import (
    CurrentRecord,
    ForecastRecord,
    WeatherRepository,
)
from app.schemas.weather import (
    CurrentWeatherRead,
    CurrentWeatherUpdate,
    ForecastDayRead,
    LocationCreate,
    LocationRead,
)


class WeatherService:
    def __init__(self, repository: WeatherRepository) -> None:
        self._repo = repository

    def list_locations(self, *, q: str | None) -> list[LocationRead]:
        rows = self._repo.list_locations()
        if q:
            needle = q.casefold()
            rows = [
                row
                for row in rows
                if needle in row.city.casefold()
                or needle in row.region.casefold()
                or needle in row.country_code.casefold()
            ]
        rows.sort(key=lambda row: (row.country_code, row.city))
        return [self._location_read(row) for row in rows]

    def get_location(self, location_id: int) -> LocationRead:
        return self._location_read(self._require_location(location_id))

    def create_location(self, payload: LocationCreate) -> LocationRead:
        if self._repo.find_by_city_country(payload.city, payload.country_code):
            raise ConflictError(
                f"Weather for {payload.city}, {payload.country_code} is already tracked"
            )
        default_current = CurrentRecord(
            temp_c=20.0,
            feels_like_c=20.0,
            humidity_pct=50,
            wind_kph=10.0,
            condition="Fair",
        )
        default_forecast = [
            ForecastRecord(
                forecast_date=default_current.observed_at.date(),
                high_c=21.0,
                low_c=14.0,
                condition="Fair",
                precipitation_chance_pct=15,
            )
        ]
        record = self._repo.create_location(
            city=payload.city,
            country_code=payload.country_code,
            region=payload.region,
            current=default_current,
            forecast=default_forecast,
        )
        return self._location_read(record)

    def delete_location(self, location_id: int) -> None:
        if self._repo.delete_location(location_id) is None:
            raise NotFoundError("Location", location_id)

    def get_current(self, location_id: int) -> CurrentWeatherRead:
        record = self._require_location(location_id)
        return self._current_read(record)

    def update_current(self, location_id: int, payload: CurrentWeatherUpdate) -> CurrentWeatherRead:
        fields = payload.model_dump(exclude_unset=True)
        if not fields:
            return self.get_current(location_id)
        record = self._repo.update_current(location_id, **fields)
        if record is None:
            raise NotFoundError("Location", location_id)
        return self._current_read(record)

    def get_forecast(self, location_id: int) -> list[ForecastDayRead]:
        record = self._require_location(location_id)
        return [self._forecast_read(day) for day in record.forecast]

    def _require_location(self, location_id: int):
        record = self._repo.get_location(location_id)
        if record is None:
            raise NotFoundError("Location", location_id)
        return record

    @staticmethod
    def _location_read(record) -> LocationRead:
        return LocationRead(
            id=record.id,
            city=record.city,
            country_code=record.country_code,
            region=record.region,
            current_path=f"/api/v1/locations/{record.id}/current",
            forecast_path=f"/api/v1/locations/{record.id}/forecast",
        )

    @staticmethod
    def _current_read(record) -> CurrentWeatherRead:
        current = record.current
        return CurrentWeatherRead(
            location_id=record.id,
            temp_c=current.temp_c,
            feels_like_c=current.feels_like_c,
            humidity_pct=current.humidity_pct,
            wind_kph=current.wind_kph,
            condition=current.condition,
            observed_at=current.observed_at,
        )

    @staticmethod
    def _forecast_read(day: ForecastRecord) -> ForecastDayRead:
        return ForecastDayRead(
            forecast_date=day.forecast_date,
            high_c=day.high_c,
            low_c=day.low_c,
            condition=day.condition,
            precipitation_chance_pct=day.precipitation_chance_pct,
        )
