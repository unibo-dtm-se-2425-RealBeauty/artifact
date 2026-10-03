import os
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime
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


def save_analysis(barcode, product_name, brand, ingredients_text, result):
    session = Session()
    analysis = Analysis(
        barcode=barcode,
        product_name=product_name,
        brand=brand,
        ingredients_text=ingredients_text,
        score=result["score"],
        summary=result["summary"],
        flagged_json=str(result["flagged"]),
        safe_highlights_json=str(result["safe_highlights"]),
    )
    session.add(analysis)
    session.commit()
    session.close()


def get_history():
    session = Session()
    analyses = session.query(Analysis).order_by(Analysis.created_at.desc()).all()
    session.close()
    return analyses
