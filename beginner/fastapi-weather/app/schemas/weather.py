from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class LocationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    city: str = Field(min_length=1, max_length=80)
    country_code: str = Field(min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")
    region: str = Field(default="", max_length=80)


class LocationRead(BaseModel):
    id: int
    city: str
    country_code: str
    region: str
    current_path: str
    forecast_path: str


class CurrentWeatherRead(BaseModel):
    location_id: int
    temp_c: float
    feels_like_c: float
    humidity_pct: int = Field(ge=0, le=100)
    wind_kph: float = Field(ge=0)
    condition: str
    observed_at: datetime


class CurrentWeatherUpdate(BaseModel):
    temp_c: float | None = Field(default=None, ge=-90, le=60)
    feels_like_c: float | None = Field(default=None, ge=-90, le=60)
    humidity_pct: int | None = Field(default=None, ge=0, le=100)
    wind_kph: float | None = Field(default=None, ge=0)
    condition: str | None = Field(default=None, min_length=1, max_length=40)


class ForecastDayRead(BaseModel):
    forecast_date: date
    high_c: float
    low_c: float
    condition: str
    precipitation_chance_pct: int = Field(ge=0, le=100)
