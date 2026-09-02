from datetime import datetime, timezone

from hub.services import weather

# Weather test constants
TEMPERATURE = 22.5
FEELS_LIKE = 23.1
HUMIDITY = 65
WIND_SPEED = 12.3
LOCATION = "New York"
HOURLY_TEMP = 20.0
DAILY_HIGH = 25.0
DAILY_LOW = 18.0


def test_current_weather_model():
    """Test creating a CurrentWeather object."""
    current = weather.CurrentWeather(
        temperature=TEMPERATURE,
        feels_like=FEELS_LIKE,
        condition="Partly Cloudy",
        humidity=HUMIDITY,
        wind_speed=WIND_SPEED,
        location=LOCATION,
    )

    assert current.temperature == TEMPERATURE
    assert current.feels_like == FEELS_LIKE
    assert current.condition == "Partly Cloudy"
    assert current.humidity == HUMIDITY
    assert current.wind_speed == WIND_SPEED
    assert current.location == "New York"

    # Test to_dict method
    weather_dict = current.to_dict()
    assert weather_dict["temperature"] == TEMPERATURE
    assert weather_dict["condition"] == "Partly Cloudy"
    assert weather_dict["location"] == "New York"


def test_hourly_forecast_model():
    """Test creating a HourlyForecast object."""

    hourly = weather.HourlyForecast(time=datetime.now(timezone.utc), temperature=HOURLY_TEMP, condition="Sunny")

    assert hourly.temperature == HOURLY_TEMP
    assert hourly.condition == "Sunny"

    # Test to_dict method
    hourly_dict = hourly.to_dict()
    assert hourly_dict["temperature"] == HOURLY_TEMP
    assert hourly_dict["condition"] == "Sunny"
    assert "time" in hourly_dict


def test_daily_forecast_model():
    """Test creating a DailyForecast object."""

    daily = weather.DailyForecast(date=datetime.now(timezone.utc), high=DAILY_HIGH, low=DAILY_LOW, condition="Cloudy")

    assert daily.high == DAILY_HIGH
    assert daily.low == DAILY_LOW
    assert daily.condition == "Cloudy"

    # Test to_dict method
    daily_dict = daily.to_dict()
    assert daily_dict["high"] == DAILY_HIGH
    assert daily_dict["low"] == DAILY_LOW
    assert daily_dict["condition"] == "Cloudy"
    assert "date" in daily_dict


def test_get_weather_data_empty_config():
    """Test weather data function with empty config."""
    # This would be tested in an integration test with app context
