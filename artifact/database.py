import ast
import json
import os
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine, func
from sqlalchemy.orm import DeclarativeBase, sessionmaker

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "realbeauty.db")

engine = create_engine(f"sqlite:///{DB_PATH}")


class Base(DeclarativeBase):
    pass


Session = sessionmaker(bind=engine)


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True)
    barcode = Column(String, nullable=True)
    product_name = Column(String)
    brand = Column(String)
    ingredients_text = Column(Text)
    score = Column(Integer)
    summary = Column(Text)
    flagged_json = Column(Text)
    safe_highlights_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(engine)


def normalize_ingredients(text):
    """Remove extra spaces and line breaks, so the same list is stored the same way."""
    return " ".join(text.split())


def save_analysis(barcode, product_name, brand, ingredients_text, result):
    session = Session()
    analysis = Analysis(
        barcode=barcode,
        product_name=product_name,
        brand=brand,
        ingredients_text=normalize_ingredients(ingredients_text),
        score=result["score"],
        summary=result["summary"],
        flagged_json=json.dumps(result["flagged"]),
        safe_highlights_json=json.dumps(result["safe_highlights"]),
    )
    session.add(analysis)
    session.commit()
    session.close()


def get_history():
    session = Session()
    analyses = session.query(Analysis).order_by(Analysis.created_at.desc()).all()
    session.close()
    return analyses


def parse_list(text):
    """Read a saved list. Old rows used Python's str() instead of JSON."""
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return ast.literal_eval(text)  # safe: only reads plain Python values


def find_cached_analysis(ingredients_text):
    """Return a saved result for the same ingredient list, or None."""
    session = Session()
    analysis = (
        session.query(Analysis)
        .filter(  # compare without caring about upper or lower case
            func.lower(Analysis.ingredients_text)
            == normalize_ingredients(ingredients_text).lower()
        )
        .order_by(Analysis.created_at.desc())
        .first()
    )
    session.close()
    if analysis is None:
        return None
    try:
        return {
            "score": analysis.score,
            "summary": analysis.summary,
            "flagged": parse_list(analysis.flagged_json),
            "safe_highlights": parse_list(analysis.safe_highlights_json),
        }
    except (TypeError, ValueError, SyntaxError):
        return None  # unreadable row: analyse again instead
