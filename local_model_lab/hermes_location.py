# -*- coding: utf-8 -*-
"""
Hermes Always-On Geolocation & Environmental Context Engine
Tracks real-time user location across connected companion devices (Smartphone, Smartwatch, Laptop)
with zero battery waste, semantic geofencing (Home Cockpit, Work, In Transit), reverse geocoding,
and live hyper-local weather intelligence.
"""

from __future__ import annotations

import json
import logging
import math
import os
import threading
import time
import urllib.parse
import urllib.request
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("hermes.location")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_LOGS_DIR = _PROJECT_ROOT / "logs"
_LOGS_DIR.mkdir(parents=True, exist_ok=True)
_LOCATION_FILE = _LOGS_DIR / "hermes_location.json"
_HOME_FILE = _LOGS_DIR / "hermes_home_location.json"

# WMO Weather interpretation codes (WW)
WMO_CODES: Dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two GPS coordinates in meters."""
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


@dataclass
class LocationTelemetry:
    latitude: float
    longitude: float
    accuracy: float = 0.0
    altitude: Optional[float] = None
    speed: Optional[float] = None
    heading: Optional[float] = None
    source_device: str = "unknown"
    source_type: str = "smartphone"  # smartphone, smartwatch, laptop, desktop
    timestamp: float = field(default_factory=time.time)
    address: Dict[str, Any] = field(default_factory=dict)
    display_name: str = ""
    zone: str = "Unknown"
    distance_to_home_meters: Optional[float] = None
    weather: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class HermesLocationEngine:
    """
    Central Coordinator for User Presence & Geolocation Telemetry.
    Integrates reverse geocoding, geofencing, breadcrumbs history, and weather.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.current: Optional[LocationTelemetry] = None
        self.history: deque = deque(maxlen=60)
        self.home_coords: Optional[Dict[str, float]] = None
        self._geocode_cache: Dict[str, Dict[str, Any]] = {}
        self._weather_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._last_nominatim_call: float = 0.0

        self._load_state()

    def _load_state(self) -> None:
        """Loads cached location and home coordinates from disk."""
        try:
            if _HOME_FILE.exists():
                with open(_HOME_FILE, "r", encoding="utf-8") as f:
                    self.home_coords = json.load(f)
                    logger.info(f"Loaded home location coordinates: {self.home_coords}")
        except Exception as e:
            logger.warning(f"Error loading home location: {e}")

        try:
            if _LOCATION_FILE.exists():
                with open(_LOCATION_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data and "latitude" in data and "longitude" in data:
                        self.current = LocationTelemetry(
                            latitude=float(data["latitude"]),
                            longitude=float(data["longitude"]),
                            accuracy=float(data.get("accuracy", 0.0)),
                            altitude=data.get("altitude"),
                            speed=data.get("speed"),
                            heading=data.get("heading"),
                            source_device=str(data.get("source_device", "cached")),
                            source_type=str(data.get("source_type", "smartphone")),
                            timestamp=float(data.get("timestamp", time.time())),
                            address=data.get("address", {}),
                            display_name=str(data.get("display_name", "")),
                            zone=str(data.get("zone", "Home Cockpit")),
                            distance_to_home_meters=data.get("distance_to_home_meters"),
                            weather=data.get("weather", {}),
                        )
        except Exception as e:
            logger.warning(f"Error loading cached location: {e}")

    def _save_state(self) -> None:
        """Persists current location snapshot to disk."""
        if not self.current:
            return
        try:
            with open(_LOCATION_FILE, "w", encoding="utf-8") as f:
                json.dump(self.current.to_dict(), f, indent=2)
        except Exception as e:
            logger.warning(f"Error saving location snapshot: {e}")

    def set_home(self, latitude: Optional[float] = None, longitude: Optional[float] = None) -> Dict[str, Any]:
        """Sets or locks current location as the user's primary 'Home Cockpit'."""
        with self._lock:
            lat = latitude if latitude is not None else (self.current.latitude if self.current else None)
            lon = longitude if longitude is not None else (self.current.longitude if self.current else None)

            if lat is None or lon is None:
                return {"status": "error", "message": "No coordinates available to set as home."}

            self.home_coords = {
                "latitude": round(lat, 6),
                "longitude": round(lon, 6),
                "set_at": time.time(),
            }
            try:
                with open(_HOME_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.home_coords, f, indent=2)
            except Exception as e:
                logger.error(f"Failed to persist home coords: {e}")

            if self.current:
                self.current.distance_to_home_meters = 0.0
                self.current.zone = "Home Cockpit"
                self._save_state()

            return {
                "status": "success",
                "message": "Home coordinates locked successfully.",
                "home": self.home_coords,
            }

    def _reverse_geocode_sync(self, lat: float, lon: float) -> Tuple[Dict[str, Any], str]:
        """
        Queries Nominatim with caching and 1 req/sec rate limiting.
        Rounds to ~100m to maximize cache hits.
        """
        cache_key = f"{round(lat, 3)},{round(lon, 3)}"
        if cache_key in self._geocode_cache:
            cached = self._geocode_cache[cache_key]
            return cached.get("address", {}), cached.get("display_name", "")

        now = time.time()
        elapsed = now - self._last_nominatim_call
        if elapsed < 1.1:
            time.sleep(1.1 - elapsed)

        self._last_nominatim_call = time.time()
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&addressdetails=1"
        headers = {"User-Agent": "Hermes-OmniMesh-LocationEngine/2.0"}

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                addr = data.get("address", {})
                display = data.get("display_name", "")

                # Format friendly compact display name
                city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("suburb") or addr.get("county") or ""
                state = addr.get("state") or addr.get("region") or ""
                country = addr.get("country") or ""
                neighborhood = addr.get("neighbourhood") or addr.get("suburb") or addr.get("road") or ""

                parts = [p for p in [neighborhood, city, state, country] if p]
                compact_display = ", ".join(parts) if parts else display

                self._geocode_cache[cache_key] = {"address": addr, "display_name": compact_display}
                return addr, compact_display
        except Exception as e:
            logger.debug(f"Reverse geocode lookup error: {e}")
            return {}, f"{round(lat, 4)}, {round(lon, 4)}"

    def _fetch_weather_sync(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Queries Open-Meteo for hyper-local current weather.
        Cached for 15 minutes per location.
        """
        cache_key = f"{round(lat, 2)},{round(lon, 2)}"
        now = time.time()
        if cache_key in self._weather_cache:
            ts, cached_data = self._weather_cache[cache_key]
            if now - ts < 900:  # 15 minutes
                return cached_data

        url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            "&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m"
            "&timezone=auto"
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Hermes-LocationEngine/2.0"})
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
                cur = raw.get("current", {})
                code = cur.get("weather_code", 0)
                desc = WMO_CODES.get(code, "Clear")
                celsius = cur.get("temperature_2m", 20.0)
                fahrenheit = round((celsius * 9.0 / 5.0) + 32.0, 1)

                weather_info = {
                    "temperature_c": celsius,
                    "temperature_f": fahrenheit,
                    "condition": desc,
                    "apparent_temperature_c": cur.get("apparent_temperature"),
                    "apparent_temperature_f": round((cur.get("apparent_temperature", 20) * 9.0 / 5.0) + 32.0, 1) if cur.get("apparent_temperature") is not None else None,
                    "humidity": cur.get("relative_humidity_2m"),
                    "wind_speed_kmh": cur.get("wind_speed_10m"),
                    "precipitation_mm": cur.get("precipitation"),
                    "updated_at": now,
                }
                self._weather_cache[cache_key] = (now, weather_info)
                return weather_info
        except Exception as e:
            logger.debug(f"Weather lookup error: {e}")
            return {}

    def update_location(
        self,
        latitude: float,
        longitude: float,
        accuracy: float = 0.0,
        altitude: Optional[float] = None,
        speed: Optional[float] = None,
        heading: Optional[float] = None,
        source_device: str = "smartphone",
        source_type: str = "smartphone",
    ) -> Dict[str, Any]:
        """
        Ingests a new location telemetry point from phone, watch, or laptop.
        Evaluates distance to home, determines zone, resolves address and weather.
        """
        with self._lock:
            # 1. Distance to Home
            dist_home: Optional[float] = None
            zone = "Outdoors"

            if self.home_coords and "latitude" in self.home_coords and "longitude" in self.home_coords:
                dist_home = haversine_distance_meters(
                    latitude, longitude,
                    self.home_coords["latitude"], self.home_coords["longitude"]
                )
                if dist_home <= 150.0:
                    zone = "Home Cockpit"
                elif speed is not None and speed >= 4.5:  # > 16 km/h
                    zone = "In Transit (Traveling)"
                else:
                    zone = "Away (Public / Work)"
            else:
                # If no home is set, automatically establish the first received location as Home!
                self.home_coords = {
                    "latitude": round(latitude, 6),
                    "longitude": round(longitude, 6),
                    "set_at": time.time(),
                    "auto_initialized": True,
                }
                try:
                    with open(_HOME_FILE, "w", encoding="utf-8") as f:
                        json.dump(self.home_coords, f, indent=2)
                except Exception:
                    pass
                dist_home = 0.0
                zone = "Home Cockpit"

            # 2. Reverse Geocode in background / quick sync
            addr, display_name = self._reverse_geocode_sync(latitude, longitude)

            # 3. Weather
            weather = self._fetch_weather_sync(latitude, longitude)

            point = LocationTelemetry(
                latitude=latitude,
                longitude=longitude,
                accuracy=accuracy,
                altitude=altitude,
                speed=speed,
                heading=heading,
                source_device=source_device,
                source_type=source_type,
                timestamp=time.time(),
                address=addr,
                display_name=display_name,
                zone=zone,
                distance_to_home_meters=round(dist_home, 1) if dist_home is not None else None,
                weather=weather,
            )

            self.current = point
            self.history.append(point.to_dict())
            self._save_state()

            logger.info(
                f"Location updated: {display_name} ({zone}, {dist_home}m from Home) via {source_type}"
            )
            return point.to_dict()

    def get_current(self) -> Dict[str, Any]:
        """Returns the current location state dictionary or fallback defaults."""
        with self._lock:
            if not self.current:
                return {
                    "status": "idle",
                    "latitude": None,
                    "longitude": None,
                    "display_name": "Location pending companion connection",
                    "zone": "Home Cockpit",
                    "is_home": True,
                    "distance_to_home_meters": 0.0,
                    "weather": {},
                    "source_type": "none",
                    "last_updated": 0,
                    "home_coords": self.home_coords,
                }

            d = self.current.to_dict()
            d["status"] = "active"
            d["is_home"] = (self.current.zone == "Home Cockpit")
            d["home_coords"] = self.home_coords
            d["age_seconds"] = round(time.time() - self.current.timestamp, 1)
            return d

    def get_history(self) -> List[Dict[str, Any]]:
        """Returns recent location trail."""
        with self._lock:
            return list(self.history)

    def is_user_home(self) -> bool:
        """Fast boolean check: Is the user currently at their Home Cockpit?"""
        with self._lock:
            if not self.current:
                return True  # Host PC assumption
            return self.current.zone == "Home Cockpit"

    def get_environmental_context_prompt(self) -> str:
        """
        Produces clean contextual snippet to inject into Agent Prompts
        so Hermes always knows where the user is and what their environment is like.
        """
        cur = self.get_current()
        if cur.get("status") != "active" or not cur.get("latitude"):
            return "User Location: Home Cockpit (Primary LAN). Weather: Standard indoor."

        loc_str = cur.get("display_name") or f"{cur.get('latitude')}, {cur.get('longitude')}"
        zone = cur.get("zone", "Home")
        dist = cur.get("distance_to_home_meters")
        dist_str = f"({dist:.0f}m from Home)" if dist is not None and zone != "Home Cockpit" else "(At Home)"

        weather = cur.get("weather", {})
        weather_str = ""
        if weather:
            cond = weather.get("condition", "")
            temp_f = weather.get("temperature_f", "")
            temp_c = weather.get("temperature_c", "")
            weather_str = f" • Current Weather: {cond}, {temp_f}°F ({temp_c}°C)"

        source = cur.get("source_type", "mobile")
        return f"User Location: {zone} {dist_str} • {loc_str}{weather_str} [GPS Telemetry from {source}]"


# Global Singleton Engine Instance
_engine_instance: Optional[HermesLocationEngine] = None


def get_location_engine() -> HermesLocationEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = HermesLocationEngine()
    return _engine_instance
