from __future__ import annotations

from datetime import datetime, time, timedelta
from app.services.rules.engine import Rule, RuleEvaluationReport, RuleResult
from app.services.search.state import EventSpec, TimeSlot, VenueSpec


# ==========================================
# HARD RULES
# ==========================================

class CapacityRule:
    rule_id = "HARD_01_CAPACITY"
    rule_name = "Venue Capacity Constraint"
    is_hard = True

    def evaluate(
        self,
        event: EventSpec,
        venue: VenueSpec,
        existing_bookings: list[tuple[int, TimeSlot]],
    ) -> RuleResult:
        if venue.capacity >= event.attendees:
            return RuleResult(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                is_hard=True,
                passed=True,
                message=f"Venue capacity ({venue.capacity}) accommodates {event.attendees} attendees.",
            )
        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            is_hard=True,
            passed=False,
            message=(
                f"Capacity violation: Venue capacity ({venue.capacity}) is smaller "
                f"than required attendees ({event.attendees}). Deficit: {event.attendees - venue.capacity} seats."
            ),
        )


class FacilityRule:
    rule_id = "HARD_02_FACILITIES"
    rule_name = "Required Facilities Constraint"
    is_hard = True

    def evaluate(
        self,
        event: EventSpec,
        venue: VenueSpec,
        existing_bookings: list[tuple[int, TimeSlot]],
    ) -> RuleResult:
        missing = event.required_facilities - venue.facilities
        if not missing:
            return RuleResult(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                is_hard=True,
                passed=True,
                message=f"All required facilities ({', '.join(event.required_facilities) or 'none'}) available.",
            )
        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            is_hard=True,
            passed=False,
            message=f"Missing required facilities: {', '.join(sorted(missing))}.",
        )


class OperatingHoursRule:
    rule_id = "HARD_03_HOURS"
    rule_name = "Venue Operating Hours Constraint"
    is_hard = True

    def evaluate(
        self,
        event: EventSpec,
        venue: VenueSpec,
        existing_bookings: list[tuple[int, TimeSlot]],
    ) -> RuleResult:
        start_t = event.start_time.time()
        end_t = event.end_time.time()
        if start_t >= venue.open_time and end_t <= venue.close_time:
            return RuleResult(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                is_hard=True,
                passed=True,
                message=f"Event time ({start_t.strftime('%H:%M')} - {end_t.strftime('%H:%M')}) is within venue operating hours ({venue.open_time.strftime('%H:%M')} - {venue.close_time.strftime('%H:%M')}).",
            )
        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            is_hard=True,
            passed=False,
            message=f"Operating hours violation: Event time ({start_t.strftime('%H:%M')}-{end_t.strftime('%H:%M')}) exceeds venue hours ({venue.open_time.strftime('%H:%M')}-{venue.close_time.strftime('%H:%M')}).",
        )


class BookingCollisionRule:
    rule_id = "HARD_04_COLLISION"
    rule_name = "Schedule Collision & Buffer Constraint"
    is_hard = True

    def evaluate(
        self,
        event: EventSpec,
        venue: VenueSpec,
        existing_bookings: list[tuple[int, TimeSlot]],
    ) -> RuleResult:
        conflicting = [
            slot for vid, slot in existing_bookings
            if vid == venue.id and slot.overlaps(event.slot, buffer_minutes=event.setup_buffer_minutes)
        ]
        if not conflicting:
            return RuleResult(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                is_hard=True,
                passed=True,
                message=f"No time conflict found. Includes {event.setup_buffer_minutes}-minute setup/teardown buffer.",
            )
        times_str = ", ".join(f"{s.start_time.strftime('%H:%M')}-{s.end_time.strftime('%H:%M')}" for s in conflicting)
        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            is_hard=True,
            passed=False,
            message=f"Booking collision: Venue has overlapping active booking(s) at {times_str} (considering {event.setup_buffer_minutes}m buffer).",
        )


class VenueTypeRule:
    rule_id = "HARD_05_TYPE"
    rule_name = "Venue Type Compatibility"
    is_hard = True

    def evaluate(
        self,
        event: EventSpec,
        venue: VenueSpec,
        existing_bookings: list[tuple[int, TimeSlot]],
    ) -> RuleResult:
        if not event.preferred_venue_type or venue.venue_type == event.preferred_venue_type:
            return RuleResult(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                is_hard=True,
                passed=True,
                message=f"Venue type '{venue.venue_type}' satisfies preference.",
            )
        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            is_hard=True,
            passed=False,
            message=f"Venue type mismatch: Event requested '{event.preferred_venue_type}', but venue is '{venue.venue_type}'.",
        )


# ==========================================
# SOFT POLICY & COMPLIANCE RULES
# ==========================================

class NoisePolicyRule:
    rule_id = "SOFT_01_NOISE"
    rule_name = "Campus Noise & Quiet Hours Policy"
    is_hard = False

    def evaluate(
        self,
        event: EventSpec,
        venue: VenueSpec,
        existing_bookings: list[tuple[int, TimeSlot]],
    ) -> RuleResult:
        # High noise (concerts, loud speakers) after 20:00 or in quiet zones
        night_cutoff = time(20, 0)
        is_late = event.end_time.time() > night_cutoff
        
        if event.noise_level == "high" and not venue.noise_allowed:
            return RuleResult(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                is_hard=False,
                passed=False,
                message=f"High noise level requested in '{venue.name}', which is designated a low-noise zone.",
                score_deduction=25.0,
            )
        if event.noise_level == "high" and is_late:
            return RuleResult(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                is_hard=False,
                passed=False,
                message=f"Campus quiet hours start at 20:00. Event ends at {event.end_time.strftime('%H:%M')} with high noise.",
                score_deduction=20.0,
            )
        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            is_hard=False,
            passed=True,
            message="Complies with campus acoustic & quiet hours policy.",
        )


class CateringPolicyRule:
    rule_id = "SOFT_02_CATERING"
    rule_name = "Food & Catering Cleanliness Policy"
    is_hard = False

    def evaluate(
        self,
        event: EventSpec,
        venue: VenueSpec,
        existing_bookings: list[tuple[int, TimeSlot]],
    ) -> RuleResult:
        if not event.requires_catering:
            return RuleResult(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                is_hard=False,
                passed=True,
                message="No catering required.",
            )

        if not venue.catering_allowed:
            return RuleResult(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                is_hard=False,
                passed=False,
                message=f"Catering requested, but food and beverages are prohibited in '{venue.name}' (e.g. computer labs / auditoriums).",
                score_deduction=30.0,
            )

        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            is_hard=False,
            passed=True,
            message="Catering is permitted in this venue. Mandatory cleanup deposit applies.",
        )


class SecurityAndCrowdRule:
    rule_id = "SOFT_03_SECURITY"
    rule_name = "Crowd Management & Security Rule"
    is_hard = False

    def evaluate(
        self,
        event: EventSpec,
        venue: VenueSpec,
        existing_bookings: list[tuple[int, TimeSlot]],
    ) -> RuleResult:
        if event.attendees >= 500:
            return RuleResult(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                is_hard=False,
                passed=True,
                message=f"Large gathering ({event.attendees} attendees): Requires mandatory campus security deployment and EMT standby.",
                score_deduction=5.0,  # Small flag to highlight logistical requirement
            )
        elif event.attendees >= 200:
            return RuleResult(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                is_hard=False,
                passed=True,
                message=f"Medium gathering ({event.attendees} attendees): Requires university security staff notification.",
            )
        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            is_hard=False,
            passed=True,
            message="Standard crowd size. No specialized security clearance needed.",
        )


class CapacityEfficiencyRule:
    rule_id = "SOFT_04_EFFICIENCY"
    rule_name = "Venue Capacity Utilization Efficiency"
    is_hard = False

    def evaluate(
        self,
        event: EventSpec,
        venue: VenueSpec,
        existing_bookings: list[tuple[int, TimeSlot]],
    ) -> RuleResult:
        if venue.capacity < event.attendees:
            return RuleResult(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                is_hard=False,
                passed=False,
                message="Venue capacity too small.",
                score_deduction=50.0,
            )
        utilization = (event.attendees / venue.capacity) * 100.0
        if utilization < 25.0 and venue.capacity >= 200:
            return RuleResult(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                is_hard=False,
                passed=False,
                message=f"Low space utilization: Event fills only {utilization:.1f}% of {venue.name} ({venue.capacity} seats for {event.attendees} attendees).",
                score_deduction=15.0,
            )
        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            is_hard=False,
            passed=True,
            message=f"Good space utilization: {utilization:.1f}%.",
        )


# ==========================================
# RULE ENGINE FACADE
# ==========================================

class VenueRuleEngine:
    """Evaluates all venue hard and soft rules for an event allocation."""

    def __init__(self, custom_rules: list[Rule] | None = None):
        if custom_rules is not None:
            self.rules = custom_rules
        else:
            self.rules = [
                CapacityRule(),
                FacilityRule(),
                OperatingHoursRule(),
                BookingCollisionRule(),
                VenueTypeRule(),
                NoisePolicyRule(),
                CateringPolicyRule(),
                SecurityAndCrowdRule(),
                CapacityEfficiencyRule(),
            ]

    def evaluate(
        self,
        event: EventSpec,
        venue: VenueSpec,
        existing_bookings: list[tuple[int, TimeSlot]] | None = None,
    ) -> RuleEvaluationReport:
        bookings = existing_bookings or []
        hard_violations: list[str] = []
        soft_warnings: list[str] = []
        passed_rules: list[str] = []
        recommendations: list[str] = []
        details: list[RuleResult] = []

        compliance_score = 100.0

        for rule in self.rules:
            result = rule.evaluate(event, venue, bookings)
            details.append(result)

            if rule.is_hard:
                if not result.passed:
                    hard_violations.append(result.message)
                else:
                    passed_rules.append(result.message)
            else:
                if not result.passed:
                    soft_warnings.append(result.message)
                    compliance_score -= result.score_deduction
                else:
                    passed_rules.append(result.message)

        # Generate actionable recommendations
        if hard_violations:
            recommendations.append("Consider alternative venues or shift the requested time window.")
        if any("Catering requested" in w for w in soft_warnings):
            recommendations.append("Apply for a catering exemption or switch to a dining-approved hall.")
        if any("quiet hours" in w or "low-noise zone" in w for w in soft_warnings):
            recommendations.append("Reduce sound amplification or conclude the event before 20:00.")
        if any("security" in p.lower() for p in passed_rules if "mandatory" in p.lower()):
            recommendations.append("Submit Event Security Form to Campus Police at least 72h prior.")

        compliance_score = max(0.0, min(100.0, compliance_score))
        is_feasible = (len(hard_violations) == 0)

        return RuleEvaluationReport(
            venue_id=venue.id,
            venue_name=venue.name,
            event_id=event.id,
            event_name=event.name,
            is_feasible=is_feasible,
            overall_compliance_score=round(compliance_score, 1),
            hard_violations=hard_violations,
            soft_warnings=soft_warnings,
            passed_rules=passed_rules,
            recommendations=recommendations,
            details=details,
        )

