"""Constants for Bratislava MHD."""

DOMAIN = "bratislava_mhd"

STOPS_URL = "https://api.magicsk.eu/stops"
SOCKET_URL = "https://imhd.sk"
SOCKET_PATH = "/rt/sio2"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_USER_AGENT = "ha-bratislava-mhd/0.2 (Home Assistant integration)"
# lon/lat corners of the IDS BK area, a search bias only.
BRATISLAVA_VIEWBOX = "16.80,48.40,17.45,47.95"
VEHICLE_IMG_URL = "https://imhd.sk/ba/media/{folder}/{img:08d}/{vehicle}"

CONF_STOPS = "stops"
CONF_PLATFORMS = "platforms"
CONF_LATITUDE = "latitude"
CONF_LONGITUDE = "longitude"
CONF_RADIUS = "radius"
CONF_MAX_STOPS = "max_stops"
CONF_MAX_DEPARTURES = "max_departures"

DEFAULT_RADIUS = 500
DEFAULT_MAX_STOPS = 10
DEFAULT_MAX_DEPARTURES = 8

# Platforms the board lists but the stop catalogue doesn't label.
UNKNOWN_PLATFORM = "?"

CARD_URL = "/bratislava_mhd/bratislava-mhd-card.js"
