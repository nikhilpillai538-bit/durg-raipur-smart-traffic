# traffic_engine.py
"""
Live traffic engine for the Durg-Raipur corridor -- Mappls (MapmyIndia) edition,
static REST License Key variant.

Some Mappls accounts are issued a single static "REST API license key"
instead of an OAuth client_id/client_secret pair. This version targets that
key type. It's the same shape of integration TomTom used to be: one secret,
hidden in an env var, never hardcoded, never logged, and only ever placed
directly in the outbound request URL at call time.

Endpoint used: the legacy Mappls Distance Matrix REST API --
  https://apis.mapmyindia.com/advancedmaps/v1/<key>/distance_matrix_eta/driving/{src};{dest}
which returns live-traffic-aware duration. A second lightweight call to the
plain (no-traffic) `distance_matrix` resource supplies the free-flow time
used for the congestion index -- confirmed response shape (per Mappls' own
GitHub samples):

    {
      "responseCode": 200,
      "results": {
        "code": "Ok",
        "distances": [[0, 6817.7, 20475.7]],   // meters
        "durations": [[0, 1844.4, 5307.5]]      // seconds
      }
    }

Coordinates in the URL path are longitude,latitude (opposite order from the
lat/lon dicts used elsewhere in this file) -- the engine handles that
conversion internally so you keep calling it with lat/lon like before.

Kept from the original version:
  - Session reuse + automatic retries with backoff
  - Short-lived in-memory caching for repeated dashboard polling
  - Concurrent fetching across corridor segments (ThreadPoolExecutor)
  - Structured logging instead of print()
  - Type hints + dataclass result object
  - Input validation on coordinates
  - Heuristic fallback so the dashboard never goes blank if the API is down
"""

import os
import time
import logging
import datetime
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Tuple, List
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter, Retry
import numpy as np

# Loads variables from a local .env file (if present) into the environment,
# so MAPPLS_API_KEY doesn't need to be manually `export`ed/`$env:`-set in
# every terminal session. Falls back silently to whatever's already in the
# environment (e.g. a real system env var, or a cloud host's secret
# manager) if python-dotenv isn't installed or there's no .env file --
# nothing about this is required for the app to run.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("traffic_engine")

# Coordinates for key corridor segments
CORRIDOR_NODES: Dict[str, Dict[str, float]] = {
    "Durg Station": {"lat": 21.1904, "lon": 81.2849},
    "Bhilai Steel Plant": {"lat": 21.1784, "lon": 81.3813},
    "GE Road Charoda": {"lat": 21.2162, "lon": 81.4468},
    "Amanaka Flyover Raipur": {"lat": 21.2468, "lon": 81.5985},
    "Raipur Clock Tower": {"lat": 21.2422, "lon": 81.6337},
    "Telibandha Lake Raipur": {"lat": 21.2335, "lon": 81.6616},
}


@dataclass
class TrafficResult:
    live_mins: float
    free_flow_mins: float
    congestion_index: float
    status_label: str
    status_color: str
    source: str  # "mappls_api" or "heuristic_fallback"
    timestamp: str

    def as_dict(self) -> dict:
        return asdict(self)


def decode_polyline(encoded: str, precision: int = 5) -> List[Tuple[float, float]]:
    """
    Decodes a Google-style encoded polyline string into a list of
    (lat, lon) tuples. Self-contained (no external `polyline` package
    needed) since this is the only place it's used.

    precision=5 matches Mappls' `geometries=polyline` (5-digit) output;
    use precision=6 if you request `geometries=polyline6` instead.
    """
    coords: List[Tuple[float, float]] = []
    index = lat = lon = 0
    factor = 10 ** precision

    while index < len(encoded):
        for is_lat in (True, False):
            shift = result = 0
            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            delta = ~(result >> 1) if (result & 1) else (result >> 1)
            if is_lat:
                lat += delta
            else:
                lon += delta
        coords.append((lat / factor, lon / factor))

    return coords


class MapplsTrafficEngine:
    BASE_URL = "https://apis.mapmyindia.com/advancedmaps/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_ttl_seconds: int = 90,
        max_retries: int = 3,
        request_timeout: int = 6,
    ):
        # Hidden key: pulled from an env var unless explicitly overridden.
        # Never hardcode this, never log it, never put it in an f-string
        # that ends up in a log/print statement.
        self.api_key = api_key or os.environ.get("MAPPLS_API_KEY")

        if self.api_key:
            logger.info(
                "Mappls API key detected (length=%d, starts with '%s...').",
                len(self.api_key), self.api_key[:4]
            )
        else:
            logger.warning(
                "No MAPPLS_API_KEY found in environment and none passed explicitly. "
                "Set it with: export MAPPLS_API_KEY=\"your_key\" (Linux/Mac) or "
                "$env:MAPPLS_API_KEY=\"your_key\" (PowerShell) before running."
            )

        self.request_timeout = request_timeout
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: Dict[Tuple[float, float, float, float], Tuple[float, TrafficResult]] = {}
        # Separate cache for road geometry -- roads don't move, so this can
        # live much longer than the live-traffic cache without going stale.
        self._route_cache: Dict[Tuple[float, float, float, float], Tuple[float, List[Tuple[float, float]]]] = {}
        self.route_cache_ttl_seconds = 3600

        # Reusable session with retry/backoff for transient network issues
        self.session = requests.Session()
        retries = Retry(
            total=max_retries,
            backoff_factor=0.5,  # 0.5s, 1s, 2s...
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _has_valid_key(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    @staticmethod
    def _validate_coords(lat: float, lon: float) -> None:
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            raise ValueError(f"Invalid coordinates: lat={lat}, lon={lon}")

    def _distance_matrix_url(self, resource: str, orig_lat: float, orig_lon: float,
                              dest_lat: float, dest_lon: float) -> str:
        """
        Builds a distance-matrix URL for the given resource
        ('distance_matrix' = no traffic, 'distance_matrix_eta' = with
        live/historic traffic). Mappls wants "longitude,latitude" order in
        the path, semicolon-separated between source and destination.
        """
        src = f"{orig_lon},{orig_lat}"
        dst = f"{dest_lon},{dest_lat}"
        return f"{self.BASE_URL}/{self.api_key}/{resource}/driving/{src};{dst}"

    # ---------------------------------------------------------------- #
    # Caching
    # ---------------------------------------------------------------- #
    def _cache_get(self, key: Tuple[float, float, float, float]) -> Optional[TrafficResult]:
        entry = self._cache.get(key)
        if not entry:
            return None
        cached_at, result = entry
        if time.time() - cached_at > self.cache_ttl_seconds:
            return None
        return result

    def _cache_set(self, key: Tuple[float, float, float, float], result: TrafficResult) -> None:
        self._cache[key] = (time.time(), result)

    # ---------------------------------------------------------------- #
    # Public API
    # ---------------------------------------------------------------- #
    def fetch_live_travel_time(
        self,
        orig_lat: float,
        orig_lon: float,
        dest_lat: float,
        dest_lon: float,
        use_cache: bool = True,
    ) -> TrafficResult:
        """
        Fetches travel time using the Mappls Distance-Time Matrix API, with
        caching, retries, and a heuristic fallback if the API is unavailable.
        """
        self._validate_coords(orig_lat, orig_lon)
        self._validate_coords(dest_lat, dest_lon)

        cache_key = (orig_lat, orig_lon, dest_lat, dest_lon)
        if use_cache:
            cached = self._cache_get(cache_key)
            if cached:
                logger.info("Cache hit for %s", cache_key)
                return cached

        result = self._fetch_from_api(orig_lat, orig_lon, dest_lat, dest_lon)
        if result is None:
            result = self._heuristic_fallback()

        self._cache_set(cache_key, result)
        return result

    def _fetch_from_api(
        self, orig_lat: float, orig_lon: float, dest_lat: float, dest_lon: float
    ) -> Optional[TrafficResult]:
        if not self._has_valid_key():
            logger.info("No valid Mappls API key configured; skipping live call.")
            return None

        try:
            # Live, traffic-aware duration
            eta_url = self._distance_matrix_url(
                "distance_matrix_eta", orig_lat, orig_lon, dest_lat, dest_lon
            )
            live_sec = self._call_distance_matrix(eta_url)
            if live_sec is None:
                return None

            # Free-flow (no-traffic) duration, for the congestion index.
            # Best-effort: if this second call fails, fall back to treating
            # the live time as the baseline (congestion index of 1.0)
            # rather than discarding a perfectly good live reading.
            plain_url = self._distance_matrix_url(
                "distance_matrix", orig_lat, orig_lon, dest_lat, dest_lon
            )
            free_sec = self._call_distance_matrix(plain_url)
            if free_sec is None:
                free_sec = live_sec

            live_mins = round(live_sec / 60.0, 1)
            free_mins = round(free_sec / 60.0, 1)
            congestion_index = round(live_mins / max(free_mins, 1.0), 2)
            status_label, status_color = self.classify_congestion(congestion_index)

            return TrafficResult(
                live_mins=live_mins,
                free_flow_mins=free_mins,
                congestion_index=congestion_index,
                status_label=status_label,
                status_color=status_color,
                source="mappls_api",
                timestamp=datetime.datetime.now().isoformat(timespec="seconds"),
            )

        except requests.exceptions.Timeout:
            logger.warning("Mappls API timed out after %ss; falling back.", self.request_timeout)
        except requests.exceptions.HTTPError as e:
            logger.warning("Mappls API HTTP error: %s; falling back.", e)
        except (KeyError, IndexError, ValueError) as e:
            logger.warning("Mappls API returned unexpected payload (%s); falling back.", e)
        except requests.exceptions.RequestException as e:
            logger.warning("Mappls API request failed (%s); falling back.", e)

        return None

    def _call_distance_matrix(self, url: str) -> Optional[float]:
        """
        Calls a Mappls distance-matrix URL and returns duration in seconds
        for the single source->destination pair, or None on failure/bad
        payload. Confirmed response shape (Mappls' own GitHub samples):

            {"results": {"code": "Ok", "distances": [[...]], "durations": [[...]]}}

        durations[0][1] is the source(0)->destination(1) leg; durations[0][0]
        is always 0 (source to itself).
        """
        response = self.session.get(url, params={"region": "ind"}, timeout=self.request_timeout)
        if not response.ok:
            logger.warning(
                "Mappls distance_matrix call failed: HTTP %d for %s -> body: %s",
                response.status_code,
                url.replace(self.api_key, "***KEY***"),
                response.text[:500],
            )
        response.raise_for_status()
        data = response.json()

        results = data.get("results")
        if not results or results.get("code") != "Ok":
            logger.warning("Mappls distance_matrix returned non-Ok payload: %s", data)
            return None

        durations = results.get("durations")
        if not durations or len(durations[0]) < 2:
            logger.warning("Mappls distance_matrix payload missing durations: %s", data)
            return None

        return float(durations[0][1])

    # ---------------------------------------------------------------- #
    # Route geometry (for drawing the actual road path on a map)
    # ---------------------------------------------------------------- #
    def fetch_route_geometry(
        self,
        orig_lat: float,
        orig_lon: float,
        dest_lat: float,
        dest_lon: float,
        use_cache: bool = True,
    ) -> List[Tuple[float, float]]:
        """
        Returns a list of (lat, lon) points tracing the actual road route
        between origin and destination, via Mappls' Routing API
        (`route_adv`). Falls back to a straight two-point line -- exactly
        what the map was drawing before -- if the API/key is unavailable,
        so the map never breaks even without live routing.
        """
        self._validate_coords(orig_lat, orig_lon)
        self._validate_coords(dest_lat, dest_lon)

        cache_key = (orig_lat, orig_lon, dest_lat, dest_lon)
        if use_cache:
            entry = self._route_cache.get(cache_key)
            if entry:
                cached_at, points = entry
                if time.time() - cached_at <= self.route_cache_ttl_seconds:
                    return points

        points = self._fetch_route_from_api(orig_lat, orig_lon, dest_lat, dest_lon)
        if points is None:
            logger.info("Falling back to a straight line for route geometry.")
            points = [(orig_lat, orig_lon), (dest_lat, dest_lon)]

        self._route_cache[cache_key] = (time.time(), points)
        return points

    def _fetch_route_from_api(
        self, orig_lat: float, orig_lon: float, dest_lat: float, dest_lon: float
    ) -> Optional[List[Tuple[float, float]]]:
        if not self._has_valid_key():
            logger.info("No valid Mappls API key configured; skipping live route fetch.")
            return None

        src = f"{orig_lon},{orig_lat}"
        dst = f"{dest_lon},{dest_lat}"
        url = f"{self.BASE_URL}/{self.api_key}/route_adv/driving/{src};{dst}"
        params = {"geometries": "polyline", "overview": "full", "region": "ind"}

        try:
            response = self.session.get(url, params=params, timeout=self.request_timeout)
            if not response.ok:
                logger.warning(
                    "Mappls route_adv call failed: HTTP %d for %s -> body: %s",
                    response.status_code,
                    url.replace(self.api_key, "***KEY***"),
                    response.text[:500],
                )
            response.raise_for_status()
            data = response.json()

            routes = data.get("routes")
            if not routes:
                logger.warning("Mappls route_adv returned no routes: %s", data)
                return None

            geometry = routes[0].get("geometry")
            if not geometry:
                logger.warning("Mappls route_adv route had no geometry field: %s", routes[0])
                return None

            points = decode_polyline(geometry, precision=5)
            if not points:
                logger.warning("Decoded route geometry was empty for %s", url.replace(self.api_key, "***KEY***"))
                return None

            return points

        except requests.exceptions.Timeout:
            logger.warning("Mappls route_adv timed out after %ss; falling back.", self.request_timeout)
        except requests.exceptions.HTTPError as e:
            logger.warning("Mappls route_adv HTTP error: %s; falling back.", e)
        except (KeyError, IndexError, ValueError) as e:
            logger.warning("Mappls route_adv returned unexpected payload (%s); falling back.", e)
        except requests.exceptions.RequestException as e:
            logger.warning("Mappls route_adv request failed (%s); falling back.", e)

        return None

    def _heuristic_fallback(self) -> TrafficResult:
        """Dynamic heuristic fallback modeling the Durg-Raipur peak curve."""
        current_hour = datetime.datetime.now().hour
        base_free_flow = 38.0  # Approx 38 mins baseline between Durg and Raipur

        if 9 <= current_hour <= 11 or 18 <= current_hour <= 20:
            mult = np.random.uniform(1.35, 1.65)
        elif 12 <= current_hour <= 16:
            mult = np.random.uniform(1.10, 1.25)
        else:
            mult = np.random.uniform(1.00, 1.10)

        live_mins = round(base_free_flow * mult, 1)
        free_mins = base_free_flow
        congestion_index = round(live_mins / free_mins, 2)
        status_label, status_color = self.classify_congestion(congestion_index)

        return TrafficResult(
            live_mins=live_mins,
            free_flow_mins=free_mins,
            congestion_index=congestion_index,
            status_label=status_label,
            status_color=status_color,
            source="heuristic_fallback",
            timestamp=datetime.datetime.now().isoformat(timespec="seconds"),
        )

    @staticmethod
    def classify_congestion(index: float) -> Tuple[str, str]:
        """Categorizes congestion levels based on index thresholds."""
        if index >= 1.35:
            return "PEAK / HEAVY TRAFFIC", "#FF4B4B"  # Red
        elif index >= 1.15:
            return "MODERATE TRAFFIC", "#FFAA00"       # Orange
        else:
            return "NORMAL / SMOOTH FLOW", "#00CC96"   # Green

    def fetch_corridor_snapshot(
        self, nodes: Dict[str, Dict[str, float]] = CORRIDOR_NODES, max_workers: int = 4
    ) -> Dict[str, TrafficResult]:
        """
        Fetches travel time for every consecutive segment along the corridor
        concurrently, returning a dict keyed by 'Origin -> Destination'.
        """
        names = list(nodes.keys())
        segments = list(zip(names[:-1], names[1:]))
        results: Dict[str, TrafficResult] = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_seg = {
                executor.submit(
                    self.fetch_live_travel_time,
                    nodes[o]["lat"], nodes[o]["lon"],
                    nodes[d]["lat"], nodes[d]["lon"],
                ): f"{o} -> {d}"
                for o, d in segments
            }
            for future in as_completed(future_to_seg):
                seg_name = future_to_seg[future]
                try:
                    results[seg_name] = future.result()
                except Exception as e:
                    logger.error("Segment %s failed: %s", seg_name, e)

        return results


# Quick test runner
if __name__ == "__main__":
    # The key is read from an env var -- nothing sensitive lives in this
    # file. Set it before running, e.g.:
    #   export MAPPLS_API_KEY="your_rest_license_key"
    engine = MapplsTrafficEngine()

    durg = CORRIDOR_NODES["Durg Station"]
    raipur = CORRIDOR_NODES["Telibandha Lake Raipur"]

    result = engine.fetch_live_travel_time(
        durg["lat"], durg["lon"], raipur["lat"], raipur["lon"]
    )
    print("=== LIVE CORRIDOR STATS (Durg -> Raipur) ===")
    print(f"Travel Time     : {result.live_mins} mins (Free-flow: {result.free_flow_mins} mins)")
    print(f"Congestion Index: {result.congestion_index}x")
    print(f"Status          : {result.status_label}")
    print(f"Source          : {result.source}")
    print()

    print("=== FULL CORRIDOR SNAPSHOT (concurrent) ===")
    snapshot = engine.fetch_corridor_snapshot()
    for segment, res in snapshot.items():
        print(f"{segment:45s} | {res.live_mins:5.1f} min | {res.status_label:22s} | {res.source}")