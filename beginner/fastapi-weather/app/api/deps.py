from typing import Annotated

from fastapi import Depends

from app.repositories.weather_repository import WeatherRepository, get_weather_repository
from app.services.weather_service import WeatherService


def get_weather_service(
    repository: Annotated[WeatherRepository, Depends(get_weather_repository)],
) -> WeatherService:
    return WeatherService(repository)
