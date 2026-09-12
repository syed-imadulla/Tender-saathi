"""Deterministic Technical Procurement Lexicon for Offline Normalization Fallback.

Provides vocabulary mappings for Indian procurement terminology across:
- Hindi (Devanagari)
- Kannada (Kannada script)
- Tamil (Tamil script)
- Transliterated romanized procurement verbs/nouns

CRITICAL ARCHITECTURAL CONSTRAINTS:
1. This module translates technical vocabulary ONLY (e.g., 'वितरण ट्रांसफार्मर' -> 'distribution transformer').
2. This module NEVER maps products to Indian Standard (IS) numbers. Standard recommendation
   is strictly performed by the downstream StandardsRecommender.
3. This is a deterministic fallback used when LLM is offline or disabled.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple


# Technical noun and compound mappings (Indic -> English technical noun)
# Hindi (Devanagari)
HINDI_TECHNICAL_TERMS: Dict[str, str] = {
    # Transformers & Electrical
    "वितरण ट्रांसफार्मर": "distribution transformer",
    "ट्रांसफार्मर": "transformer",
    "पावर ट्रांसफार्मर": "power transformer",
    "वोल्टेज": "voltage",
    "धारा": "current",
    "विद्युत": "electrical",
    "केबल": "cable",
    "भूमिगत केबल": "underground cable",
    "एक्सएलपीई": "XLPE",
    "पीवीसी": "PVC",
    "कंडक्टर": "conductor",
    "स्विचगियर": "switchgear",
    "सर्किट ब्रेकर": "circuit breaker",
    "मोटर": "motor",
    "प्रेरण मोटर": "induction motor",
    
    # Units & Ratings
    "केवीए": "kVA",
    "केवी": "kV",
    "किलोवाट": "kW",
    "एमएम": "mm",
    "मिमी": "mm",
    "मीटर": "meter",
    "इंच": "inch",
    "बार": "bar",
    "वर्ग मिमी": "sq mm",
    "स्क्वायर एमएम": "sq mm",
    
    # Materials & Components
    "कास्ट आयरन": "cast iron",
    "कास्ट स्टील": "cast steel",
    "तांबा": "copper",
    "एल्युमिनियम": "aluminium",
    "स्टेनलेस स्टील": "stainless steel",
    "हल्का स्टील": "mild steel",
    "जस्ती": "galvanized",
    "गैल्वनाइज्ड": "galvanized",

    
    # Valves & Fittings
    "गेट वाल्व": "gate valve",
    "वाल्व": "valve",
    "स्लुइस वाल्व": "sluice valve",
    "चेक वाल्व": "check valve",
    "नॉन रिटर्न वाल्व": "non-return valve",
    "बॉल वाल्व": "ball valve",
    "बटरफ्लाई वाल्व": "butterfly valve",
    
    # Pumps
    "सबमर्सिबल पंप": "submersible pump",
    "पंप": "pump",
    "पंपसेट": "pump set",
    "केन्द्रापसारक पंप": "centrifugal pump",
    
    # Materials & Construction
    "सीमेंट": "cement",
    "पोर्टलैंड सीमेंट": "portland cement",
    "साधारण पोर्टलैंड सीमेंट": "ordinary portland cement",
    "स्टील": "steel",
    "इस्पात": "steel",
    "सरिया": "TMT bar",
    "टीएमटी सरिया": "TMT bar",
    "संरचनात्मक स्टील": "structural steel",
    
    # Scope / Action
    "आपूर्ति": "supply",
    "बिछाने": "laying",
    "बिछाना": "laying",
    "स्थापना": "installation",
    "परीक्षण": "testing",
    "चालू करना": "commissioning",
    "रखरखाव": "maintenance",
}

# Kannada (Kannada script)
KANNADA_TECHNICAL_TERMS: Dict[str, str] = {
    # Transformers & Electrical
    "ವಿತರಣಾ ಪರಿವರ್ತಕ": "distribution transformer",
    "ಟ್ರಾನ್ಸ್‌ಫಾರ್ಮರ್": "transformer",
    "ಟ್ರಾನ್ಸ್ಫಾರ್ಮರ್": "transformer",
    "ವಿದ್ಯುತ್": "electrical",
    "ಕೇಬಲ್": "cable",
    "ಭೂಗತ ಕೇಬಲ್": "underground cable",
    "ಎಕ್ಸ್‌ಎಲ್‌ಪಿಇ": "XLPE",
    "ಪಿವಿಸಿ": "PVC",
    "ವಾಹಕ": "conductor",
    "ಸ್ವಿಚ್‌ಗೇರ್": "switchgear",
    "ಮೋಟರ್": "motor",
    
    # Pipes & Plumbing
    "ಸಿಪಿವಿಸಿ": "CPVC",
    "ಪೈಪ್": "pipe",
    "ಪೈಪ್‌ಗಳು": "pipes",
    "ಕೊಳವೆ": "pipe",
    "ನೀರು ಸರಬರಾಜು": "water supply",
    "ಕುಡಿಯುವ ನೀರು": "drinking water",
    "ಜಿಐ ಪೈಪ್": "GI pipe",
    "ಎಚ್‌ಡಿಪಿಇ": "HDPE",
    
    # Valves & Fittings
    "ಗೇಟ್ ವಾಲ್ವ್": "gate valve",
    "ವಾಲ್ವ್": "valve",
    "ಸ್ಲೂಯಿಸ್ ವಾಲ್ವ್": "sluice valve",
    "ಚೆಕ್ ವಾಲ್ವ್": "check valve",
    "ನಾನ್ ರಿಟರ್ನ್ ವಾಲ್ವ್": "non-return valve",
    "ಚಿಟ್ಟೆ ವಾಲ್ವ್": "butterfly valve",
    
    # Pumps
    "ಸಬ್‌ಮರ್ಸಿಬಲ್ ಪಂಪ್": "submersible pump",
    "ಪಂಪ್": "pump",
    "ಪಂಪ್‌ಸೆಟ್": "pump set",
    
    # Units & Ratings
    "ಕೆವಿಎ": "kVA",
    "ಕೆವಿ": "kV",
    "ಕಿಲೋವ್ಯಾಟ್": "kW",
    "ಮಿಮೀ": "mm",
    "ಮೀಟರ್": "meter",
    "ಇಂಚು": "inch",
    "ಬಾರ್": "bar",
    "ಚದರ ಮಿಮೀ": "sq mm",
    
    # Materials
    "ಸಿಮೆಂಟ್": "cement",
    "ಪೋರ್ಟ್‌ಲ್ಯಾಂಡ್ ಸಿಮೆಂಟ್": "portland cement",
    "ಉಕ್ಕು": "steel",
    "ಕಬ್ಬಿಣ": "iron",
    "ಎರಕಹೊಯ್ದ ಕಬ್ಬಿಣ": "cast iron",
    "ತಾಮ್ರ": "copper",
    "ಅಲ್ಯೂಮಿನಿಯಂ": "aluminium",
    "ಟಿಎಂಟಿ ಬಾರ್": "TMT bar",
    
    # Scope / Action
    "ಸರಬರಾಜು": "supply",
    "ಅಳವಡಿಕೆ": "installation",
    "ಹಾಕುವುದು": "laying",
    "ಪರೀಕ್ಷೆ": "testing",
    "ಕಾರ್ಯಾರಂಭ": "commissioning",
}

# Tamil (Tamil script)
TAMIL_TECHNICAL_TERMS: Dict[str, str] = {
    # Transformers & Electrical
    "விநியோக மின்மாற்றி": "distribution transformer",
    "மின்மாற்றி": "transformer",
    "டிரான்ஸ்பார்மர்": "transformer",
    "மின்னழுத்தம்": "voltage",
    "மின்சாரம்": "electrical",
    "கேபிள்": "cable",
    "பூமிக்கடியில் கேபிள்": "underground cable",
    "எக்ஸ்எல்பிஇ": "XLPE",
    "பிவிசி": "PVC",
    "சுவிட்ச்கியர்": "switchgear",
    "மோட்டார்": "motor",
    
    # Pipes & Plumbing
    "சிபிவிசி": "CPVC",
    "குழாய்": "pipe",
    "குழாய்கள்": "pipes",
    "குடிநீர்": "drinking water",
    "நீர் விநியோகம்": "water supply",
    "ஜிஐ குழாய்": "GI pipe",
    "ஹெச்டிபிஇ": "HDPE",
    
    # Valves & Fittings
    "கேட் வால்வு": "gate valve",
    "வால்வு": "valve",
    "ஸ்லூயிஸ் வால்வு": "sluice valve",
    "செக் வால்வு": "check valve",
    "நான் ரிட்டர்ன் வால்வு": "non-return valve",
    "பட்டர்பிளை வால்வு": "butterfly valve",
    
    # Pumps
    "சப்மெர்சிபிள் பம்ப்": "submersible pump",
    "பம்ப்": "pump",
    "பம்ப் செட்": "pump set",
    
    # Units & Ratings
    "கேவிஏ": "kVA",
    "கேவி": "kV",
    "கிலோவாட்": "kW",
    "மிமீ": "mm",
    "மீட்டர்": "meter",
    "இன்ச்": "inch",
    "பார்": "bar",
    "சதுர மிமீ": "sq mm",
    
    # Materials
    "சிமெண்ட்": "cement",
    "போர்ட்லேண்ட் சிமெண்ட்": "portland cement",
    "எஃகு": "steel",
    "இரும்பு": "iron",
    "வார்ப்பிரும்பு": "cast iron",
    "செம்பு": "copper",
    "அலுமினியம்": "aluminium",
    "டிஎம்டி கம்பி": "TMT bar",
    
    # Scope / Action
    "வழங்கல்": "supply",
    "விநியோகம்": "supply",
    "பொருத்துதல்": "installation",
    "பதித்தல்": "laying",
    "சோதனை": "testing",
    "இயக்குதல்": "commissioning",
}

# Transliterated Indic words (Roman script) commonly mixed in tenders
TRANSLITERATED_TERMS: Dict[str, str] = {
    # Hindi romanized
    "sarabaraju": "supply",
    "puravike": "supply",
    "alavadike": "installation",
    "parikshe": "testing",
    "thevai": "required",
    "vazhangu": "supply",
    "poruthu": "install",
    "karna hai": "to be executed",
    "ki supply": "supply of",
    "ka supply": "supply of",
    "aur laying": "and laying",
    "tatha": "and",
    "sahit": "including",
    "anusaar": "as per",
    "anusar": "as per",
}

# Consolidated lookup table sorted by key length descending (for greedy prefix matching)
ALL_INDIC_TERMS: List[Tuple[str, str]] = sorted(
    [
        *HINDI_TECHNICAL_TERMS.items(),
        *KANNADA_TECHNICAL_TERMS.items(),
        *TAMIL_TECHNICAL_TERMS.items(),
        *TRANSLITERATED_TERMS.items(),
    ],
    key=lambda x: len(x[0]),
    reverse=True,
)


def normalize_with_lexicon(text: str) -> Tuple[str, float, int]:
    """Applies greedy dictionary replacement of Indic technical terms to English.

    Args:
        text: Raw input text.

    Returns:
        Tuple of:
        - normalized_text: String with recognized terms translated to English.
        - replacement_confidence: Estimated quality based on density of replaced terms.
        - hit_count: Number of technical terms mapped.
    """
    if not text:
        return text, 0.0, 0

    working_text = text
    hit_count = 0

    for indic_term, english_term in ALL_INDIC_TERMS:
        if indic_term in working_text:
            # Replace occurrences with boundaries where possible
            pattern = re.escape(indic_term)
            new_text, n = re.subn(pattern, english_term, working_text)
            if n > 0:
                working_text = new_text
                hit_count += n

    # Clean redundant whitespace
    working_text = re.sub(r"\s+", " ", working_text).strip()

    if hit_count == 0:
        return text, 0.0, 0

    # Calculate rough confidence: higher if multiple technical terms replaced
    conf = min(0.80, 0.40 + (0.10 * hit_count))
    return working_text, conf, hit_count
