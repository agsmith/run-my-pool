from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Any, Optional
import os
import logging

from app.models.event import Timeline, ProfileData
from app.services.api_service import APIService

logger = logging.getLogger(__name__)


class EventService:
    """Service for processing event-related business logic."""

    def __init__(self, api_service: APIService = None):
        self.api_service = api_service or APIService()

    def format_timeline_events(self, timeline_events: List[Timeline]) -> List[Dict[str, Any]]:
        """Format timeline events with display properties"""
        if not timeline_events:
            return []

        formatted_events = []
        for event in timeline_events:
            if not event.txn_time:
                continue

            dt = event.txn_time
            event_dict = event.dict()
            event_dict["_dt"] = dt

            # Format day with suffix
            day = dt.day
            if 4 <= day <= 20 or 24 <= day <= 30:
                suffix = "th"
            else:
                mod = day % 10
                if mod < 4 and mod > 0:
                    suffix = ["st", "nd", "rd"][mod - 1]
                else:
                    suffix = "th"

            # Add formatted date information
            event_dict["month_name"] = dt.strftime("%B %Y")
            event_dict["day_name"] = dt.strftime("%d")
            event_dict["day_with_suffix"] = f"{day}{suffix}"
            event_dict["time_only"] = dt.strftime("%H:%M")

            # Add visual properties
            color = "#b71c1c" if event.exception else "#1976d2"
            bg_color = "#ffebee" if event.exception else "#e3f2fd"
            op = event.operation or ""

            if op in ["ADD", "addSecurePI"]:
                display_label = "Tokenization"
                main_label = "Token"
            elif op in ["SUBMIT", "SubmitSecurePymt"]:
                display_label = "Payments"
                main_label = "Payment"
            elif event.exception:
                display_label = f"Exception: {op}"
                main_label = "Error"
            else:
                display_label = op
                main_label = op[:6] if op else "Event"

            event_dict["color"] = color
            event_dict["bg_color"] = bg_color
            event_dict["display_label"] = display_label
            event_dict["main_label"] = main_label

            formatted_events.append(event_dict)

        # Sort events by date, newest first
        formatted_events.sort(key=lambda x: x.get("_dt", datetime(1970, 1, 1)), reverse=True)
        return formatted_events

    def get_month_labels(self) -> List[Tuple[str, str]]:
        """Get labels for last 6 months"""
        now_dt = datetime.now().replace(day=1)
        return [(
            (now_dt - timedelta(days=30*i)).strftime("%b %Y"),
            (now_dt - timedelta(days=30*i)).strftime("%Y-%m")
        ) for i in reversed(range(6))]

    def extract_card_data(self, cards: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract structured data from profile cards"""
        result = {
            "channels": [],
            "token_tails": [],
            "instruments": [],
            "customer_ids": [],
            "billing_ids": [],
            "error_codes": [],
            "error_details": {},
            "fav_channel": None,
            "fav_instrument": None,
            "avg_amount": 0,
            "std_deviation": 0,
            "amount_count": 0,
            "total_events": 0,
            "failed_events": 0
        }

        if not cards:
            return result

        for card in cards:
            # Amount card
            if "amount" in card:
                amount_data = card["amount"]
                result["avg_amount"] = amount_data.get("avg_amt", 0)
                result["std_deviation"] = amount_data.get("std_dev", 0)

            # Billing arrangement IDs
            elif "baids" in card:
                result["billing_ids"] = card["baids"]

            # Channels
            elif "channels" in card:
                result["channels"] = card["channels"]

            # Customer IDs
            elif "cust_ids" in card:
                result["customer_ids"] = card["cust_ids"]

            # Errors
            elif "errors" in card:
                error_data = card["errors"]
                result["error_codes"] = list(error_data.keys())
                result["error_details"] = error_data

            # Instruments
            elif "instruments" in card:
                result["instruments"] = card["instruments"]

            # Favorite channel and instrument
            elif "favourite" in card:
                fav_data = card["favourite"]
                result["fav_channel"] = fav_data.get("channel")
                result["fav_instrument"] = fav_data.get("instrument")

            elif "transactions" in card:
                txn_details = card["transactions"]
                result["amount_count"] = txn_details.get("payment_txn")
                result["total_events"] = txn_details.get("total_txn")
                result["failed_events"] = txn_details.get("failed_txn")

            # Tokens
            elif "tokens" in card:
                result["token_tails"] = card["tokens"]

        return result

    def get_event_view_model(self, customer_id: Optional[str] = None,
                             billing_arrangement_id: Optional[str] = None,
                             view: str = "timeline", request=None) -> Dict[str, Any]:
        """Get event view model for the template"""
        result = {
            "customerId": customer_id or "",
            "billingArrangementID": billing_arrangement_id or "",
            "view": view,
            "error": None,
            "profile_data": None,
            "months": self.get_month_labels(),
            "active_section": "event"
        }

        if not (customer_id or billing_arrangement_id):
            return result

        try:
            # Get profile data from API
            profile_data = self.api_service.get_profile_data(
                customer_id,
                billing_arrangement_id
            )

            # Convert to Pydantic model
            profile_model = ProfileData(**profile_data)
            result["profile_data"] = profile_model

            # Extract data from cards - summary data is pre-calculated by API
            card_data = self.extract_card_data(profile_model.cards or [])
            result.update(card_data)

            # Format timeline events
            timeline_events = self.format_timeline_events(profile_model.timeline)

            # Sort and format for display
            result["sorted_events"] = timeline_events
            result["timeline_events"] = timeline_events
            result["activated"] = profile_model.activated or []

        except Exception as e:
            result["error"] = str(e)

        # Add request context data
        if request:
            username = request.cookies.get("username", "User")
            viewer_user = os.getenv("PFM_VIEWER_USERNAME")
            is_viewer = username == viewer_user

            git_commit = os.getenv("GIT_COMMIT", "-")
            if git_commit and len(git_commit) > 7:
                git_commit = git_commit[:7]

            result["username"] = username
            result["environment"] = os.getenv("ENV", "-")
            result["version"] = os.getenv("VERSION", "-")
            result["git_commit"] = git_commit
            result["is_viewer"] = is_viewer

        return result
        return result
