from datetime import datetime, timedelta
from app.config import SLA_HOURS
from app.schemas import SLAStatusSchema

def get_category_sla_hours(category: str) -> int:
    return SLA_HOURS.get(category.lower(), 24)

def calculate_sla_info(created_at: datetime, sla_hours: int, current_status: str = "OPEN", resolution_time: datetime = None) -> SLAStatusSchema:
    deadline = created_at + timedelta(hours=sla_hours)
    reference_time = resolution_time if (current_status == "RESOLVED" and resolution_time) else datetime.utcnow()
    
    elapsed_seconds = (reference_time - created_at).total_seconds()
    hours_elapsed = round(max(0.0, elapsed_seconds / 3600.0), 2)
    
    remaining_seconds = (deadline - reference_time).total_seconds()
    hours_remaining = round(remaining_seconds / 3600.0, 2)
    
    is_breached = reference_time > deadline
    
    if is_breached:
        status = "Breached"
    elif hours_remaining <= (0.25 * sla_hours):
        status = "Near deadline"
    else:
        status = "On time"
        
    return SLAStatusSchema(
        status=status,
        hours_remaining=hours_remaining,
        hours_elapsed=hours_elapsed,
        total_sla_hours=sla_hours,
        deadline=deadline,
        is_breached=is_breached
    )
