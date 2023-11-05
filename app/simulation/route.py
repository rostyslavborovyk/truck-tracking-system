from __future__ import annotations

from pydantic import BaseModel

from app.clients.maps import LocationPoint, MapsClient
from app.simulation.truck import Truck


class Route(BaseModel):
    origin_address: str | None = None
    origin_location: LocationPoint | None = None
    destination_address: str | None = None
    destination_location: LocationPoint | None = None
    location_points: list[LocationPoint]
    expected_duration_in_seconds: int

    @staticmethod
    def combine_routes(r1: Route, r2: Route) -> Route:
        return Route(
            origin_address=r1.origin_address,
            origin_location=r1.origin_location,
            destination_address=r2.destination_address,
            destination_location=r2.destination_location,
            location_points=[*r1.location_points, *r2.location_points],
            expected_duration_in_seconds=r1.expected_duration_in_seconds
            + r2.expected_duration_in_seconds,
        )

    @classmethod
    def from_origin_and_destination(
        cls,
        *,
        maps_client: MapsClient,
        origin_address: str | None = None,
        destination_address: str | None = None,
        origin_location: LocationPoint | None = None,
        destination_location: LocationPoint | None = None,
    ) -> Route:
        route_response = maps_client.get_route(
            origin_address=origin_address,
            destination_address=destination_address,
            origin_location=origin_location,
            destination_location=destination_location,
        )
        return cls(**route_response.model_dump())

    @classmethod
    def from_truck_location_origin_and_destination(
        cls,
        maps_client: MapsClient,
        truck: Truck,
        origin_address: str,
        destination_address: str,
    ) -> Route:
        truck_to_origin_route = cls.from_origin_and_destination(
            maps_client=maps_client,
            origin_location=truck.location,
            destination_address=origin_address,
        )

        origin_to_destination_route = cls.from_origin_and_destination(
            maps_client=maps_client,
            origin_address=origin_address,
            destination_address=destination_address,
        )

        return Route.combine_routes(truck_to_origin_route, origin_to_destination_route)
