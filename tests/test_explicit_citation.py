import pytest
from src.recommend import StandardsRecommender
from src.extract import Requirement

@pytest.fixture
def recommender():
    return StandardsRecommender()

def test_explicit_cpvc_citation(recommender):
    text = "Supply and installation of CPVC pipes and fittings for domestic hot and cold water distribution system, conforming to IS 15778."
    req = Requirement(
        requirement_id="1", 
        requirement_text=text, 
        category="product_equipment",
        explicit_standards=["IS 15778"]
    )
    
    result = recommender.recommend_for_requirement(req)
    
    assert result.critic_result["decision"] in ["REVIEW_REQUIRED", "RECOMMEND", "RECOMMEND_WITH_REVIEW"], f"Decision was {result.critic_result['decision']}"
    assert result.candidate_standard is not None
    assert "IS 15778" in result.candidate_standard
    # Ensure evidence was extracted and scored high
    assert result.critic_result["evidence"]["evidence_strength"] == "STRONG"
    assert result.deterministic_score == 1.0

def test_no_citation_cpvc(recommender):
    text = "Supply and installation of CPVC pipes and fittings for domestic hot and cold water distribution system."
    req = Requirement(
        requirement_id="2", 
        requirement_text=text, 
        category="product_equipment",
        explicit_standards=[]
    )
    
    result = recommender.recommend_for_requirement(req)
    
    # Should still find IS 15778 but through semantic/bm25 discovery
    assert result.candidate_standard is not None
    assert "IS 15778" in result.candidate_standard
    assert result.deterministic_score < 1.0 # Because it wasn't explicitly cited
