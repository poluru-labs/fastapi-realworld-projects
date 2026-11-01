from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_weather_service
from app.schemas.weather import (
    CurrentWeatherRead,
    CurrentWeatherUpdate,
    ForecastDayRead,
    LocationCreate,
    LocationRead,
)
from app.services.weather_service import WeatherService

router = APIRouter()


@router.get(
    "",
    response_model=list[LocationRead],
    summary="List tracked locations",
    description=(
        "Sorted by country then city. Optional search `q` matches city, region, or country code."
    ),
)
def list_locations(
    service: Annotated[WeatherService, Depends(get_weather_service)],
    q: Annotated[str | None, Query(max_length=80)] = None,
) -> list[LocationRead]:
    return service.list_locations(q=q)


@router.post(
    "",
    response_model=LocationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a location",
    description="Creates a location with starter current conditions and a one-day forecast.",
    responses={409: {"description": "City and country pair already exists."}},
)
def create_location(
    payload: LocationCreate,
    service: Annotated[WeatherService, Depends(get_weather_service)],
) -> LocationRead:
    return service.create_location(payload)


@router.get(
    "/{location_id}",
    response_model=LocationRead,
    summary="Get location metadata",
)
def get_location(
    location_id: int,
    service: Annotated[WeatherService, Depends(get_weather_service)],
) -> LocationRead:
    return service.get_location(location_id)


@router.delete(
    "/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Stop tracking a location",
)
def delete_location(
    location_id: int,
    service: Annotated[WeatherService, Depends(get_weather_service)],
) -> None:
    service.delete_location(location_id)


@router.get(
    "/{location_id}/current",
    response_model=CurrentWeatherRead,
    summary="Current conditions",
)
def get_current_weather(
    location_id: int,
    service: Annotated[WeatherService, Depends(get_weather_service)],
) -> CurrentWeatherRead:
    return service.get_current(location_id)


@router.patch(
    "/{location_id}/current",
    response_model=CurrentWeatherRead,
    summary="Refresh current conditions",
    description="Simulate a weather update; `observed_at` is set to now on any change.",
)
def update_current_weather(
    location_id: int,
    payload: CurrentWeatherUpdate,
    service: Annotated[WeatherService, Depends(get_weather_service)],
) -> CurrentWeatherRead:
    return service.update_current(location_id, payload)


@router.get(
    "/{location_id}/forecast",
    response_model=list[ForecastDayRead],
    summary="Multi-day forecast",
)
def get_forecast(
    location_id: int,
    service: Annotated[WeatherService, Depends(get_weather_service)],
) -> list[ForecastDayRead]:
    return service.get_forecast(location_id)
