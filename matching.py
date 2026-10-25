"""
CoMitra Weighted Scoring Partner Matching Algorithm
Computes partner suitability scores based on five standardized criteria:
1. Production Capacity (30%)
2. Machinery Compatibility (25%)
3. Quality Rating (20%)
4. Delivery Reliability (15%)
5. Location Suitability (10%)

Total Score = (Capacity * 0.30) + (Machinery * 0.25) + (Quality * 0.20) + (Delivery * 0.15) + (Location * 0.10)
"""

def is_machinery_compatible(req_machinery, business_machinery):
    req_clean = req_machinery.lower().strip()
    b_clean = business_machinery.lower().strip()
    
    if req_clean in b_clean or b_clean in req_clean:
        return True
        
    # Semantic token match (e.g. 'CNC Machine' matches '5-Axis CNC Milling & Turning Center')
    generic_words = {'machine', 'machines', 'press', 'presses', 'equipment', 'tool', 'tools', 'system', 'systems', 'center', 'centers'}
    req_tokens = [w for w in req_clean.replace('-', ' ').replace('/', ' ').split() if w not in generic_words and len(w) >= 2]
    b_tokens = [w for w in b_clean.replace('-', ' ').replace('/', ' ').split() if len(w) >= 2]
    
    # If any key term like 'cnc', 'lathe', 'milling', 'moulding' matches
    for t in req_tokens:
        if t in b_clean or any(t == bt for bt in b_tokens):
            return True
            
    return False

def match_partners_for_order(order, businesses):
    """
    Evaluates all businesses against the order requirements.
    Returns:
        ranked_partners: List of dicts for eligible partners sorted by score desc
        excluded_partners: List of dicts for ineligible partners with exclusion reasons
    """
    eligible = []
    excluded = []

    req_machinery = order['required_machinery']
    min_quality = float(order.get('min_quality_rating', 4.0))
    delivery_loc = order.get('delivery_location', '').lower().strip()
    total_qty = float(order['quantity'])

    for b in businesses:
        b_name = b['name']
        status = b.get('status', 'Active')
        avail_cap = float(b.get('available_capacity', 0))
        b_machinery = b.get('machinery', '')
        q_rating = float(b.get('quality_rating', 0.0))
        d_reliability = float(b.get('delivery_reliability', 4.0))
        b_loc = b.get('location', '').lower()

        # Check Exclusions
        if status.lower() != 'active':
            excluded.append({
                'business': b,
                'reason': 'Business profile is inactive.'
            })
            continue

        if avail_cap <= 0:
            excluded.append({
                'business': b,
                'reason': f'No available capacity ({int(avail_cap)} units available).'
            })
            continue

        if not is_machinery_compatible(req_machinery, b_machinery):
            excluded.append({
                'business': b,
                'reason': f'Incompatible machinery. Required: "{req_machinery}", Facility has: "{b_machinery}".'
            })
            continue

        if q_rating < min_quality:
            excluded.append({
                'business': b,
                'reason': f'Quality rating ({q_rating:.1f}/5.0) is below required minimum threshold ({min_quality:.1f}/5.0).'
            })
            continue

        # 1. Capacity Score (Weight: 30%)
        # Evaluates available capacity against order proportion (400 capacity out of 1000 is 40%, scaled to 100 capped)
        capacity_ratio = min(1.0, avail_cap / (total_qty * 0.40)) if total_qty > 0 else 1.0
        capacity_score = round(capacity_ratio * 100.0, 1)

        # 2. Machinery Score (Weight: 25%)
        machinery_score = 100.0

        # 3. Quality Score (Weight: 20%)
        quality_score = round((q_rating / 5.0) * 100.0, 1)

        # 4. Delivery Score (Weight: 15%)
        delivery_score = round((d_reliability / 5.0) * 100.0, 1)

        # 5. Location Score (Weight: 10%)
        if ('hyderabad' in b_loc and 'hyderabad' in delivery_loc) or ('secunderabad' in b_loc and 'secunderabad' in delivery_loc) or (b_loc == delivery_loc):
            location_score = 100.0
        elif any(loc in b_loc for loc in ['hyderabad', 'secunderabad', 'telangana', 'patancheru', 'jeedimetla', 'sanathnagar', 'balanagar']):
            location_score = 95.0
        else:
            location_score = 75.0

        # Weighted Total Score
        total_score = round(
            (capacity_score * 0.30) +
            (machinery_score * 0.25) +
            (quality_score * 0.20) +
            (delivery_score * 0.15) +
            (location_score * 0.10),
            1
        )

        est_days = max(3, round((min(avail_cap, total_qty) / 100) * 2))

        explanation = (
            f"Verified eligible partner: Has {int(avail_cap)} units available capacity, "
            f"certified {b['machinery']} capability, high {q_rating}/5.0 quality rating, "
            f"and prime industrial proximity in {b.get('location')}."
        )

        eligible.append({
            'business': b,
            'capacity_score': capacity_score,
            'machinery_score': machinery_score,
            'quality_score': quality_score,
            'delivery_score': delivery_score,
            'location_score': location_score,
            'total_score': total_score,
            'estimated_days': est_days,
            'explanation': explanation,
            'recommended_allocation': min(int(avail_cap), int(total_qty))
        })

    # Sort eligible partners descending by total score
    eligible.sort(key=lambda x: x['total_score'], reverse=True)

    return eligible, excluded
