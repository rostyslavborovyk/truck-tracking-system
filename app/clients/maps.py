from __future__ import annotations

import typing

import polyline  # type: ignore[import-untyped]
import requests  # type: ignore[import-untyped]
from pydantic import BaseModel

from app.config import MAPS_API_TOKEN


class LocationPoint(BaseModel):
    lat: float
    lon: float


class RouteResponse(BaseModel):
    origin_address: str | None = None
    origin_location: LocationPoint | None = None
    destination_address: str | None = None
    destination_location: LocationPoint | None = None
    location_points: list[LocationPoint]
    expected_duration_in_seconds: int


# Polyline decoder
# https://developers.google.com/maps/documentation/utilities/polylineutility
class MapsClient(BaseModel):
    def get_route(
        self,
        *,
        origin_address: str | None = None,
        destination_address: str | None = None,
        origin_location: LocationPoint | None = None,
        destination_location: LocationPoint | None = None,
    ) -> RouteResponse:
        if not origin_address and not origin_location:
            raise Exception("Origin address or origin location must be specified!")

        if not destination_address and not destination_location:
            raise Exception(
                "Destination address or destination location must be specified!"
            )

        origin: dict[str, typing.Any] = {}
        if origin_address:
            origin.update({"address": origin_address})
        elif origin_location:
            origin.update(
                {
                    "location": {
                        "latLng": {
                            "latitude": origin_location.lat,
                            "longitude": origin_location.lon,
                        }
                    }
                }
            )

        destination: dict[str, typing.Any] = {}
        if destination_address:
            destination.update({"address": destination_address})
        elif destination_location:
            destination.update(
                {
                    "location": {
                        "latLng": {
                            "latitude": destination_location.lat,
                            "longitude": destination_location.lon,
                        }
                    }
                }
            )

        data = {
            "origin": origin,
            "destination": destination,
            "travelMode": "DRIVE",
            "routingPreference": "TRAFFIC_AWARE",
            "departureTime": "2023-11-15T15:01:23.045123456Z",
            "computeAlternativeRoutes": False,
            "routeModifiers": {
                "avoidTolls": False,
                "avoidHighways": False,
                "avoidFerries": False,
            },
            "languageCode": "en-US",
            "units": "METRIC",
        }

        response = requests.post(
            "https://routes.googleapis.com/directions/v2:computeRoutes",
            json=data,
            headers=self._get_default_headers(),
        )
        data = response.json()
        encoded_polyline = data["routes"][0]["polyline"]["encodedPolyline"]  # type: ignore[index]
        data_points = polyline.decode(encoded_polyline)
        expected_duration_in_seconds = int(data["routes"][0]["duration"][:-1])  # type: ignore[index]
        return RouteResponse(
            origin_address=origin_address,
            origin_location=origin_location,
            destination_address=destination_address,
            destination_location=destination_location,
            location_points=[LocationPoint(lat=dp[0], lon=dp[1]) for dp in data_points],
            expected_duration_in_seconds=expected_duration_in_seconds,
        )

    def get_location(self, address) -> LocationPoint:
        params = self._get_default_params()
        params.update({"address": address})

        response = requests.post(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params=params,
            headers=self._get_default_headers(),
        )
        data = response.json()
        location = data["results"][0]["geometry"]["location"]

        return LocationPoint(lat=location["lat"], lon=location["lng"])

    def _get_default_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": MAPS_API_TOKEN,
            "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline",
        }

    def _get_default_params(self) -> dict[str, str]:
        return {
            "key": MAPS_API_TOKEN,
        }


if __name__ == "__main__":
    # route = MapsClient().get_route("Vilnius, Lithuania", "Klaipeda, Lithuania")
    loc = MapsClient().get_location("Vilnius, Lithuania")
