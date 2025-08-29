import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


# default is no-op
def geo_by_addr(ip: str) -> dict[str, Any] | None:
    return None


def _init_geoip() -> None:
    global geo_by_addr  # noqa: PLW0603

    import maxminddb

    assert settings.GEOIP_PATH_MMDB is not None  # checked below

    try:
        geo_db = maxminddb.open_database(settings.GEOIP_PATH_MMDB, maxminddb.MODE_AUTO)
    except Exception:
        logger.exception("Error opening GeoIP database: %s", settings.GEOIP_PATH_MMDB)
        return

    def _geo_by_addr(ip: str) -> dict[str, Any] | None:
        rv = geo_db.get(ip)
        if not rv:
            return None

        assert isinstance(rv, dict)
        geo: dict[str, Any] = rv
        return {
            "country_code": geo["country"]["iso_code"],
            "region": geo.get("subdivisions", [{}])[-1].get("iso_code"),
            "city": geo.get("city", {}).get("names", {}).get("en"),
            "latitude": geo["location"]["latitude"],
            "longitude": geo["location"]["longitude"],
        }

    geo_by_addr = _geo_by_addr


if settings.GEOIP_PATH_MMDB:
    _init_geoip()
