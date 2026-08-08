# UN Comtrade uses M49 numeric country codes, not ISO 3166-1 alpha-3.
# Covers only the countries currently seeded in countries_seed.csv -
# extend this if you add more countries.
ISO3_TO_M49 = {
    "USA": 842, "GBR": 826, "FRA": 251, "DEU": 276, "ITA": 380,
    "CAN": 124, "POL": 616, "NOR": 579, "ESP": 724, "TUR": 792,
    "NLD": 528, "BEL": 56, "JPN": 392, "KOR": 410, "AUS": 36,
    "PRK": 408, "CHN": 156, "RUS": 643, "IRN": 364, "BLR": 112,
    "KAZ": 398, "ARM": 51, "KGZ": 417, "TJK": 762, "IND": 356,
    "UKR": 804,
}

WORLD_PARTNER_CODE = 0  # Comtrade's "World" partner code
