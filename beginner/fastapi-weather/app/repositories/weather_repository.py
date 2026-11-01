from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from functools import lru_cache


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


@dataclass
class CurrentRecord:
    temp_c: float
    feels_like_c: float
    humidity_pct: int
    wind_kph: float
    condition: str
    observed_at: datetime = field(default_factory=_utcnow)


@dataclass
class ForecastRecord:
    forecast_date: date
    high_c: float
    low_c: float
    condition: str
    precipitation_chance_pct: int


@dataclass
class LocationRecord:
    id: int
    city: str
    country_code: str
    region: str
    current: CurrentRecord
    forecast: list[ForecastRecord]


def _seed() -> dict[int, LocationRecord]:
    return {
        1: LocationRecord(
            id=1,
            city="San Francisco",
            country_code="US",
            region="California",
            current=CurrentRecord(
                temp_c=18.2,
                feels_like_c=17.5,
                humidity_pct=72,
                wind_kph=14.0,
                condition="Partly cloudy",
                observed_at=datetime.fromisoformat("2026-03-10T16:00:00+00:00"),
            ),
            forecast=[
                ForecastRecord(date(2026, 3, 11), 19.0, 12.5, "Sunny", 5),
                ForecastRecord(date(2026, 3, 12), 17.0, 11.0, "Fog", 10),
                ForecastRecord(date(2026, 3, 13), 16.5, 10.5, "Drizzle", 45),
            ],
        ),
        2: LocationRecord(
            id=2,
            city="London",
            country_code="GB",
            region="England",
            current=CurrentRecord(
                temp_c=11.0,
                feels_like_c=9.2,
                humidity_pct=81,
                wind_kph=22.0,
                condition="Overcast",
                observed_at=datetime.fromisoformat("2026-03-10T15:30:00+00:00"),
            ),
            forecast=[
                ForecastRecord(date(2026, 3, 11), 12.0, 6.0, "Light rain", 60),
                ForecastRecord(date(2026, 3, 12), 13.5, 7.5, "Cloudy", 30),
                ForecastRecord(date(2026, 3, 13), 14.0, 8.0, "Showers", 55),
            ],
        ),
        3: LocationRecord(
            id=3,
            city="Tokyo",
            country_code="JP",
            region="Kanto",
            current=CurrentRecord(
                temp_c=22.4,
                feels_like_c=22.0,
                humidity_pct=58,
                wind_kph=8.0,
                condition="Clear",
                observed_at=datetime.fromisoformat("2026-03-11T00:00:00+00:00"),
            ),
            forecast=[
                ForecastRecord(date(2026, 3, 12), 23.0, 15.0, "Clear", 0),
                ForecastRecord(date(2026, 3, 13), 21.0, 14.0, "Cloudy", 20),
                ForecastRecord(date(2026, 3, 14), 19.5, 13.5, "Rain", 70),
            ],
        ),
    }


class WeatherRepository:
    """In-memory weather locations (resets on restart)."""

    def __init__(self) -> None:
        self._locations = _seed()
        self._next_id = max(self._locations.keys(), default=0) + 1

    def list_locations(self) -> list[LocationRecord]:
        return list(self._locations.values())

    def get_location(self, location_id: int) -> LocationRecord | None:
        return self._locations.get(location_id)

    def find_by_city_country(self, city: str, country_code: str) -> LocationRecord | None:
        city_key = city.casefold()
        for record in self._locations.values():
            if record.city.casefold() == city_key and record.country_code == country_code:
                return record
        return None

    def create_location(
        self,
        *,
        city: str,
        country_code: str,
        region: str,
        current: CurrentRecord,
        forecast: list[ForecastRecord],
    ) -> LocationRecord:
        location_id = self._next_id
        self._next_id += 1
        record = LocationRecord(
            id=location_id,
            city=city,
            country_code=country_code,
            region=region,
            current=current,
            forecast=forecast,
        )
        self._locations[location_id] = record
        return record

    def update_current(self, location_id: int, **fields) -> LocationRecord | None:
        record = self._locations.get(location_id)
        if record is None:
            return None
        current = record.current
        for key, value in fields.items():
            if value is not None:
                setattr(current, key, value)
        current.observed_at = _utcnow()
        return record

    def delete_location(self, location_id: int) -> LocationRecord | None:
        return self._locations.pop(location_id, None)


@lru_cache
def get_weather_repository() -> WeatherRepository:
    return WeatherRepository()
