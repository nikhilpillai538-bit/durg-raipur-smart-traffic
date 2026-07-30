# parking_generator.py

import random
import numpy as np
import pandas as pd
from datetime import datetime
from parking_spots import PARKING_HUBS

class ParkingMockGenerator:
    def __init__(self, hubs_dict):
        self.hubs = hubs_dict

    def _calculate_occupancy_rate(self, hub_type, hour, is_weekend):
        """Simulates realistic crowds depending on time and site purpose."""
        if hour < 6 or hour >= 23:
            return random.uniform(0.05, 0.20)  # Night / Off-peak

        if hub_type == "commercial":
            if is_weekend:
                return random.uniform(0.75, 0.98) if 16 <= hour <= 21 else random.uniform(0.40, 0.70)
            return random.uniform(0.55, 0.85) if 17 <= hour <= 21 else random.uniform(0.20, 0.50)

        elif hub_type == "transit":
            return random.uniform(0.60, 0.90) if 7 <= hour <= 21 else random.uniform(0.30, 0.50)

        elif hub_type == "recreational":
            return random.uniform(0.75, 0.95) if 17 <= hour <= 22 else random.uniform(0.15, 0.40)

        return random.uniform(0.30, 0.60)

    def fetch_snapshot(self, target_time=None):
        """Generates a Pandas DataFrame snapshot for current or specified time."""
        now = target_time if target_time else datetime.now()
        hour = now.hour
        is_weekend = now.weekday() >= 5

        records = []
        for city, spots in self.hubs.items():
            for spot in spots:
                occ_rate = self._calculate_occupancy_rate(spot["type"], hour, is_weekend)
                occupied = int(spot["capacity"] * occ_rate)
                available = max(0, spot["capacity"] - occupied)
                occ_pct = round(occ_rate * 100, 1)

                records.append({
                    "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "city": city,
                    "location_name": spot["name"],
                    "latitude": spot["lat"],
                    "longitude": spot["lon"],
                    "capacity": spot["capacity"],
                    "occupied_spots": occupied,
                    "available_spots": available,
                    "occupancy_pct": occ_pct,
                    "status": "FULL" if occ_pct >= 85 else ("MODERATE" if occ_pct >= 50 else "AVAILABLE")
                })

        return pd.DataFrame(records)

# Direct execution test
if __name__ == "__main__":
    generator = ParkingMockGenerator(PARKING_HUBS)
    df_snapshot = generator.fetch_snapshot()
    
    print("=== LIVE PARKING SNAPSHOT (DURG & RAIPUR) ===")
    print(df_snapshot[["city", "location_name", "available_spots", "capacity", "status"]])