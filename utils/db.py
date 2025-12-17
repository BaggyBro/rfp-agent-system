"""Database helpers for accessing the product catalog in PostgreSQL."""

from __future__ import annotations

import logging
import os
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

from sqlalchemy import Column, Float, Integer, String, create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for ORM models."""


class Product(Base):
    """SQLAlchemy model mapping to the products catalog table."""

    __tablename__ = "products"

    sku = Column(String, primary_key=True)
    product_name = Column(String)
    voltage = Column(String)
    insulation = Column(String)
    core_count = Column(Integer)
    cross_section_mm2 = Column(Float)
    armor = Column(String)
    standard = Column(String)
    base_price = Column(Float)
    conductor_material = Column(String)


def get_engine():
    """Create the SQLAlchemy engine from env or defaults."""
    uri = os.getenv(
        "POSTGRES_URI",
        "postgresql+psycopg2://postgres:kakarot*9000@localhost/rfp_catalog",
    )
    return create_engine(uri, echo=False)


def get_session_factory():
    """Return a session factory bound to the catalog engine."""
    engine = get_engine()
    return sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


@dataclass
class ProductMatch:
    """Structured representation of a product with a match score and reason."""

    sku: str
    product_name: str
    base_price: float
    match_score: float
    reason: str
    voltage: Optional[str] = None
    insulation: Optional[str] = None
    core_count: Optional[int] = None
    cross_section_mm2: Optional[float] = None
    armor: Optional[str] = None
    standard: Optional[str] = None
    conductor_material: Optional[str] = None

    def as_dict(self) -> Dict:
        return asdict(self)


def query_products(filters: Dict[str, Optional[str]], limit: int = 10) -> List[Dict]:
    """
    Query products from PostgreSQL that match the provided filters.

    The filters are soft; missing values are ignored. Returns at most `limit`
    rows, sorted by base price ascending as a simple heuristic.
    """
    logger.info(f"[DB] Querying products with filters: {filters}, limit: {limit}")
    SessionLocal = get_session_factory()
    try:
        with SessionLocal() as session:
            stmt = select(Product)
            active_filters = []
            if filters.get("voltage"):
                stmt = stmt.where(Product.voltage == filters["voltage"])
                active_filters.append(f"voltage={filters['voltage']}")
            if filters.get("insulation"):
                stmt = stmt.where(Product.insulation == filters["insulation"])
                active_filters.append(f"insulation={filters['insulation']}")
            if filters.get("core_count"):
                try:
                    stmt = stmt.where(Product.core_count == int(filters["core_count"]))
                    active_filters.append(f"core_count={filters['core_count']}")
                except (TypeError, ValueError):
                    pass
            if filters.get("standard"):
                stmt = stmt.where(Product.standard.ilike(f"%{filters['standard']}%"))
                active_filters.append(f"standard={filters['standard']}")
            if filters.get("conductor_material"):
                stmt = stmt.where(Product.conductor_material == filters["conductor_material"])
                active_filters.append(f"conductor_material={filters['conductor_material']}")

            logger.debug(f"[DB] Active filters: {', '.join(active_filters) if active_filters else 'none'}")
            stmt = stmt.order_by(Product.base_price.asc()).limit(limit)
            results = session.execute(stmt).scalars().all()
            logger.info(f"[DB] Query returned {len(results)} products")
            return [
                {
                    "sku": p.sku,
                    "product_name": p.product_name,
                    "voltage": p.voltage,
                    "insulation": p.insulation,
                    "core_count": p.core_count,
                    "cross_section_mm2": p.cross_section_mm2,
                    "armor": p.armor,
                    "standard": p.standard,
                    "base_price": p.base_price,
                    "conductor_material": p.conductor_material,
                }
                for p in results
            ]
    except SQLAlchemyError as e:
        logger.error(f"[DB] Database query failed: {str(e)}")
        # If database is not reachable, return empty list gracefully.
        return []


