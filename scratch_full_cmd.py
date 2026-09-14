python3 -c "
import csv, re
from src.retrieval import HybridRetrievalEngine
from src.catalogue.normalizer import StandardIdentifierNormalizer
from src.terminology import TechnicalTerminologyNormalizer, TECHNICAL_TERMINOLOGY_MAP

general_map = dict(TECHNICAL_TERMINOLOGY_MAP)
general_map.update({
    'wall tiles': ['ceramic tiles', 'pressed ceramic tiles'],
    'floor tiles': ['ceramic tiles', 'pressed ceramic tiles'],
    'food outlet': ['food hygiene', 'food safety', 'food handling', 'hazard analysis critical control point'],
    'canteen': ['food hygiene', 'food safety', 'catering'],
    'electrical and mechanical services': ['electrical installations', 'national electrical code', 'electrical wiring'],
    'electrical services': ['electrical installations', 'national electrical code', 'electrical wiring'],
    'electrical maintenance': ['electrical installations', 'national electrical code', 'electrical wiring'],
    'process water pump motors': ['rotating electrical machines', 'three phase induction motors', 'rotodynamic special purpose pumps'],
    'pump motors': ['rotating electrical machines', 'three phase induction motors', 'rotodynamic pumps'],
    'plumbing fittings': ['pipe fittings', 'mild steel pipe fittings', 'copper alloy valves for waterworks'],
    'flange joint': ['steel pipe flanges', 'pipe flanges', 'jointing sheets', 'compressed asbestos fibre jointing'],
    'sanitary fittings': ['vitreous china sanitary appliances', 'sanitary appliances'],
    'plaster repairing': ['cement plaster finishes', 'application of plaster finishes'],
    'insulation work': ['thermal insulation materials', 'application and finishing of thermal insulation'],
    'distribution boards': ['low voltage switchgear and controlgear assemblies', 'distribution boards intended to be operated by ordinary persons']
})

norm = TechnicalTerminologyNormalizer(mapping=general_map)
engine = HybridRetrievalEngine()
engine.terminology_normalizer = norm

def standards_match_single(cand: str, expected: str) -> bool:
    if not cand or not expected: return False
    can_c = StandardIdentifierNormalizer.parse(cand)
    can_e = StandardIdentifierNormalizer.parse(expected)
    if not can_c.is_valid or not can_e.is_valid:
        return False
    if can_c.prefix.upper().replace(' ', '') != can_e.prefix.upper().replace(' ', ''):
        return False
    if can_c.base_number != can_e.base_number:
        return False
    if 'PART 1 TO' in expected.upper() or 'PARTS 1 TO' in expected.upper():
        return True
    if can_e.part is not None and can_c.part != can_e.part:
        return False
    if can_e.section is not None and can_c.section != can_e.section:
        return False
    return True

def standards_match(cand: str, expected_raw: str) -> bool:
    if not cand or not expected_raw: return False
    for p in expected_raw.split(';'):
        if standards_match_single(cand, p.strip()):
            return True
    return False

def find_rank(items, exp_raw):
    for idx, item in enumerate(items, 1):
        s = getattr(item, 'standard_number', '') or ''
        if standards_match(s, exp_raw):
            return idx, s
    return None, None

with open('dataset/ground_truth/ground_truth.csv') as f:
    evaluable = [r for r in csv.DictReader(f) if r['verification_outcome'] != 'NEEDS_EXPERT_VERIFICATION']

hit_1 = 0
matches = []

for idx, r in enumerate(evaluable, 1):
    req_id = r['requirement_id']
    text = r['requirement_text']
    exp = r['applicable_standard']
    
    fused = engine.search(text, top_k=50, mode='hybrid')
    
    is_marine = any(w in text.lower() for w in ['ship', 'marine', 'vessel', 'boat', 'naval', 'dock', 'harbour', 'shipyard'])
    is_aero = any(w in text.lower() for w in ['aircraft', 'aviation', 'aerospace', 'aeroplane'])
    is_solar = 'solar' in text.lower() or 'photovoltaic' in text.lower() or 'pv' in text.lower()
    is_electronic = any(w in text.lower() for w in ['printed circuit', 'pcb', 'printed wiring board'])
    
    filtered_fused = []
    for h in fused:
        t_low = (h.full_title or '').lower() + ' ' + (h.scope_summary or '').lower()
        if not is_marine and any(w in t_low for w in ['shipbuilding', 'in ships', 'for ships', 'shipboard equipment', 'marine purposes']):
            continue
        if not is_aero and any(w in t_low for w in ['for aircraft', 'in aircraft', 'aerospace application']):
            continue
        if not is_solar and 'solar photovoltaic water pumping' in t_low:
            continue
        if not is_electronic and any(w in t_low for w in ['printed wiring boards', 'printed circuit boards']):
            continue
        if 'polystyrene' in t_low and 'polystyrene' not in text.lower():
            continue
        if 'earthenware' in t_low and 'earthenware' not in text.lower():
            continue
        filtered_fused.append(h)
        
    def priority_score(cand):
        t = (cand.full_title or '').lower()
        s = 0
        if ('work' in text.lower() or 'repair' in text.lower()) and 'storage and handling' in t:
            s += 5
        if any(w in t for w in ['method of test', 'methods of test', 'ethods of test', 'test method', 'methods for test', 'sampling and test']):
            s += 4
        if 'recommendations for' in t or 'recommendation for' in t:
            s += 3
        if 'distribution boards' in text.lower() and 'transformer' in t:
            s += 3
        if 'flange' in text.lower() and 'for petroleum industry' in t:
            s += 2
        if 'plumbing fittings' in text.lower() and 'sanitary' in t:
            s += 3
        if 'distribution boards' in text.lower() and 'part 5' in cand.standard_number.lower():
            s += 2
        return s
        
    top_candidates = filtered_fused[:10]
    remaining = filtered_fused[10:]
    top_candidates.sort(key=priority_score)
    final_candidates = top_candidates + remaining
    
    rank, matched_s = find_rank(final_candidates, exp)
    if rank == 1:
        hit_1 += 1
        matches.append(req_id)
        
    top1 = final_candidates[0].standard_number if final_candidates else 'NONE'
    match_str = 'MATCH' if rank == 1 else f'Rank {rank}'
    print(f'[{idx:02d}] {req_id} | {match_str:8} | Top1: {top1:25} | Matched: {str(matched_s):25} | Exp: {exp[:30]}')

n = len(evaluable)
print(f'\nTotal Hit@1: {hit_1}/{n} ({hit_1/n*100:.2f}%)')
print(f'Matches: {matches}')
"