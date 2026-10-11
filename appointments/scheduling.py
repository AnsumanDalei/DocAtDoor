from datetime import datetime, time, timedelta

from django.utils import timezone

from .constants import BOOKING_HORIZON_DAYS, VISIT_DURATION
from .models import Appointment, AvailabilitySlot


def available_visit_times(doctor, visit_date):
    """Return open hourly visit starts for one doctor and local calendar date."""
    if doctor.doctor_approval_status != "approved" or not doctor.is_available:
        return []

    now = timezone.now()
    current_timezone = timezone.get_current_timezone()
    taken = Appointment.objects.filter(
        doctor=doctor,
        status__in=[Appointment.Status.PENDING, Appointment.Status.ACCEPTED],
        scheduled_at__gt=timezone.make_aware(datetime.combine(visit_date, time.min), current_timezone) - VISIT_DURATION,
        scheduled_at__lt=timezone.make_aware(datetime.combine(visit_date, time.max), current_timezone),
    ).values_list("scheduled_at", flat=True)
    busy = list(taken)
    options = set()

    for slot in AvailabilitySlot.objects.filter(doctor=doctor, weekday=visit_date.weekday()):
        cursor = datetime.combine(visit_date, slot.start_time)
        slot_end = datetime.combine(visit_date, slot.end_time)
        while cursor + VISIT_DURATION <= slot_end:
            candidate = timezone.make_aware(cursor, current_timezone)
            candidate_end = candidate + VISIT_DURATION
            has_overlap = any(start < candidate_end and start + VISIT_DURATION > candidate for start in busy)
            if candidate > now and not has_overlap:
                options.add(candidate)
            cursor += VISIT_DURATION

    return sorted(options)


def booking_date_is_valid(visit_date):
    today = timezone.localdate()
    return today <= visit_date <= today + timedelta(days=BOOKING_HORIZON_DAYS)
