from .territory import Territory

TERRITORIES = [
    ("Alaska", "North America", ["Northwest Territory", "Alberta", "Kamchatka"]),
    ("Northwest Territory", "North America", ["Alaska", "Alberta", "Ontario", "Greenland"]),
    ("Greenland", "North America", ["Northwest Territory", "Ontario", "Quebec", "Iceland"]),
    ("Alberta", "North America", ["Alaska", "Northwest Territory", "Ontario", "Western United States"]),
    ("Ontario", "North America", ["Northwest Territory", "Alberta", "Greenland", "Quebec", "Western United States", "Eastern United States"]),
    ("Quebec", "North America", ["Ontario", "Greenland", "Eastern United States"]),
    ("Western United States", "North America", ["Alberta", "Ontario", "Eastern United States", "Central America"]),
    ("Eastern United States", "North America", ["Ontario", "Quebec", "Western United States", "Central America"]),
    ("Central America", "North America", ["Western United States", "Eastern United States", "Venezuela"]),
    ("Venezuela", "South America", ["Central America", "Brazil", "Peru"]),
    ("Brazil", "South America", ["Venezuela", "Peru", "Argentina", "North Africa"]),
    ("Peru", "South America", ["Venezuela", "Brazil", "Argentina"]),
    ("Argentina", "South America", ["Peru", "Brazil"]),
    ("Iceland", "Europe", ["Greenland", "Great Britain", "Scandinavia"]),
    ("Great Britain", "Europe", ["Iceland", "Scandinavia", "Northern Europe", "Western Europe"]),
    ("Scandinavia", "Europe", ["Iceland", "Great Britain", "Northern Europe", "Ukraine"]),
    ("Northern Europe", "Europe", ["Great Britain", "Scandinavia", "Ukraine", "Western Europe", "Southern Europe"]),
    ("Western Europe", "Europe", ["Great Britain", "Northern Europe", "Southern Europe", "North Africa"]),
    ("Southern Europe", "Europe", ["Northern Europe", "Western Europe", "Ukraine", "North Africa", "Egypt", "Middle East"]),
    ("Ukraine", "Europe", ["Scandinavia", "Northern Europe", "Southern Europe", "Ural", "Afghanistan", "Middle East"]),
    ("North Africa", "Africa", ["Brazil", "Western Europe", "Southern Europe", "Egypt", "East Africa", "Congo"]),
    ("Egypt", "Africa", ["Southern Europe", "North Africa", "East Africa", "Middle East"]),
    ("East Africa", "Africa", ["North Africa", "Egypt", "Congo", "South Africa", "Madagascar", "Middle East"]),
    ("Congo", "Africa", ["North Africa", "East Africa", "South Africa"]),
    ("South Africa", "Africa", ["Congo", "East Africa", "Madagascar"]),
    ("Madagascar", "Africa", ["East Africa", "South Africa"]),
    ("Ural", "Asia", ["Ukraine", "Siberia", "China", "Afghanistan"]),
    ("Siberia", "Asia", ["Ural", "Yakutsk", "Irkutsk", "Mongolia", "China"]),
    ("Yakutsk", "Asia", ["Siberia", "Kamchatka", "Irkutsk"]),
    ("Kamchatka", "Asia", ["Alaska", "Yakutsk", "Irkutsk", "Mongolia", "Japan"]),
    ("Irkutsk", "Asia", ["Siberia", "Yakutsk", "Kamchatka", "Mongolia"]),
    ("Mongolia", "Asia", ["Siberia", "Irkutsk", "Kamchatka", "Japan", "China"]),
    ("Japan", "Asia", ["Kamchatka", "Mongolia"]),
    ("China", "Asia", ["Ural", "Siberia", "Mongolia", "Afghanistan", "India", "Siam"]),
    ("Afghanistan", "Asia", ["Ukraine", "Ural", "China", "India", "Middle East"]),
    ("Middle East", "Asia", ["Ukraine", "Southern Europe", "Egypt", "East Africa", "Afghanistan", "India"]),
    ("India", "Asia", ["Afghanistan", "China", "Middle East", "Siam"]),
    ("Siam", "Asia", ["China", "India", "Indonesia"]),
    ("Indonesia", "Australia", ["Siam", "New Guinea", "Western Australia"]),
    ("New Guinea", "Australia", ["Indonesia", "Eastern Australia", "Western Australia"]),
    ("Western Australia", "Australia", ["Indonesia", "New Guinea", "Eastern Australia"]),
    ("Eastern Australia", "Australia", ["New Guinea", "Western Australia"]),
]

class Board:
    def __init__(self):
        self.territories = {}
        for name, continent, neighbors in TERRITORIES:
            self.territories[name] = Territory(name, continent, neighbors)

    def get(self, name):
        return self.territories.get(name)

    def all_territories(self):
        return list(self.territories.values())
