# A point on the map
# Global variables/constants

from math import sqrt, pi, radians, sin, cos, atan2

class Point:
    def __init__(self, lat=0.0, lon=0):
        self.lat = lat
        self.lon = lon

# A region on the map which is used to define the task MBR
class Region:
    def __init__(self):
        self.topLeft = Point()
        self.bottomRight = Point()

# US Address: CA,US
class Address:
    def __init__(self):
        self.country = ""
        self.state = ""


def distance_latlon(p1, p2):
    # Haversine formula example in Python
    # Original Author: Wayne Dyck

    earth_radius = 6371  # km

    dlat = radians(p2.lat - p1.lat)
    dlon = radians(p2.lon - p1.lon)
    a = sin(dlat / 2) * sin(dlat / 2) + cos(radians(p1.lat)) * cos(radians(p2.lat)) * sin(dlon / 2) * sin(dlon / 2)
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    d = earth_radius * c

    return d