"""Deterministic Technical Procurement Lexicon for Offline Normalization Fallback.

Provides vocabulary and compound phrase mappings for Indian procurement terminology across:
- Hindi (Devanagari)
- Kannada (Kannada script)
- Tamil (Tamil script)
- Transliterated romanized procurement verbs/nouns (Hinglish, Kanglish, Tanglish)

CRITICAL ARCHITECTURAL CONSTRAINTS:
1. This module translates technical vocabulary ONLY (e.g., 'ವಿತರಣಾ ಪರಿವರ್ತಕ' -> 'distribution transformer').
2. This module NEVER maps products to Indian Standard (IS) numbers. Standard recommendation
   is strictly performed downstream by the authoritative StandardsRecommender.
3. Phrase matching is strictly executed BEFORE single-token matching to preserve technical semantics.
4. Technical units, ratings, dimensions, and abbreviations are normalized without mutating numeric values.
5. Exact boundary lookaround regex is used to handle Indic scripts with combining characters (matras).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Tuple, Union


# ==============================================================================
# 1. Technical Abbreviations, Units, and Material Acronyms (Lookaround Patterns)
# ==============================================================================
# Uses Unicode-aware negative lookaround (?<![a-zA-Z0-9\u0900-\u0D7F])TERM(?![a-zA-Z0-9\u0900-\u0D7F])
# instead of \b, which fails on Indic combining characters (matras, halants).
# Longer terms (e.g. kVA before kV, sq mm before mm) are strictly evaluated first.
TECHNICAL_UNIT_TERMS: List[Tuple[str, str]] = [
    # Power & Voltage
    ("केवीए", "kVA"),
    ("ಕೆವಿಎ", "kVA"),
    ("கேவிஏ", "kVA"),
    ("केवी", "kV"),
    ("ಕೆವಿ", "kV"),
    ("கேவி", "kV"),
    ("किलोवाट", "kW"),
    ("ಕಿಲೋವ್ಯಾಟ್", "kW"),
    ("கிலோவாட்", "kW"),
    ("एचपी", "HP"),
    ("ಎಚ್‌ಪಿ", "HP"),
    ("ಎಚ್.ಪಿ", "HP"),
    ("எச்பி", "HP"),

    # Dimensions & Area
    ("वर्ग मिमी", "sq mm"),
    ("वर्गमीमी", "sq mm"),
    ("स्क्वायर एमएम", "sq mm"),
    ("ಚದರ ಮಿಮೀ", "sq mm"),
    ("ವರ್ಗ ಮಿಮೀ", "sq mm"),
    ("ಸதுர மிமீ", "sq mm"),
    ("मिमी", "mm"),
    ("एमएम", "mm"),
    ("ಮಿಮೀ", "mm"),
    ("மிமீ", "mm"),
    ("मीटर", "meter"),
    ("ಮೀಟರ್", "meter"),
    ("மீட்டர்", "meter"),
    ("इंच", "inch"),
    ("ಇಂಚು", "inch"),
    ("இன்ச்", "inch"),

    # Pressure & Cable specs
    ("बार", "bar"),
    ("ಬಾರ್", "bar"),
    ("பார்", "bar"),
    ("पीएन", "PN"),
    ("ಪಿಎನ್", "PN"),
    ("பிஎன்", "PN"),
    ("कोर", "core"),
    ("ಕೋರ್", "core"),
    ("கோர்", "core"),

    # Materials in Indic scripts
    ("सीपीवीसी", "CPVC"),
    ("सिपिविसी", "CPVC"),
    ("ಸಿಪಿವಿಸಿ", "CPVC"),
    ("சிபிவیسی", "CPVC"),
    ("சிபிவிசி", "CPVC"),

    ("एक्सएलपीई", "XLPE"),
    ("ಎಕ್ಸ್‌ಎಲ್‌ಪಿಇ", "XLPE"),
    ("எக்ஸ்எல்பிஇ", "XLPE"),

    ("अनप्लास्टिकाइज्ड पीवीसी", "unplasticized PVC"),
    ("अनप्लास्टिकाइज्ड", "unplasticized"),
    ("पीवीसी", "PVC"),
    ("ಯುಪಿವಿಸಿ", "uPVC"),
    ("ಪಿವಿಸಿ", "PVC"),
    ("பிவிசி", "PVC"),
    ("ஹெச்டிபிஇ", "HDPE"),
    ("ಎಚ್‌ಡಿಪಿಇ", "HDPE"),

    ("जीआई", "GI"),
    ("ಜಿಐ", "GI"),
    ("ஜிஐ", "GI"),

    # Standards & Part references
    ("आईएस", "IS"),
    ("ಐಎಸ್", "IS"),
    ("ஐஎஸ்", "IS"),
    ("पार्ट", "Part"),
    ("ಭಾಗ", "Part"),
    ("பகுதி", "Part"),

    # Grades
    ("ग्रेड", "grade"),
    ("ಗ್ರೇಡ್", "grade"),
    ("தரம்", "grade"),
]

# Sort units by length descending so longer abbreviations match first
TECHNICAL_UNIT_TERMS.sort(key=lambda x: len(x[0]), reverse=True)

# Precompile regexes with Unicode lookarounds
COMPILED_UNIT_PATTERNS: List[Tuple[re.Pattern, str]] = []
for _term, _replacement in TECHNICAL_UNIT_TERMS:
    _escaped = re.escape(_term).replace(r"\ ", r"\s*")
    _pattern = re.compile(
        r"(?<![a-zA-Z0-9\u0900-\u0D7F])" + _escaped + r"(?![a-zA-Z0-9\u0900-\u0D7F])",
        re.IGNORECASE,
    )
    COMPILED_UNIT_PATTERNS.append((_pattern, _replacement))


# ==============================================================================
# 2. Multi-Word Compound Technical Phrases (Matched Greedy Longest-First)
# ==============================================================================
# Multi-word technical combinations covering products, engineering applications,
# materials, and procurement actions across Hindi, Kannada, Tamil, and Hinglish.
COMPOUND_TECHNICAL_PHRASES: List[Tuple[str, str]] = [
    # --- Hindi Multi-Word Phrases ---
    ("आउटडोर तेल निमज्जित वितरण ट्रांसफार्मर", "outdoor oil immersed distribution transformer"),
    ("तेल निमज्जित वितरण ट्रांसफार्मर", "oil immersed distribution transformer"),
    ("वितरण ट्रांसफार्मर", "distribution transformer"),
    ("पावर ट्रांसफार्मर", "power transformer"),
    ("तेल निमज्जित", "oil immersed"),
    ("एक्सएलपीई इंसुलेटेड भूमिगत केबल", "XLPE insulated underground cable"),
    ("इंसुलेटेड भूमिगत केबल", "insulated underground cable"),
    ("भूमिगत केबल", "underground cable"),
    ("की आपूर्ति और बिछाना", "supply and laying"),
    ("की आपूर्ति और स्थापना", "supply and installation"),
    ("पेयजल आपूर्ति के लिए", "for potable drinking water supply"),
    ("पीने के पानी के लिए", "for potable drinking water"),
    ("पेयजल आपूर्ति", "potable drinking water supply"),
    ("पेयजल", "potable drinking water"),
    ("जल कार्यों के लिए", "for water works"),
    ("जल कार्यों", "water works"),
    ("भूमिगत जल निकास के लिए", "for underground drainage and sewerage"),
    ("भूमिगत जल निकास", "underground drainage and sewerage"),
    ("अनप्लास्टिकाइज्ड पीवीसी पाइप", "unplasticized PVC pipe"),
    ("कास्ट आयरन स्लुइस वाल्व", "cast iron sluice valve"),
    ("स्लुइस वाल्व", "sluice valve"),
    ("गेट वाल्व", "gate valve"),
    ("चेक वाल्व", "check valve"),
    ("नॉन रिटर्न वाल्व", "non-return valve"),
    ("कास्ट आयरन", "cast iron"),
    ("कास्ट स्टील", "cast steel"),
    ("स्टेनलेस स्टील", "stainless steel"),
    ("हल्का स्टील", "mild steel"),
    ("कृषि जल आपूर्ति के लिए", "for agricultural water supply"),
    ("कृषि जल आपूर्ति", "agricultural water supply"),
    ("कृषि सिंचाई के लिए", "for agricultural irrigation"),
    ("सबमर्सिबल पंपसेट", "submersible pumpset"),
    ("सबमर्सिबल पंप", "submersible pump"),
    ("केन्द्रापसारक पंप", "centrifugal pump"),
    ("कंक्रीट सुदृढीकरण के लिए", "for concrete reinforcement"),
    ("कंक्रीट सुदृढीकरण", "concrete reinforcement"),
    ("संरचनात्मक कंक्रीट कार्य के लिए", "for structural concrete works"),
    ("संरचनात्मक कंक्रीट कार्य", "structural concrete works"),
    ("टीएमटी स्टील सरिया", "TMT steel reinforcement bar"),
    ("टीएमटी सरिया", "TMT steel bar"),
    ("स्टील सरिया", "steel reinforcement bar"),
    ("सरिया", "steel bar"),
    ("साधारण पोर्टलैंड सीमेंट", "ordinary portland cement"),
    ("पोर्टलैंड सीमेंट", "portland cement"),
    ("संरचनात्मक स्टील", "structural steel"),
    ("विद्युत केबल और वायरिंग", "electrical cable and wiring"),
    ("विद्युत केबल", "electrical cable"),
    ("के अनुसार", "conforming to"),
    ("की आपूर्ति", "supply"),
    ("का प्रावधान", "provision"),

    # --- Kannada Multi-Word Phrases ---
    ("ಹೊರಾಂಗಣ ತೈಲ ಮುಳುಗಿದ ವಿತರಣಾ ಪರಿವರ್ತಕ", "outdoor oil immersed distribution transformer"),
    ("ತೈಲ ಮುಳುಗಿದ ವಿತರಣಾ ಪರಿವರ್ತಕ", "oil immersed distribution transformer"),
    ("ಎಣ್ಣೆ ಮುಳುಗಿದ ವಿತರಣಾ ಪರಿವರ್ತಕ", "oil immersed distribution transformer"),
    ("ವಿತರಣಾ ಪರಿವರ್ತಕ", "distribution transformer"),
    ("ತೈಲ ಮುಳುಗಿದ", "oil immersed"),
    ("ಎಣ್ಣೆ ಮುಳುಗಿದ", "oil immersed"),
    ("ಹೊರಾಂಗಣ", "outdoor"),
    ("ಎಕ್ಸ್‌ಎಲ್‌ಪಿಇ ಭೂಗತ ಕೇಬಲ್", "XLPE underground cable"),
    ("ಭೂಗತ ಕೇಬಲ್", "underground cable"),
    ("ಕುಡಿಯುವ ನೀರು ಸರಬರಾಜಿಗಾಗಿ", "for potable drinking water supply"),
    ("ಕುಡಿಯುವ ನೀರು ಸರಬರಾಜಿಗೆ", "for potable drinking water supply"),
    ("ಕುಡಿಯುವ ನೀರು", "potable drinking water"),
    ("ನೀರು ಸರಬರಾಜು ಕಾರ್ಯಗಳಿಗಾಗಿ", "for water supply works"),
    ("ನೀರು ಸರಬರಾಜಿಗೆ", "for water supply"),
    ("ನೀರು ಸರಬರಾಜು", "water supply"),
    ("ಭೂಗತ ಒಳಚರಂಡಿಗಾಗಿ", "for underground drainage and sewerage"),
    ("ಭೂಗತ ಒಳಚರಂಡಿ", "underground drainage and sewerage"),
    ("ಕಟ್ಟಡ ನಿರ್ಮಾಣಕ್ಕಾಗಿ", "for building construction"),
    ("ಕಟ್ಟಡ ನಿರ್ಮಾಣಕ್ಕೆ", "for building construction"),
    ("ಕಟ್ಟಡ ನಿರ್ಮಾಣ", "building construction"),
    ("ಎರಕಹೊಯ್ದ ಕಬ್ಬಿಣದ ಸ್ಲೂಯಿಸ್ ವಾಲ್ವ್", "cast iron sluice valve"),
    ("ಎರಕಹೊಯ್ದ ಕಬ್ಬಿಣದ ಸ್ಲೂಯಿಸ್ ಕವಾಟ", "cast iron sluice valve"),
    ("ಎರಕಹೊಯ್ದ ಕಬ್ಬಿಣದ", "cast iron"),
    ("ಎರಕಹೊಯ್ದ ಕಬ್ಬಿಣ", "cast iron"),
    ("ಸ್ಲೂಯಿಸ್ ವಾಲ್ವ್", "sluice valve"),
    ("ಸ್ಲೂಯಿಸ್ ಕವಾಟ", "sluice valve"),
    ("ಗೇಟ್ ವಾಲ್ವ್", "gate valve"),
    ("ಚೆಕ್ ವಾಲ್ವ್", "check valve"),
    ("ನಾನ್ ರಿಟರ್ನ್ ವಾಲ್ವ್", "non-return valve"),
    ("ಚಿಟ್ಟೆ ವಾಲ್ವ್", "butterfly valve"),
    ("ಬೋರ್‌ವೆಲ್ ನೀರು ಸರಬರಾಜಿಗೆ", "for borewell water supply"),
    ("ಬೋರ್‌ವೆಲ್", "borewell"),
    ("ಸಬ್‌ಮರ್ಸಿಬಲ್ ಪಂಪ್‌ಸೆಟ್", "submersible pumpset"),
    ("ಸಬ್‌ಮರ್ಸಿಬಲ್ ಪಂಪ್", "submersible pump"),
    ("ಟಿಎಂಟಿ ಉಕ್ಕಿನ ಬಾರ್", "TMT steel bar"),
    ("ಉಕ್ಕಿನ ಬಾರ್", "steel bar"),
    ("ಸಾಮಾನ್ಯ ಪೋರ್ಟ್‌ಲ್ಯಾಂಡ್ ಸಿಮೆಂಟ್", "ordinary portland cement"),
    ("ಪೋರ್ಟ್‌ಲ್ಯಾಂಡ್ ಸಿಮೆಂಟ್", "portland cement"),
    ("ಸಿಪಿವಿಸಿ ಪೈಪ್‌ಗಳು", "CPVC pipes"),
    ("ಸಿಪಿವಿಸಿ ಪೈಪ್", "CPVC pipe"),
    ("ಪಿವಿಸಿ ಪೈಪ್‌ಗಳು", "PVC pipes"),
    ("ಪಿವಿಸಿ ಪೈಪ್", "PVC pipe"),
    ("ಪೈಪ್‌ಗಳು", "pipes"),
    ("ಪೈಪ್", "pipe"),
    ("ಕೊಳವೆ", "pipe"),
    ("ರ ಪ್ರಕಾರ", "conforming to"),
    ("ಸೂಕ್ತವಾದ ವಾಲ್ವ್‌ಗಳು ಮತ್ತು ಪೈಪ್‌ಗಳ ಪೂರೈಕೆ", "supply of suitable valves and pipes"),
    ("ಪೂರೈಕೆ", "supply"),

    # --- Tamil Multi-Word Phrases ---
    ("எண்ணெய் மூழ்கிய விநியோக மின்மாற்றி", "oil immersed distribution transformer"),
    ("விநியோக மின்மாற்றி", "distribution transformer"),
    ("எண்ணெய் மூழ்கிய", "oil immersed"),
    ("எக்ஸ்எல்பிஇ பூமிக்கடியில் கேபிள்", "XLPE underground cable"),
    ("பூமிக்கடியில் கேபிள்", "underground cable"),
    ("குடிநீர் விநியோகத்திற்கு", "for potable drinking water supply"),
    ("குடிநீர் விநியோகம்", "potable drinking water supply"),
    ("குடிநீர்", "potable drinking water"),
    ("நீர் விநியோகத்திற்கு", "for water supply"),
    ("நீர் விநியோகம்", "water supply"),
    ("நிலத்தடி வடிகாலுக்கு", "for underground drainage and sewerage"),
    ("நிலத்தடி வடிகால்", "underground drainage and sewerage"),
    ("கட்டுமான பணிக்காக", "for construction works"),
    ("கட்டுமான பணிக்கு", "for construction works"),
    ("கட்டுமான பணி", "construction works"),
    ("கான்கிரீட் பணிகளுக்கு", "for concrete works"),
    ("கான்கிரீட் பணி", "concrete works"),
    ("விவசாய பாசனத்திற்கு", "for agricultural irrigation"),
    ("விவசாய பாசனம்", "agricultural irrigation"),
    ("வார்ப்பிரும்பு ஸ்லூயிஸ் வால்வு", "cast iron sluice valve"),
    ("வார்ப்பிரும்பு", "cast iron"),
    ("ஸ்லூயிஸ் வால்வு", "sluice valve"),
    ("கேட் வால்வு", "gate valve"),
    ("செக் வால்வு", "check valve"),
    ("நான் ரிட்டர்ன் வால்வு", "non-return valve"),
    ("சப்மெர்சிபிள் பம்ப் செட்", "submersible pump set"),
    ("சப்மெர்சிபிள் பம்ப்", "submersible pump"),
    ("டிஎம்டி எஃகு கம்பி", "TMT steel bar"),
    ("எஃகு கம்பி", "steel bar"),
    ("சாதாரண போர்ட்லேண்ட் சிமெண்ட்", "ordinary portland cement"),
    ("போர்ட்லேண்ட் சிமெண்ட்", "portland cement"),
    ("சிபிவیسی குழாய்", "CPVC pipe"),
    ("சிபிவிசி குழாய்", "CPVC pipe"),
    ("பிவிசி குழாய்கள்", "PVC pipes"),
    ("பிவிசி குழாய்", "PVC pipe"),
    ("குழாய்கள்", "pipes"),
    ("குழாய்", "pipe"),
    ("பகுதி 2 இன் படி", "Part 2 conforming to"),
    ("இன் படி", "conforming to"),
    ("மின் வயரிங் மற்றும் பாதுகாப்பு சாதனங்கள் பொருத்துதல்", "installation of electrical wiring and safety equipment"),
    ("பாதுகாப்பு சாதனங்கள்", "safety equipment"),
    ("மின் வயரிங்", "electrical wiring"),

    # --- Transliterated / Romanized Multi-Word Phrases ---
    ("ki supply aur laying karna hai", "supply and laying to be executed"),
    ("supply aur laying karna hai", "supply and laying to be executed"),
    ("supply aur laying", "supply and laying"),
    ("aur laying", "and laying"),
    ("ki supply", "supply of"),
    ("ka supply", "supply of"),
    ("provide karna hoga", "provide to be executed"),
    ("supply karna hai", "supply to be executed"),
    ("supply karna", "supply to be executed"),
    ("supply madabekagide", "supply to be executed"),
    ("sarabaraju madabeku", "supply to be executed"),
    ("supply thevai for", "supply required for"),
    ("supply thevai vendum", "supply required"),
    ("thevai vendum", "required"),
    ("anusar hona chahiye", "conforming to requirement"),
    ("as per", "as per"),
    ("ke liye", "for"),
    ("bina kisi standard ke", "without any standard specification"),
    ("kuch bhi general samaan", "unspecified general goods"),
]


# ==============================================================================
# 3. Single-Token Technical Vocabulary
# ==============================================================================
SINGLE_TOKEN_TERMS: List[Tuple[str, str]] = [
    # Hindi single tokens
    ("ट्रांसफार्मर", "transformer"),
    ("केबल", "cable"),
    ("कंडक्टर", "conductor"),
    ("स्विचगियर", "switchgear"),
    ("सर्किट ब्रेकर", "circuit breaker"),
    ("मोटर", "motor"),
    ("पाइप", "pipe"),
    ("वाल्व", "valve"),
    ("पंप", "pump"),
    ("पंपसेट", "pumpset"),
    ("सीमेंट", "cement"),
    ("स्टील", "steel"),
    ("इस्पात", "steel"),
    ("तांबा", "copper"),
    ("एल्युमिनियम", "aluminium"),
    ("जस्ती", "galvanized"),
    ("गैल्वनाइज्ड", "galvanized"),
    ("आपूर्ति", "supply"),
    ("बिछाने", "laying"),
    ("बिछाना", "laying"),
    ("स्थापना", "installation"),
    ("परीक्षण", "testing"),

    # Kannada single tokens
    ("ಟ್ರಾನ್ಸ್‌ಫಾರ್ಮರ್", "transformer"),
    ("ಟ್ರಾನ್ಸ್ಫಾರ್ಮರ್", "transformer"),
    ("ಕೇಬಲ್", "cable"),
    ("ವಾಹಕ", "conductor"),
    ("ಸ್ವಿಚ್‌ಗೇರ್", "switchgear"),
    ("ಮೋಟರ್", "motor"),
    ("ಪೈಪ್", "pipe"),
    ("ವಾಲ್ವ್", "valve"),
    ("ಕವಾಟ", "valve"),
    ("ಪಂಪ್", "pump"),
    ("ಪಂಪ್‌ಸೆಟ್", "pumpset"),
    ("ಸಿಮೆಂಟ್", "cement"),
    ("ಉಕ್ಕು", "steel"),
    ("ಕಬ್ಬಿಣ", "iron"),
    ("ತಾಮ್ರ", "copper"),
    ("ಅಲ್ಯೂಮಿನಿಯಂ", "aluminium"),
    ("ಸರಬರಾಜು", "supply"),
    ("ಅಳವಡಿಕೆ", "installation"),
    ("ಹಾಕುವುದು", "laying"),
    ("ಪರೀಕ್ಷೆ", "testing"),

    # Tamil single tokens
    ("மின்மாற்றி", "transformer"),
    ("டிரான்ஸ்பார்மர்", "transformer"),
    ("கேபிள்", "cable"),
    ("சுவிட்ச்கியர்", "switchgear"),
    ("மோட்டார்", "motor"),
    ("குழாய்", "pipe"),
    ("வால்வு", "valve"),
    ("பம்ப்", "pump"),
    ("சிமெண்ட்", "cement"),
    ("எஃகு", "steel"),
    ("இரும்பு", "iron"),
    ("செம்பு", "copper"),
    ("அலுமினியம்", "aluminium"),
    ("வழங்கல்", "supply"),
    ("விநியோகம்", "supply"),
    ("பொருத்துதல்", "installation"),
    ("பதித்தல்", "laying"),
    ("சோதனை", "testing"),

    # Transliterated single tokens
    ("sarabaraju", "supply"),
    ("puravike", "supply"),
    ("alavadike", "installation"),
    ("thevai", "required"),
    ("vendum", "required"),
    ("vazhangu", "supply"),
    ("poruthu", "install"),
    ("karna", "execute"),
    ("chahiye", "required"),
    ("hoga", "to be"),
    ("hogi", "to be"),
    ("tatha", "and"),
    ("aur", "and"),
    ("sahit", "including"),
    ("anusaar", "as per"),
    ("anusar", "as per"),
    ("madabeku", "execute"),
    ("madabekagide", "to be executed"),
    ("beku", "required"),
    ("matthu", "and"),
    ("matrum", "and"),
]


# Sort compounds and single tokens strictly by length descending for greedy longest-first matching
COMPOUND_TECHNICAL_PHRASES = sorted(COMPOUND_TECHNICAL_PHRASES, key=lambda x: len(x[0]), reverse=True)
SINGLE_TOKEN_TERMS = sorted(SINGLE_TOKEN_TERMS, key=lambda x: len(x[0]), reverse=True)


def normalize_with_lexicon(
    text: str,
    return_details: bool = False,
) -> Union[Tuple[str, float, int], Tuple[str, float, int, Dict[str, Any]]]:
    """Applies structured multi-phase technical lexicon normalization.

    Execution Pipeline:
    Phase 1: Technical Abbreviations & Units (e.g., '11 केवी' -> '11 kV', '250 ಚದರ ಮಿಮೀ' -> '250 sq mm')
    Phase 2: Compound Technical Phrases (e.g., 'ಸ್ಲೂಯಿಸ್ ಕವಾಟ' -> 'sluice valve')
    Phase 3: Single-Token Technical Terms (e.g., 'ಕೇಬಲ್' -> 'cable')
    Phase 4: Syntactic connectors & whitespace cleanup

    Args:
        text: Raw input procurement requirement string.
        return_details: If True, returns a 4-tuple including diagnostic details. Default False.

    Returns:
        If return_details is False:
            (normalized_text, confidence, hit_count)
        If return_details is True:
            (normalized_text, confidence, hit_count, details)
    """
    if not text or not text.strip():
        empty_details = {"unit_hits": 0, "phrase_hits": 0, "token_hits": 0, "indic_residue": 0}
        return (text, 0.0, 0, empty_details) if return_details else (text, 0.0, 0)

    working_text = unicodedata.normalize("NFKC", text.strip())
    hit_count = 0
    unit_hits = 0
    phrase_hits = 0
    token_hits = 0

    # Phase 1: Technical Abbreviations and Units (Precompiled lookaround regexes)
    for pattern, replacement in COMPILED_UNIT_PATTERNS:
        new_text, n = pattern.subn(replacement, working_text)
        if n > 0:
            working_text = new_text
            hit_count += n
            unit_hits += n

    # Phase 2: Compound Technical Phrases (Longest-first greedy string replacement)
    for indic_phrase, english_phrase in COMPOUND_TECHNICAL_PHRASES:
        if indic_phrase in working_text:
            new_text = working_text.replace(indic_phrase, english_phrase)
            if new_text != working_text:
                n = (len(working_text) - len(new_text.replace(english_phrase, ""))) // max(1, len(english_phrase))
                working_text = new_text
                hit_count += max(1, n)
                phrase_hits += max(1, n)

    # Phase 3: Single-Token Technical Terms
    for indic_term, english_term in SINGLE_TOKEN_TERMS:
        if indic_term in working_text:
            # If term is in Latin script, use word boundaries
            if re.match(r"^[a-zA-Z]+$", indic_term):
                new_text, n = re.subn(r"\b" + re.escape(indic_term) + r"\b", english_term, working_text, flags=re.IGNORECASE)
            else:
                new_text = working_text.replace(indic_term, english_term)
                n = 1 if new_text != working_text else 0
            if n > 0:
                working_text = new_text
                hit_count += n
                token_hits += n

    # Phase 4: Clean grammatical connectors (e.g. isolated Hindi 'के', 'का', 'की')
    working_text = re.sub(
        r"(?<![a-zA-Z0-9\u0900-\u0D7F])(?:के|का|की)(?![a-zA-Z0-9\u0900-\u0D7F])",
        "of",
        working_text,
    )
    working_text = re.sub(r"\s+", " ", working_text).strip()
    working_text = re.sub(r"\s+([,.:;])", r"\1", working_text)

    # Check remaining Indic characters
    indic_chars_left = [ch for ch in working_text if 0x0900 <= ord(ch) <= 0x0D7F and ch.isalpha()]
    total_alpha = [ch for ch in working_text if ch.isalpha()]

    # Quality and confidence scoring
    if hit_count == 0:
        details = {"unit_hits": 0, "phrase_hits": 0, "token_hits": 0, "indic_residue": len(indic_chars_left)}
        return (text, 0.0, 0, details) if return_details else (text, 0.0, 0)

    # High confidence if compound phrases matched and zero Indic characters remain
    if len(indic_chars_left) == 0:
        conf = min(0.92, 0.70 + (0.04 * phrase_hits) + (0.02 * unit_hits))
    else:
        residue_ratio = len(indic_chars_left) / max(1, len(total_alpha))
        conf = max(0.35, 0.75 - (0.50 * residue_ratio))

    details = {
        "unit_hits": unit_hits,
        "phrase_hits": phrase_hits,
        "token_hits": token_hits,
        "indic_residue": len(indic_chars_left),
    }

    if return_details:
        return working_text, conf, hit_count, details
    return working_text, conf, hit_count
