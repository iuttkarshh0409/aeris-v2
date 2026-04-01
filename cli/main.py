# cli/main.py
import argparse
import sys
import os

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import Command Modules
from cli.commands import (
    simulate, explain, status, logs, ingest, seed, demo
)

def format_header(title):
    w = 50
    print("\n" + "=" * w)
    print(f" AERIS Control Plane: {title}")
    print("=" * w + "\n")

def main():
    parser = argparse.ArgumentParser(
        description="AERIS v2: Professional Incident Intelligence CLI",
        usage="python -m cli.main <command> [options]"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: SIMULATE
    simulate_parser = subparsers.add_parser("simulate", help="Run deterministic failure scenarios")
    simulate_parser.add_argument("--scenario", choices=["brownian", "storm", "tail", "deployment"], default="deployment", help="Scenario to run")
    simulate_parser.add_argument("--duration", type=int, default=5, help="Simulation duration (min)")

    # Command: EXPLAIN
    subparsers.add_parser("explain", help="Run drift engine and display Decision-Safe Brief")

    # Command: STATUS
    subparsers.add_parser("status", help="Get a high-level system state summary")

    # Command: LOGS
    logs_parser = subparsers.add_parser("logs", help="Display recent ingested events")
    logs_parser.add_argument("--limit", type=int, default=20, help="Max logs to show")

    # Command: INGEST
    ingest_parser = subparsers.add_parser("ingest", help="Manually ingest event JSON data")
    ingest_parser.add_argument("--file", required=True, help="Path to JSON file")

    # Command: SEED
    subparsers.add_parser("seed", help="Seed baseline operational data")

    # Command: DEMO
    subparsers.add_parser("demo", help="Run the academic demonstration scenario")

    # Command: HELP
    subparsers.add_parser("help", help="Display all available commands and descriptions")

    args = parser.parse_args()

    # Define custom help output
    def print_custom_help():
        format_header("HELP / COMMAND REFERENCE")
        print("Commands:")
        print("  simulate   Run failure simulation scenarios")
        print("  explain    Run drift analysis and show Decision-Safe Brief")
        print("  status     Show current system health summary")
        print("  logs       View recent ingested events")
        print("  ingest     Load events from JSON file")
        print("  seed       Initialize baseline data")
        print("  demo       Run academic demonstration")
        print("  help       Show this help message")
        print("\nUsage: python -m cli.main <command> [options]")
        print("=" * 50 + "\n")

    if not args.command or args.command == "help":
        print_custom_help()
        sys.exit(0)

    # Dispatch to specific command handlers
    try:
        if args.command == "simulate":
            format_header(f"Simulating {args.scenario} scenario")
            simulate.run(args.scenario, args.duration)
        elif args.command == "explain":
            format_header("Analytic Explanation Brief")
            explain.run()
        elif args.command == "status":
            format_header("Current System Status")
            status.run()
        elif args.command == "logs":
            format_header(f"Recent Events (Limit: {args.limit})")
            logs.run(args.limit)
        elif args.command == "ingest":
            format_header(f"Manual Event Ingestion: {args.file}")
            ingest.run(args.file)
        elif args.command == "seed":
            format_header("Seeding Baseline Operations")
            seed.run()
        elif args.command == "demo":
            demo.run()
        else:
            print(f"[ERROR] Unknown command: {args.command}")
            print_custom_help()
            sys.exit(1)
            
    except Exception as e:
        print(f"\n[FATAL] CLI Routing Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
