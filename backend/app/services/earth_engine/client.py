"""Google Earth Engine integration.

This module is a placeholder for the future integration with the existing
Ramsar Wetlands Water Quality Monitoring Earth Engine application
(https://ee-ramsarwetlands5.projects.earthengine.app/view/ramsarwetlands).

No Earth Engine API calls are implemented yet. The EARTH_ENGINE_PROJECT
environment variable is reserved for the future service account / project
configuration.
"""

from app.core.config import settings


class EarthEngineClient:
    def __init__(self) -> None:
        self.project = settings.EARTH_ENGINE_PROJECT

    def is_configured(self) -> bool:
        return bool(self.project)
