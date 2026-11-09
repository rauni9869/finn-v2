import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

CACHE_DIR = Path(os.getenv("FINN_CACHE_DIR", ROOT_DIR / ".cache"))
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# Cheap models for short bulk jobs, stronger ones where reasoning matters. Later entries are fallbacks.
FAST_MODELS = os.getenv("FINN_FAST_MODELS", "gemini-flash-lite-latest,gemini-3.1-flash-lite").split(",")
REASONING_MODELS = os.getenv("FINN_REASONING_MODELS", "gemini-3-flash-preview,gemini-flash-latest").split(",")

# Mock portfolio: 18 NSE companies across sectors and sizes
PORTFOLIO = [
    {"ticker": "RELIANCE", "name": "Reliance Industries", "sector": "Energy & Conglomerate", "size": "Mega"},
    {"ticker": "HDFCBANK", "name": "HDFC Bank", "sector": "Banking", "size": "Large"},
    {"ticker": "TCS", "name": "Tata Consultancy Services", "sector": "IT Services", "size": "Large"},
    {"ticker": "TMPV", "name": "Tata Motors Passenger Vehicles", "sector": "Automobiles", "size": "Large"},
    {"ticker": "SUNPHARMA", "name": "Sun Pharmaceutical", "sector": "Pharma", "size": "Large"},
    {"ticker": "LT", "name": "Larsen & Toubro", "sector": "Infrastructure", "size": "Large"},
    {"ticker": "TITAN", "name": "Titan Company", "sector": "Consumer", "size": "Large"},
    {"ticker": "ITC", "name": "ITC", "sector": "FMCG", "size": "Large"},
    {"ticker": "PERSISTENT", "name": "Persistent Systems", "sector": "IT Services", "size": "Mid"},
    {"ticker": "POLYCAB", "name": "Polycab India", "sector": "Cables & Wires", "size": "Mid"},
    {"ticker": "TRENT", "name": "Trent", "sector": "Retail", "size": "Mid"},
    {"ticker": "FEDERALBNK", "name": "Federal Bank", "sector": "Banking", "size": "Mid"},
    {"ticker": "DEEPAKNTR", "name": "Deepak Nitrite", "sector": "Chemicals", "size": "Mid"},
    {"ticker": "KAYNES", "name": "Kaynes Technology", "sector": "Electronics Mfg", "size": "Small"},
    {"ticker": "ZENTEC", "name": "Zen Technologies", "sector": "Defence", "size": "Small"},
    {"ticker": "SUPRIYA", "name": "Supriya Lifescience", "sector": "Pharma", "size": "Small"},
    {"ticker": "ETHOSLTD", "name": "Ethos", "sector": "Luxury Retail", "size": "Small"},
    {"ticker": "KSOLVES", "name": "Ksolves India", "sector": "IT Services", "size": "Micro"},
]

# Suggested companies outside the portfolio for on-demand research
AD_HOC = ["SWIGGY", "DIXON", "ETERNAL", "BEL"]
