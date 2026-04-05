import math
from typing import Dict, Any, Optional, Tuple

class GPSLandVerifier:
    """
    GPS-based land verification service
    Verifies if farmer's actual location matches claimed land location
    """
    
    EARTH_RADIUS_KM = 6371
    
    def __init__(self):
        self.max_distance_meters = 5000  # 5km tolerance for land verification
        self.land_parcel_tolerance = 2000  # 2km for land parcel check
    
    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two GPS coordinates in meters"""
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return self.EARTH_RADIUS_KM * c * 1000  # Convert to meters
    
    def get_direction(self, lat1: float, lon1: float, lat2: float, lon2: float) -> str:
        """Get compass direction from point 1 to point 2"""
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lon = math.radians(lon2 - lon1)
        
        x = math.sin(delta_lon) * math.cos(lat2_rad)
        y = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon)
        
        bearing = math.degrees(math.atan2(x, y))
        bearing = (bearing + 360) % 360
        
        directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
        index = round(bearing / 45) % 8
        
        return directions[index]
    
    def verify_land_location(
        self,
        claimed_lat: float,
        claimed_lon: float,
        farmer_lat: float,
        farmer_lon: float,
        land_area_hectares: float = None
    ) -> Dict[str, Any]:
        """
        Verify if farmer's GPS location matches claimed land location
        
        Args:
            claimed_lat: Latitude from land records
            claimed_lon: Longitude from land records  
            farmer_lat: Farmer's current GPS latitude
            farmer_lon: Farmer's current GPS longitude
            land_area_hectares: Size of land for tolerance adjustment
        
        Returns:
            Verification result with distance, status, and confidence
        """
        # Calculate distance
        distance_meters = self.haversine_distance(
            claimed_lat, claimed_lon, 
            farmer_lat, farmer_lon
        )
        
        # Adjust tolerance based on land size
        tolerance = self.max_distance_meters
        if land_area_hectares:
            # Larger lands have more tolerance
            if land_area_hectares > 10:
                tolerance = 10000  # 10km for large farms
            elif land_area_hectares > 5:
                tolerance = 7500   # 7.5km
            elif land_area_hectares > 2:
                tolerance = 5000   # 5km
        
        # Determine verification status
        if distance_meters <= 500:
            status = "VERIFIED"
            confidence = 0.95
            status_note = "Farmer is at or very near the claimed land location"
        elif distance_meters <= tolerance:
            status = "LIKELY_VERIFIED"
            confidence = 0.75
            status_note = "Farmer location is within acceptable range of claimed land"
        elif distance_meters <= tolerance * 1.5:
            status = "NEEDS_REVIEW"
            confidence = 0.5
            status_note = "Distance exceeds normal tolerance - requires officer review"
        else:
            status = "MISMATCH"
            confidence = 0.2
            status_note = "Farmer location significantly differs from claimed land location"
        
        direction = self.get_direction(farmer_lat, farmer_lon, claimed_lat, claimed_lon)
        
        return {
            "verified": status in ["VERIFIED", "LIKELY_VERIFIED"],
            "status": status,
            "confidence": confidence,
            "distance_meters": round(distance_meters, 2),
            "tolerance_meters": tolerance,
            "direction_from_farmer_to_land": direction,
            "status_note": status_note,
            "claimed_location": {
                "latitude": claimed_lat,
                "longitude": claimed_lon
            },
            "farmer_location": {
                "latitude": farmer_lat,
                "longitude": farmer_lon
            }
        }
    
    def estimate_land_area_from_gps(
        self,
        corner_coords: list
    ) -> float:
        """
        Estimate land area from GPS coordinates of corners (polygon)
        
        Args:
            corner_coords: List of (lat, lon) tuples for land corners
        
        Returns:
            Estimated area in hectares
        """
        if len(corner_coords) < 3:
            return 0.0
        
        # Use Shoelace formula for polygon area
        # Convert to local Cartesian coordinates (approximate)
        center_lat = sum(c[0] for c in corner_coords) / len(corner_coords)
        center_lon = sum(c[1] for c in corner_coords) / len(corner_coords)
        
        # Convert to meters (approximate)
        coords_meters = []
        for lat, lon in corner_coords:
            x = (lon - center_lon) * 111320 * math.cos(math.radians(center_lat))
            y = (lat - center_lat) * 110540
            coords_meters.append((x, y))
        
        # Shoelace formula
        n = len(coords_meters)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += coords_meters[i][0] * coords_meters[j][1]
            area -= coords_meters[j][0] * coords_meters[i][1]
        
        area = abs(area) / 2
        
        # Convert square meters to hectares
        area_hectares = area / 10000
        
        return round(area_hectares, 4)
    
    def check_location_risk(
        self,
        farmer_lat: float,
        farmer_lon: float,
        disaster_lat: float = None,
        disaster_lon: float = None,
        disaster_radius_km: float = 50
    ) -> Dict[str, Any]:
        """
        Check if location is in a disaster-prone area
        
        Args:
            farmer_lat: Farmer's latitude
            farmer_lon: Farmer's longitude
            disaster_lat: Disaster center latitude
            disaster_lon: Disaster center longitude
            disaster_radius_km: Radius of disaster impact
        
        Returns:
            Risk assessment
        """
        if disaster_lat is None or disaster_lon is None:
            return {
                "in_disaster_zone": False,
                "risk_level": "UNKNOWN",
                "note": "No disaster zone data provided"
            }
        
        distance_km = self.haversine_distance(
            farmer_lat, farmer_lon,
            disaster_lat, disaster_lon
        ) / 1000
        
        if distance_km <= disaster_radius_km * 0.3:
            risk_level = "HIGH"
            in_zone = True
        elif distance_km <= disaster_radius_km * 0.6:
            risk_level = "MODERATE"
            in_zone = True
        elif distance_km <= disaster_radius_km:
            risk_level = "LOW"
            in_zone = True
        else:
            risk_level = "NONE"
            in_zone = False
        
        return {
            "in_disaster_zone": in_zone,
            "risk_level": risk_level,
            "distance_to_disaster_center_km": round(distance_km, 2),
            "disaster_radius_km": disaster_radius_km
        }


# Singleton instance
_gps_verifier = None

def get_gps_verifier() -> GPSLandVerifier:
    global _gps_verifier
    if _gps_verifier is None:
        _gps_verifier = GPSLandVerifier()
    return _gps_verifier
