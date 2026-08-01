from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Country(Base):
    __tablename__ = "country"
    iso_code = Column(String(3), primary_key=True)
    name = Column(String, nullable=False)
    region = Column(String, nullable=False)


class TradeFlow(Base):
    __tablename__ = "trade_flow"
    id = Column(Integer, primary_key=True)
    reporter_iso = Column(String(3), ForeignKey("country.iso_code"), nullable=False)
    partner_iso = Column(String(3), ForeignKey("country.iso_code"), nullable=False)
    hs_sector_code = Column(String, nullable=False)
    year = Column(Integer, nullable=False)
    trade_value_usd = Column(Float, nullable=False)
    flow_type = Column(String, nullable=False)  # "import" | "export"


class EnergyDependency(Base):
    __tablename__ = "energy_dependency"
    id = Column(Integer, primary_key=True)
    country_iso = Column(String(3), ForeignKey("country.iso_code"), nullable=False)
    source_country_iso = Column(String(3), ForeignKey("country.iso_code"), nullable=False)
    year = Column(Integer, nullable=False)
    import_share_pct = Column(Float, nullable=False)
    energy_type = Column(String, nullable=False)


class Alliance(Base):
    __tablename__ = "alliance"
    id = Column(Integer, primary_key=True)
    country_a_iso = Column(String(3), ForeignKey("country.iso_code"), nullable=False)
    country_b_iso = Column(String(3), ForeignKey("country.iso_code"), nullable=False)
    treaty_name = Column(String, nullable=False)
    year_signed = Column(Integer, nullable=False)
    alliance_type = Column(String, nullable=False)


class ConflictCase(Base):
    __tablename__ = "conflict_case"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    country_a_iso = Column(String(3), ForeignKey("country.iso_code"), nullable=False)
    country_b_iso = Column(String(3), ForeignKey("country.iso_code"), nullable=False)
    start_date = Column(Date, nullable=False)
    description = Column(Text, nullable=False)
    documented_outcome = Column(Text, nullable=False)


class ConflictQuery(Base):
    __tablename__ = "conflict_query"
    id = Column(Integer, primary_key=True)
    raw_input = Column(Text)
    country_a_iso = Column(String(3), ForeignKey("country.iso_code"))
    country_b_iso = Column(String(3), ForeignKey("country.iso_code"))
    conflict_type = Column(String)
    created_at = Column(DateTime, nullable=False)


class ExposureScore(Base):
    __tablename__ = "exposure_score"
    id = Column(Integer, primary_key=True)
    conflict_query_id = Column(Integer, ForeignKey("conflict_query.id"), nullable=False)
    affected_country_iso = Column(String(3), ForeignKey("country.iso_code"), nullable=False)
    trade_score = Column(Float)
    energy_score = Column(Float)
    alliance_score = Column(Float)
    composite_score = Column(Float)


class HistoricalShockImpact(Base):
    __tablename__ = "historical_shock_impact"
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("conflict_case.id"), nullable=False)
    country_iso = Column(String(3), ForeignKey("country.iso_code"), nullable=False)
    indicator = Column(String, nullable=False)  # "fuel_price" | "cpi" | "currency"
    change_pct = Column(Float, nullable=False)
    timeframe = Column(String, nullable=False)  # e.g. "within 6 months"
    source_note = Column(Text, nullable=False)


class NarrativeReport(Base):
    __tablename__ = "narrative_report"
    id = Column(Integer, primary_key=True)
    conflict_query_id = Column(Integer, ForeignKey("conflict_query.id"), nullable=False, unique=True)
    content = Column(Text, nullable=False)
    citations = Column(JSON, nullable=False)
    confidence_tags = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False)
