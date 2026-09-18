"""
Autonomous Travel & Reservations Booking Agent (ZeroKey).
Uses 100% in-memory data structures (NO external database required).
Equipped with real travel booking tools (search flights, search hotels, create/view/cancel reservations),
a personalized Concierge persona, and multi-turn autonomous tool execution loops.

Usage:
    python tests/real_agent.py
    python tests/real_agent.py "Find flights from New York to London and book a 4-star hotel in London for John Doe"
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import json
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional

# Ensure root workspace is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openai import OpenAI
from config.settings import settings
from config.logger import get_logger

logger = get_logger("booking_agent")

BASE_URL = f"http://{settings.HOST}:{settings.PORT}/v1"

# -------------------------------------------------------------
# 1. IN-MEMORY TRAVEL CATALOG & STATE (NO DATABASE)
# -------------------------------------------------------------

FLIGHTS_CATALOG = [
    {
        "flight_id": "FL-101",
        "airline": "Skyline Airways",
        "origin": "New York (JFK)",
        "destination": "London (LHR)",
        "departure": "08:30 AM",
        "arrival": "08:45 PM",
        "price_usd": 520,
        "available_seats": 5
    },
    {
        "flight_id": "FL-102",
        "airline": "Global Jet",
        "origin": "New York (JFK)",
        "destination": "London (LHR)",
        "departure": "06:15 PM",
        "arrival": "06:30 AM (+1)",
        "price_usd": 480,
        "available_seats": 12
    },
    {
        "flight_id": "FL-205",
        "airline": "Pacific Express",
        "origin": "San Francisco (SFO)",
        "destination": "Tokyo (HND)",
        "departure": "11:00 AM",
        "arrival": "03:15 PM (+1)",
        "price_usd": 890,
        "available_seats": 6
    },
    {
        "flight_id": "FL-310",
        "airline": "EuroWings",
        "origin": "London (LHR)",
        "destination": "Paris (CDG)",
        "departure": "02:45 PM",
        "arrival": "04:55 PM",
        "price_usd": 140,
        "available_seats": 18
    },
    {
        "flight_id": "FL-408",
        "airline": "IndiAir",
        "origin": "Delhi (DEL)",
        "destination": "Dubai (DXB)",
        "departure": "09:20 PM",
        "arrival": "11:45 PM",
        "price_usd": 290,
        "available_seats": 8
    }
]

HOTELS_CATALOG = [
    {
        "hotel_id": "HT-10",
        "name": "The Savoy Palace",
        "city": "London",
        "category": "5-Star Luxury",
        "price_per_night_usd": 310,
        "amenities": ["Complimentary Breakfast", "Spa & Wellness", "High-speed WiFi"],
        "available_rooms": 3
    },
    {
        "hotel_id": "HT-11",
        "name": "Covent Garden Boutique Hotel",
        "city": "London",
        "category": "4-Star Modern",
        "price_per_night_usd": 185,
        "amenities": ["Fitness Center", "High-speed WiFi", "Central Location"],
        "available_rooms": 7
    },
    {
        "hotel_id": "HT-20",
        "name": "Shibuya Sky Tower Hotel",
        "city": "Tokyo",
        "category": "4.5-Star Panoramic",
        "price_per_night_usd": 220,
        "amenities": ["City View", "Direct Metro Access", "Rooftop Lounge"],
        "available_rooms": 5
    },
    {
        "hotel_id": "HT-30",
        "name": "Eiffel Grandview Hotel",
        "city": "Paris",
        "category": "4-Star Classic",
        "price_per_night_usd": 260,
        "amenities": ["Balcony Views", "French Bistro", "WiFi"],
        "available_rooms": 4
    },
    {
        "hotel_id": "HT-40",
        "name": "Downtown Palm Suites",
        "city": "Dubai",
        "category": "5-Star Resort",
        "price_per_night_usd": 295,
        "amenities": ["Infinity Pool", "Private Beach", "Butler Service"],
        "available_rooms": 8
    }
]

# In-memory store for active bookings (persisted in RAM during session)
ACTIVE_BOOKINGS: Dict[str, Dict[str, Any]] = {}

# -------------------------------------------------------------
# 2. BOOKING TOOL FUNCTIONS (Python Execution)
# -------------------------------------------------------------

def search_flights(origin: str, destination: str) -> Dict[str, Any]:
    """Search for available flights between two cities or airports."""
    logger.info("Tool executed: search_flights", origin=origin, destination=destination)
    orig_clean = origin.lower().strip()
    dest_clean = destination.lower().strip()

    matches = []
    for f in FLIGHTS_CATALOG:
        match_orig = any(term in f["origin"].lower() for term in orig_clean.split())
        match_dest = any(term in f["destination"].lower() for term in dest_clean.split())
        if match_orig and match_dest:
            matches.append(f)

    if not matches:
        logger.warning("No direct flight match found", origin=origin, destination=destination)
        return {
            "status": "no_direct_match",
            "message": f"No direct flights found for {origin} -> {destination}. Here are our popular active routes:",
            "available_routes": FLIGHTS_CATALOG
        }

    logger.info("Flights search results", count=len(matches), flight_ids=[f["flight_id"] for f in matches])
    return {
        "status": "success",
        "count": len(matches),
        "flights": matches
    }

def search_hotels(city: str) -> Dict[str, Any]:
    """Search for available hotels in a given city."""
    logger.info("Tool executed: search_hotels", city=city)
    city_clean = city.lower().strip()

    matches = [h for h in HOTELS_CATALOG if city_clean in h["city"].lower()]
    if not matches:
        logger.warning("No hotels found in city", city=city)
        return {
            "status": "no_city_match",
            "message": f"No registered hotels found in {city}. Available destinations:",
            "properties": HOTELS_CATALOG
        }

    logger.info("Hotels search results", count=len(matches), hotel_names=[h["name"] for h in matches])
    return {
        "status": "success",
        "count": len(matches),
        "hotels": matches
    }

def book_flight(flight_id: str, passenger_name: str, seat_class: str = "Economy") -> Dict[str, Any]:
    """Books a flight and issues a confirmed reservation reference."""
    logger.info("Tool executed: book_flight", flight_id=flight_id, passenger=passenger_name, seat_class=seat_class)
    flight = next((f for f in FLIGHTS_CATALOG if f["flight_id"].upper() == flight_id.upper()), None)
    if not flight:
        logger.error("Flight booking failed: ID not found", flight_id=flight_id)
        return {"status": "error", "message": f"Flight ID '{flight_id}' not found in catalog."}

    if flight["available_seats"] <= 0:
        logger.error("Flight booking failed: Sold out", flight_id=flight_id)
        return {"status": "error", "message": f"Flight {flight_id} is completely sold out."}

    # Decrement in-memory seats
    flight["available_seats"] -= 1

    booking_ref = f"BK-FL-{uuid.uuid4().hex[:6].upper()}"
    reservation = {
        "booking_type": "flight",
        "booking_reference": booking_ref,
        "passenger_name": passenger_name,
        "flight_id": flight["flight_id"],
        "airline": flight["airline"],
        "route": f"{flight['origin']} -> {flight['destination']}",
        "departure": flight["departure"],
        "seat_class": seat_class,
        "total_cost_usd": flight["price_usd"],
        "status": "CONFIRMED"
    }

    ACTIVE_BOOKINGS[booking_ref] = reservation
    logger.info("Flight booked successfully", booking_ref=booking_ref, total_cost_usd=flight["price_usd"])
    return {"status": "success", "reservation": reservation}

def book_hotel(hotel_id: str, guest_name: str, nights: int = 1) -> Dict[str, Any]:
    """Books a hotel room and issues a confirmed reservation reference."""
    logger.info("Tool executed: book_hotel", hotel_id=hotel_id, guest=guest_name, nights=nights)
    hotel = next((h for h in HOTELS_CATALOG if h["hotel_id"].upper() == hotel_id.upper()), None)
    if not hotel:
        logger.error("Hotel booking failed: ID not found", hotel_id=hotel_id)
        return {"status": "error", "message": f"Hotel ID '{hotel_id}' not found in catalog."}

    if hotel["available_rooms"] <= 0:
        logger.error("Hotel booking failed: No rooms available", hotel_id=hotel_id)
        return {"status": "error", "message": f"Hotel {hotel['name']} has no remaining rooms."}

    hotel["available_rooms"] -= 1
    total_cost = hotel["price_per_night_usd"] * max(1, nights)

    booking_ref = f"BK-HT-{uuid.uuid4().hex[:6].upper()}"
    reservation = {
        "booking_type": "hotel",
        "booking_reference": booking_ref,
        "guest_name": guest_name,
        "hotel_name": hotel["name"],
        "city": hotel["city"],
        "nights": nights,
        "total_cost_usd": total_cost,
        "amenities": hotel["amenities"],
        "status": "CONFIRMED"
    }

    ACTIVE_BOOKINGS[booking_ref] = reservation
    logger.info("Hotel booked successfully", booking_ref=booking_ref, total_cost_usd=total_cost)
    return {"status": "success", "reservation": reservation}

def get_booking(booking_reference: str) -> Dict[str, Any]:
    """Retrieves an existing reservation by its booking reference code."""
    logger.info("Tool executed: get_booking", booking_reference=booking_reference)
    ref_clean = booking_reference.upper().strip()
    booking = ACTIVE_BOOKINGS.get(ref_clean)
    if not booking:
        logger.warning("Booking reference not found", booking_reference=booking_reference)
        return {"status": "not_found", "message": f"No reservation found for reference '{booking_reference}'."}
    logger.info("Booking reference retrieved", booking_reference=booking_reference, details=booking)
    return {"status": "found", "booking": booking}

def cancel_booking(booking_reference: str) -> Dict[str, Any]:
    """Cancels an existing booking."""
    logger.info("Tool executed: cancel_booking", booking_reference=booking_reference)
    ref_clean = booking_reference.upper().strip()
    if ref_clean in ACTIVE_BOOKINGS:
        canceled = ACTIVE_BOOKINGS.pop(ref_clean)
        logger.info("Booking canceled successfully", booking_reference=booking_reference)
        return {"status": "canceled", "message": f"Booking {ref_clean} successfully canceled.", "details": canceled}
    logger.warning("Cancel booking failed: Reference not found", booking_reference=booking_reference)
    return {"status": "not_found", "message": f"Cannot cancel: Reference '{booking_reference}' does not exist."}

TOOL_REGISTRY = {
    "search_flights": search_flights,
    "search_hotels": search_hotels,
    "book_flight": book_flight,
    "book_hotel": book_hotel,
    "get_booking": get_booking,
    "cancel_booking": cancel_booking
}

# -------------------------------------------------------------
# 3. OPENAI TOOL SCHEMAS FOR THE BOOKING AGENT
# -------------------------------------------------------------

BOOKING_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_flights",
            "description": "Query live flight availability, schedules, and pricing between origin and destination cities or airports.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {"type": "string", "description": "Departure city or airport (e.g. New York, JFK, London)"},
                    "destination": {"type": "string", "description": "Arrival city or airport (e.g. London, LHR, Paris, Tokyo)"}
                },
                "required": ["origin", "destination"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_hotels",
            "description": "Search available hotel properties, star ratings, amenities, and nightly rates in a destination city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "Destination city (e.g. London, Paris, Tokyo, Dubai)"}
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_flight",
            "description": "Confirm and book a seat on a selected flight. Generates a formal booking reference.",
            "parameters": {
                "type": "object",
                "properties": {
                    "flight_id": {"type": "string", "description": "The exact flight ID, e.g. FL-101 or FL-102"},
                    "passenger_name": {"type": "string", "description": "Full name of the passenger"},
                    "seat_class": {"type": "string", "description": "Seat class (Economy, Business, First)", "default": "Economy"}
                },
                "required": ["flight_id", "passenger_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_hotel",
            "description": "Confirm and book a room at a hotel. Generates a formal reservation reference.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hotel_id": {"type": "string", "description": "The hotel ID, e.g. HT-10 or HT-11"},
                    "guest_name": {"type": "string", "description": "Full name of the primary guest"},
                    "nights": {"type": "integer", "description": "Number of nights to stay", "default": 1}
                },
                "required": ["hotel_id", "guest_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_booking",
            "description": "Look up details for an existing flight or hotel reservation using its reference code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_reference": {"type": "string", "description": "Booking reference code, e.g. BK-FL-A1B2C3"}
                },
                "required": ["booking_reference"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_booking",
            "description": "Cancel an active booking reference.",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_reference": {"type": "string", "description": "Booking reference to cancel"}
                },
                "required": ["booking_reference"]
            }
        }
    }
]

# -------------------------------------------------------------
# 4. PERSONALIZED SYSTEM PROMPT (TRAVEL CONCIERGE)
# -------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are Atlas, an elite autonomous luxury travel & reservations concierge. "
    "MANDATORY OPERATIONAL PROTOCOLS:\n"
    "1. REAL-TIME DATA ONLY: You MUST query real-time data using the provided tools (search_flights, search_hotels) "
    "   before making recommendations or answering. Never invent flights or hotels from imagination.\n"
    "2. PROACTIVE BOOKING: If the user provides passenger/guest details or confirms a booking, "
    "   call book_flight or book_hotel immediately to confirm the reservation in the system.\n"
    "3. ITINERARY PRESENTATION: After gathering tool data or completing bookings, format your final response as a clear, premium travel itinerary with:\n"
    "   - Passenger / Guest Name\n"
    "   - Flight & Hotel Details (Flight #, Airline, Hotel name, Room type)\n"
    "   - Official Confirmation References (e.g. BK-FL-XXXXXX, BK-HT-XXXXXX)\n"
    "   - Total Cost Breakdown\n"
    "Maintain a courteous, highly professional executive concierge tone."
)

# -------------------------------------------------------------
# 5. MULTI-TURN AUTONOMOUS AGENT LOOP
# -------------------------------------------------------------

def run_booking_agent(user_query: str, max_turns: int = 6):
    client = OpenAI(base_url=BASE_URL, api_key="local")

    logger.info("Starting booking agent session", query=user_query, max_turns=max_turns, endpoint=BASE_URL)
    print("\n" + "=" * 70)
    print("  ATLAS - AUTONOMOUS TRAVEL BOOKING CONCIERGE")
    print(f"  API Bridge: {BASE_URL}")
    print(f"  User Request: \"{user_query}\"")
    print("=" * 70)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query}
    ]

    turn = 1
    while turn <= max_turns:
        logger.info("Agent turn starting", turn=turn, max_turns=max_turns, conversation_length=len(messages))
        print(f"\n--- [CONCIERGE TURN {turn}] Consulting Travel Engine ---")
        t0 = time.time()

        try:
            response = client.chat.completions.create(
                model="chatgpt",
                messages=messages,
                tools=BOOKING_TOOLS
            )
        except Exception as e:
            logger.error("ZeroKey API request failed", turn=turn, error=str(e), exc_info=True)
            print(f"\n[X] Error communicating with ZeroKey API: {e}")
            return False

        duration = round(time.time() - t0, 2)
        choice = response.choices[0]
        finish_reason = choice.finish_reason

        logger.info("ZeroKey API response received", turn=turn, latency_seconds=duration, finish_reason=finish_reason)
        print(f" * Latency:       {duration}s")
        print(f" * Finish Reason: {finish_reason}")

        # Case A: Agent queries booking tools
        if finish_reason == "tool_calls" and choice.message.tool_calls:
            tool_calls = choice.message.tool_calls
            tool_names = [tc.function.name for tc in tool_calls]
            logger.info("Agent requested tool calls", count=len(tool_calls), tools=tool_names)
            print(f" * Action:        Invoking {len(tool_calls)} Booking Tool(s)")

            # Record assistant turn with tool calls
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in tool_calls
                ]
            })

            # Execute real in-memory tool logic
            for tc in tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments
                except Exception:
                    fn_args = {}

                logger.info("Executing tool call", call_id=tc.id, tool=fn_name, arguments=fn_args)

                if fn_name in TOOL_REGISTRY:
                    tool_result = TOOL_REGISTRY[fn_name](**fn_args)
                else:
                    logger.error("Tool not found in registry", tool=fn_name)
                    tool_result = {"error": f"Tool '{fn_name}' not registered."}

                logger.info("Tool output generated", call_id=tc.id, tool=fn_name, result=tool_result)

                # Send observation back to agent
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(tool_result)
                })

            turn += 1
            continue

        # Case B: Agent delivers final itinerary
        elif finish_reason == "stop":
            final_text = choice.message.content
            logger.info("Agent final itinerary generated", turns=turn, output_length=len(final_text) if final_text else 0)
            print("\n" + "=" * 70)
            print("  CONCIERGE FINAL ITINERARY CONFIRMATION:")
            print("=" * 70)
            print(final_text)
            print("=" * 70)
            print(f"\n[+] Itinerary successfully processed in {turn} turns!\n")
            return True

        else:
            logger.warning("Unexpected finish reason", finish_reason=finish_reason, content=choice.message.content)
            print(f"[!] Finish reason: {finish_reason}")
            print(choice.message.content)
            break

    logger.warning("Agent reached maximum turns without completion", max_turns=max_turns)
    print(f"\n[X] Reached maximum turns ({max_turns}) without completion.")
    return False

# -------------------------------------------------------------
# 6. INTERACTIVE CONSOLE
# -------------------------------------------------------------

def interactive_mode():
    print("=" * 70)
    print("  ZeroKey Travel & Hotel Booking Agent (No Database)")
    print("  Persona: Atlas (Executive Travel Concierge)")
    print("  Try saying:")
    print("   - 'Find flights from New York to London and book a 4-star hotel in London for Alice Smith'")
    print("   - 'Search flights from San Francisco to Tokyo'")
    print("   - 'Check my booking reference BK-FL-XXXXXX'")
    print("=" * 70)

    while True:
        try:
            print("\nEnter your travel request (or 'exit' to quit):")
            req = input("User > ").strip()
            if not req:
                continue
            if req.lower() in ("exit", "quit", "q"):
                print("Thank you for using Atlas Concierge. Safe travels!")
                break
            run_booking_agent(req)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting booking agent.")
            break

if __name__ == "__main__":
    if len(sys.argv) > 1:
        user_query = " ".join(sys.argv[1:])
        run_booking_agent(user_query)
    else:
        interactive_mode()
