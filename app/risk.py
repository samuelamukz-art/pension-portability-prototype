from datetime import datetime
import statistics

def score_fund(contributions: list[dict]) -> dict:
    """Prototype 'AI' scorer: transparent, deterministic, explainable.
    Real ML model slots in later behind the same interface."""
    if not contributions:
        return {"fund_id": "N/A", "risk_score": 0.0, "sustainability_score": 0.0,
                "top_factors": [], "confidence": 0.0, "generated_at": datetime.utcnow()}

    amounts = [c["amount"] for c in contributions]
    volatility = statistics.pstdev(amounts) / (statistics.mean(amounts) or 1)
    concentration = 1 / len({c["institution_id"] for c in contributions})
    employer_churn = len({c["employer_id"] for c in contributions}) / len(contributions)

    risk = min(1.0, 0.5*volatility + 0.3*concentration + 0.2*employer_churn)
    sustainability = max(0.0, 1.0 - risk*0.7)
    confidence = min(0.99, 0.5 + 0.05*len(contributions))

    return {
        "fund_id": contributions[0]["institution_id"],
        "risk_score": round(risk, 3),
        "sustainability_score": round(sustainability, 3),
        "top_factors": [
            {"factor": "contribution_volatility", "weight": round(0.5*volatility, 3)},
            {"factor": "institution_concentration", "weight": round(0.3*concentration, 3)},
            {"factor": "employer_churn", "weight": round(0.2*employer_churn, 3)},
        ],
        "confidence": round(confidence, 3),
        "generated_at": datetime.utcnow(),
    }