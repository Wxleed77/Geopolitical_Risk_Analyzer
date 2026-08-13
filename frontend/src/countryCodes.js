// world-atlas topojson (used by react-simple-maps) identifies countries by
// ISO 3166-1 numeric code, which matches the UN M49 codes already used on
// the backend (backend/ingestion/country_codes.py) - same standard, kept
// in sync manually since this is a small, stable list.
export const ISO3_TO_NUMERIC = {
  USA: "842", GBR: "826", FRA: "251", DEU: "276", ITA: "380",
  CAN: "124", POL: "616", NOR: "579", ESP: "724", TUR: "792",
  NLD: "528", BEL: "056", JPN: "392", KOR: "410", AUS: "036",
  PRK: "408", CHN: "156", RUS: "643", IRN: "364", BLR: "112",
  KAZ: "398", ARM: "051", KGZ: "417", TJK: "762", IND: "356",
  UKR: "804", SAU: "682",
};

export const NUMERIC_TO_ISO3 = Object.fromEntries(
  Object.entries(ISO3_TO_NUMERIC).map(([iso3, numeric]) => [numeric, iso3])
);
