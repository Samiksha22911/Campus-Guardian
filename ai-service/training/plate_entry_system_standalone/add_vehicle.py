"""
add_vehicle.py
---------------
Small CLI to manage the vehicle registry without writing SQL by hand.

Examples:
    python add_vehicle.py add --plate MP09XY5678 --name "Dr. Neha Verma" --role faculty --dept ECE --type car
    python add_vehicle.py remove --plate MP09XY5678
    python add_vehicle.py list
"""

import argparse
from database import init_db, add_vehicle, remove_vehicle, get_connection


def list_vehicles():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM vehicles ORDER BY plate_number").fetchall()
    conn.close()
    if not rows:
        print("No vehicles registered yet.")
        return
    print(f"{'PLATE':<15}{'OWNER':<20}{'ROLE':<10}{'DEPT':<10}{'TYPE':<8}{'ACTIVE'}")
    for r in rows:
        print(f"{r['plate_number']:<15}{r['owner_name']:<20}{r['role']:<10}"
              f"{r['department'] or '':<10}{r['vehicle_type'] or '':<8}{bool(r['active'])}")


def main():
    parser = argparse.ArgumentParser(description="Manage the vehicle registry")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Register a new vehicle")
    p_add.add_argument("--plate", required=True)
    p_add.add_argument("--name", required=True)
    p_add.add_argument("--role", required=True, choices=["student", "staff", "faculty", "visitor"])
    p_add.add_argument("--dept", default="")
    p_add.add_argument("--type", default="car", choices=["car", "bike"])

    p_remove = sub.add_parser("remove", help="Remove a vehicle by plate number")
    p_remove.add_argument("--plate", required=True)

    sub.add_parser("list", help="List all registered vehicles")

    args = parser.parse_args()
    init_db()

    if args.command == "add":
        add_vehicle(args.plate, args.name, args.role, args.dept, args.type)
        print(f"Added {args.plate.upper()} -> {args.name}")
    elif args.command == "remove":
        remove_vehicle(args.plate)
        print(f"Removed {args.plate.upper()}")
    elif args.command == "list":
        list_vehicles()


if __name__ == "__main__":
    main()
