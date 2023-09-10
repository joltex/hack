import csv
from typing import List, Optional

import attrs
import cattrs
import requests
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim
from geopy.location import Location as GeopyLocation
from gmplot import gmplot


@attrs.define
class Location:
    address: str
    city: str
    geopy_location: Optional[GeopyLocation] = attrs.field(init=False)
    name: Optional[str] = attrs.field(default=None)

    @geopy_location.default
    def _geolocate(self):
        try:
            geolocator = Nominatim(user_agent="joltex")
            return geolocator.geocode(f"{self.address}, {self.city}")
        except:
            return None

    @property
    def latitude(self) -> Optional[float]:
        if self.geopy_location:
            return self.geopy_location.latitude
        else:
            return None

    @property
    def longitude(self) -> Optional[float]:
        if self.geopy_location:
            return self.geopy_location.longitude
        else:
            return None


def get_locations_without_photos(
    url: str,
    location_col: str = "Location",
    photo_col: str = "Photo",
    city: str = "Vancouver",
) -> List[Location]:
    """Parse a Wikipedia page with tables of locations and associated photos and
    return a list of all locations without a photo

    :param url: Address of the Wikipedia page, expected to have tables with at least an
                `address` column and `photo` column.
    :param location_col: String or substring that identifies the table columns containing
                        location information.
    :param photo_col: String or substring that identifies the table columns containing
                      photos.
    :param city: City in which the addresses are located.
    :return: List of Location objects without associated photos.
    """
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    tables = soup.findAll("table", {"class": "wikitable"})

    locations_without_photos = []
    for table in tables:
        headers = [header.get_text(strip=True) for header in table.findAll("th")]

        # Identify the table indices of the location and photo columns
        photo_index = next(
            (i for i, header in enumerate(headers) if photo_col in header), None
        )
        location_index = next(
            (i for i, header in enumerate(headers) if location_col in header), None
        )

        # If both columns are present, proceed to extract data
        if photo_index is not None and location_index is not None:
            rows = table.findAll("tr")
            for row in rows:
                columns = row.findAll("td")
                if len(columns) > max(photo_index, location_index):
                    photo_column = columns[photo_index]
                    address = columns[location_index].get_text(strip=True)
                    if not photo_column.find("img"):
                        locations_without_photos.append(
                            Location(address=address, city=city)
                        )

    return locations_without_photos


def generate_google_maps_url_for_ios(
    locations: List[Location], start_location: Optional[Location] = None
) -> str:
    """Generate a Google maps URL for a collection of locations that can be
    openned by the Google Maps iOS app

    :param locations: List of Location objects with latitude and longitude attributes.
    :param start_location: Location to start from. If None, start at `locations[0]`.
    :return: Google maps iOS URL with all locations.
    """
    start_location = start_location if start_location else locations[0]
    start_str = f"{start_location.latitude},{start_location.longitude}"
    destination_locations = "+to:".join(
        [f"{loc.latitude},{loc.longitude}" for loc in locations]
    )
    url = f"comgooglemaps://?saddr={start_location}&daddr={destination_locations}"

    return url


def plot_locations_on_map(
    locations: List[Location],
    centre_location: Optional[Location] = None,
    output_path="./map.html",
):
    """Generate a Google maps html file that displays a list of Locations

    :param locations: List of Location objects with latitude and longitude attributes.
    :param centre_location: Location on which to centre the map. If None, centre on
                            `locations[0]`.
    :param output_path: Output path to save map to.
    """
    centre_location = centre_location if centre_location else locations[0]
    gmap = gmplot.GoogleMapPlotter(
        centre_location.latitude, centre_location.longitude, 13
    )
    for location in locations:
        gmap.marker(location.latitude, location.longitude, title=location.address)
    gmap.draw(output_path)


def to_csv(locations: List[Location], output_path="./locations.csv"):
    """Save a list of locations to a csv file that can be imported by
    Google MyMaps

    :param locations: List of Location objects.
    :param output_path: Path to save csv file to.
    """
    converter = cattrs.Converter()
    hook = cattrs.gen.make_dict_unstructure_fn(
        Location, converter, geopy_location=cattrs.gen.override(omit=True)
    )
    converter.register_unstructure_hook(Location, hook)
    csv_data = [converter.unstructure(location) for location in locations]

    with open(output_path, "w", encoding="utf8", newline="") as fout:
        csv_writer = csv.DictWriter(fout, fieldnames=csv_data[0].keys())
        csv_writer.writeheader()
        csv_writer.writerows(csv_data)
