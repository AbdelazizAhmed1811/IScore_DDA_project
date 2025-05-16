from app.schemas import AllUserDataResponse, ScoreComponent
from app.core.config import settings

def calculate_payment_history_score(data: AllUserDataResponse) -> float:
    if not data.derived_payment_history or data.derived_payment_history.total_due_payments == 0:
        return 0.0 
    
    history = data.derived_payment_history
    score = (history.on_time_payments / history.total_due_payments) * 100
    return round(score, 2)

def calculate_outstanding_debt_score(data: AllUserDataResponse) -> float:
    if not data.debt_info or data.debt_info.credit_limit == 0:
        return 0.0 # Or handle as an error/default
    utilization = data.debt_info.used_credit / data.debt_info.credit_limit
    score = (1 - utilization) * 100
    return round(max(0, score), 2) # Ensure score isn't negative if utilization > 1

def calculate_credit_history_age_score(data: AllUserDataResponse) -> float:
    if not data.history_info or settings.MAX_POSSIBLE_AGE_YEARS == 0:
        return 0.0
    score = (data.history_info.account_age_years / settings.MAX_POSSIBLE_AGE_YEARS) * 100
    return round(min(100, score), 2) # Cap at 100% if age > max_possible_age

def calculate_credit_mix_score(data: AllUserDataResponse) -> float:
    if not data.mix_info or settings.TOTAL_SYSTEM_CREDIT_TYPES == 0:
        return 0.0
    score = (data.mix_info.credit_types_used / settings.TOTAL_SYSTEM_CREDIT_TYPES) * 100
    return round(score, 2)

def calculate_final_iscore(user_data: AllUserDataResponse):
    components = []

    # 1. Payment History (35%)
    payment_raw = calculate_payment_history_score(user_data) # This function is now updated
    payment_weighted = payment_raw * 0.35
    # The 'value' for ScoreComponent might be the on_time_payments / total_due_payments ratio
    payment_metric_value = 0
    if user_data.derived_payment_history and user_data.derived_payment_history.total_due_payments > 0:
        payment_metric_value = user_data.derived_payment_history.on_time_payments / user_data.derived_payment_history.total_due_payments

    components.append(ScoreComponent(
        name="Payment History",
        value=payment_metric_value, # Ratio or raw counts, depending on what you want to show
        raw_score=payment_raw,
        weight=0.35,
        weighted_score=payment_weighted
    ))
    # 2. Outstanding Debt (30%)
    debt_raw = calculate_outstanding_debt_score(user_data)
    debt_weighted = debt_raw * 0.30
    components.append(ScoreComponent(name="Outstanding Debt", value=user_data.debt_info.used_credit / user_data.debt_info.credit_limit if user_data.debt_info and user_data.debt_info.credit_limit else 0, raw_score=debt_raw, weight=0.30, weighted_score=debt_weighted))

    # 3. Credit History Age (15%)
    history_raw = calculate_credit_history_age_score(user_data)
    history_weighted = history_raw * 0.15
    components.append(ScoreComponent(name="Credit History Age", value=user_data.history_info.account_age_years if user_data.history_info else 0, raw_score=history_raw, weight=0.15, weighted_score=history_weighted))

    # 4. Credit Mix (20%)
    mix_raw = calculate_credit_mix_score(user_data)
    mix_weighted = mix_raw * 0.20
    components.append(ScoreComponent(name="Credit Mix", value=user_data.mix_info.credit_types_used if user_data.mix_info else 0, raw_score=mix_raw, weight=0.20, weighted_score=mix_weighted))

    final_unscaled_score = sum(c.weighted_score for c in components)
    
    # Scale the score (e.g. 300-850)
    score_range = settings.SCORE_MAX - settings.SCORE_MIN
    scaled_score = settings.SCORE_MIN + (final_unscaled_score / 100) * score_range
    
    return {
        "components": components,
        "final_unscaled_score": round(final_unscaled_score, 2),
        "iscore": round(scaled_score, 2)
    }

