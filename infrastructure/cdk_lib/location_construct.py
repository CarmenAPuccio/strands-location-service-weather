"""
Amazon Location Service construct for place search and routing.

This module provides a reusable CDK construct for creating Amazon Location Service
resources including place indexes and route calculators.
"""

from aws_cdk import (
    RemovalPolicy,
)
from aws_cdk import (
    aws_location as location,
)
from constructs import Construct


class LocationServiceConstruct(Construct):
    """Construct for Amazon Location Service resources."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        resource_name_prefix: str = "LocationWeather",
    ) -> None:
        """
        Initialize the LocationServiceConstruct.

        Args:
            scope: CDK scope
            construct_id: Construct ID
            resource_name_prefix: Prefix for Location Service resource names
        """
        super().__init__(scope, construct_id)

        self.resource_name_prefix = resource_name_prefix

        # Create Place Index for location search
        self.place_index = self._create_place_index()

        # Create Route Calculator for routing
        self.route_calculator = self._create_route_calculator()

    def _create_place_index(self) -> location.CfnPlaceIndex:
        """Create Amazon Location Service Place Index."""
        place_index = location.CfnPlaceIndex(
            self,
            "PlaceIndex",
            index_name=f"{self.resource_name_prefix}PlaceIndex",
            data_source="Esri",  # Esri provides comprehensive global coverage
            description="Place index for location search in weather application",
            pricing_plan="RequestBasedUsage",  # Pay per request
        )

        # Apply removal policy for development
        place_index.apply_removal_policy(RemovalPolicy.DESTROY)

        return place_index

    def _create_route_calculator(self) -> location.CfnRouteCalculator:
        """Create Amazon Location Service Route Calculator."""
        route_calculator = location.CfnRouteCalculator(
            self,
            "RouteCalculator",
            calculator_name=f"{self.resource_name_prefix}RouteCalculator",
            data_source="Esri",  # Esri provides comprehensive routing data
            description="Route calculator for directions in weather application",
            pricing_plan="RequestBasedUsage",  # Pay per request
        )

        # Apply removal policy for development
        route_calculator.apply_removal_policy(RemovalPolicy.DESTROY)

        return route_calculator

    def get_place_index_name(self) -> str:
        """Get the place index name for Lambda environment variables."""
        return self.place_index.index_name

    def get_route_calculator_name(self) -> str:
        """Get the route calculator name for Lambda environment variables."""
        return self.route_calculator.calculator_name
