import os
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json

class WeatherService:
    """
    Weather API Service for fetching real-time and historical weather data
    Uses Open-Meteo API (free, no API key required)
    """
    
    def __init__(self):
        self.base_url = "https://api.open-meteo.com/v1"
        self.geocoding_url = "https://geocoding-api.open-meteo.com/v1"
        
    def search_location(self, district: str, state: str) -> Optional[Dict[str, Any]]:
        """Search for location coordinates"""
        try:
            # Use simpler query format for better results
            query = f"{district}"
            response = requests.get(
                f"{self.geocoding_url}/search",
                params={"name": query, "count": 5, "language": "en", "format": "json"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("results"):
                    # Try to find best match for the state
                    for result in data["results"]:
                        if result.get("country_code") == "IN" and result.get("admin1", "").lower() == state.lower():
                            return result
                    # Return first Indian result if exact state match not found
                    for result in data["results"]:
                        if result.get("country_code") == "IN":
                            return result
                    return data["results"][0]
            return None
        except Exception as e:
            print(f"[Weather] Location search error: {e}")
            return None
    
    def get_historical_weather(self, lat: float, lon: float, start_date: str, end_date: str) -> Optional[Dict[str, Any]]:
        """Get historical weather data for a date range using forecast API with past_days"""
        try:
            # Calculate days between start and end
            from datetime import datetime, timedelta
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            days_diff = (end_dt - start_dt).days
            
            # Use forecast API with past_days to get historical data
            response = requests.get(
                f"{self.base_url}/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max,weathercode",
                    "timezone": "Asia/Kolkata",
                    "past_days": min(days_diff + 7, 90)  # Max 90 days in past
                },
                timeout=15
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"[Weather] Historical data error: {e}")
            return None
    
    def get_current_weather(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Get current weather data"""
        try:
            response = requests.get(
                f"{self.base_url}/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,precipitation,weathercode,windspeed_10m",
                    "timezone": "Asia/Kolkata"
                },
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"[Weather] Current weather error: {e}")
            return None
    
    def analyze_disaster_risk(self, district: str, state: str, loss_reason: str, loss_date: str) -> Dict[str, Any]:
        """Analyze if the reported disaster aligns with weather data"""
        result = {
            "weather_verified": False,
            "confidence_score": 0.0,
            "weather_data": None,
            "explanation": "",
            "risk_factors": []
        }
        
        location = self.search_location(district, state)
        if not location:
            result["explanation"] = f"Could not find location data for {district}, {state}"
            return result
        
        lat = location.get("latitude")
        lon = location.get("longitude")
        
        # Parse loss date
        try:
            loss_dt = datetime.strptime(loss_date, "%Y-%m-%d")
        except:
            try:
                loss_dt = datetime.strptime(loss_date, "%d-%m-%Y")
            except:
                result["explanation"] = f"Invalid date format: {loss_date}"
                return result
        
        # Get weather for the loss date and surrounding days
        start_date = (loss_dt - timedelta(days=3)).strftime("%Y-%m-%d")
        end_date = (loss_dt + timedelta(days=3)).strftime("%Y-%m-%d")
        
        weather = self.get_historical_weather(lat, lon, start_date, end_date)
        
        if not weather or "daily" not in weather:
            result["explanation"] = "Could not retrieve weather data for the specified period"
            return result
        
        daily = weather.get("daily", {})
        dates = daily.get("time", [])
        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])
        precipitations = daily.get("precipitation_sum", [])
        wind_speeds = daily.get("windspeed_10m_max", [])
        weather_codes = daily.get("weathercode", [])
        
        # Find the day closest to loss date
        loss_date_str = loss_dt.strftime("%Y-%m-%d")
        closest_idx = 0
        min_diff = float('inf')
        for i, d in enumerate(dates):
            diff = abs((datetime.strptime(d, "%Y-%m-%d") - loss_dt).days)
            if diff < min_diff:
                min_diff = diff
                closest_idx = i
        
        # Analyze based on disaster type
        risk_factors = []
        disaster_confirmed = False
        
        if loss_reason.lower() in ["flood", "floods"]:
            rain = precipitations[closest_idx] if closest_idx < len(precipitations) else 0
            if rain > 50:
                risk_factors.append(f"Heavy rainfall: {rain}mm on/near loss date")
                disaster_confirmed = True
                result["confidence_score"] = min(0.9, 0.5 + (rain / 100))
            elif rain > 20:
                risk_factors.append(f"Moderate rainfall: {rain}mm recorded")
                disaster_confirmed = True
                result["confidence_score"] = 0.6
            else:
                risk_factors.append(f"Low rainfall: {rain}mm - unlikely flood")
                result["confidence_score"] = 0.2
                
        elif loss_reason.lower() in ["drought", "droughts"]:
            rain_total = sum(precipitations) if precipitations else 0
            avg_temp = sum(max_temps) / len(max_temps) if max_temps else 0
            if rain_total < 10 and avg_temp > 35:
                risk_factors.append(f"Very low rainfall: {rain_total}mm over 7 days")
                risk_factors.append(f"High temperature: {avg_temp}°C average")
                disaster_confirmed = True
                result["confidence_score"] = 0.85
            elif rain_total < 25:
                risk_factors.append(f"Low rainfall: {rain_total}mm over 7 days")
                disaster_confirmed = True
                result["confidence_score"] = 0.65
            else:
                risk_factors.append(f"Adequate rainfall: {rain_total}mm")
                result["confidence_score"] = 0.25
                
        elif loss_reason.lower() in ["cyclone", "cyclones", "storm"]:
            wind = wind_speeds[closest_idx] if closest_idx < len(wind_speeds) else 0
            rain = precipitations[closest_idx] if closest_idx < len(precipitations) else 0
            if wind > 50:
                risk_factors.append(f"High wind speed: {wind} km/h")
                disaster_confirmed = True
                result["confidence_score"] = 0.85
            elif wind > 30:
                risk_factors.append(f"Moderate wind speed: {wind} km/h")
                risk_factors.append(f"Rainfall: {rain}mm")
                disaster_confirmed = True
                result["confidence_score"] = 0.6
            else:
                risk_factors.append(f"Normal wind: {wind} km/h - unlikely cyclone")
                result["confidence_score"] = 0.2
                
        elif loss_reason.lower() in ["pest", "pest attack", "disease"]:
            # For pest/disease, check for high humidity (from rain) and temperature
            rain_recent = sum(precipitations[-3:]) if len(precipitations) >= 3 else sum(precipitations)
            avg_temp = sum(max_temps[-3:]) / 3 if len(max_temps) >= 3 else (sum(max_temps) / len(max_temps) if max_temps else 0)
            
            if 25 <= avg_temp <= 35 and rain_recent > 10:
                risk_factors.append(f"High humidity conditions: {rain_recent}mm recent rain")
                risk_factors.append(f"Optimal temperature for pests: {avg_temp}°C")
                disaster_confirmed = True
                result["confidence_score"] = 0.7
            else:
                risk_factors.append(f"Temperature: {avg_temp}°C, Recent rain: {rain_recent}mm")
                result["confidence_score"] = 0.4
        else:
            # Default analysis
            rain = precipitations[closest_idx] if closest_idx < len(precipitations) else 0
            wind = wind_speeds[closest_idx] if closest_idx < len(wind_speeds) else 0
            risk_factors.append(f"Rainfall: {rain}mm, Wind: {wind} km/h")
            result["confidence_score"] = 0.3
        
        result["weather_verified"] = disaster_confirmed
        result["weather_data"] = {
            "location": f"{location.get('name', district)}, {location.get('country', 'India')}",
            "coordinates": {"lat": lat, "lon": lon},
            "loss_date": loss_date_str,
            "weather_on_date": {
                "max_temp": max_temps[closest_idx] if closest_idx < len(max_temps) else None,
                "min_temp": min_temps[closest_idx] if closest_idx < len(min_temps) else None,
                "precipitation": precipitations[closest_idx] if closest_idx < len(precipitations) else None,
                "wind_speed": wind_speeds[closest_idx] if closest_idx < len(wind_speeds) else None,
                "weather_code": weather_codes[closest_idx] if closest_idx < len(weather_codes) else None
            }
        }
        result["risk_factors"] = risk_factors
        result["explanation"] = f"Weather data analysis for {district}, {state} on {loss_date_str}: " + "; ".join(risk_factors)
        
        return result

# Singleton instance
_weather_service = None

def get_weather_service() -> WeatherService:
    global _weather_service
    if _weather_service is None:
        _weather_service = WeatherService()
    return _weather_service
