#!/usr/bin/env python3
"""
Instagram Automation Tool
Tracks posts, comments, followers, and following for any Instagram account.
"""

import argparse
import sys

from colorama import init, Fore, Style

import config as cfg
import database as db
from tracker import InstagramTracker

init(autoreset=True)

BANNER = f"""
{Fore.CYAN}{Style.BRIGHT}
{'='*50}
     Instagram Automation Tracker
  Posts | Comments | Followers | Following
{'='*50}
{Style.RESET_ALL}
"""

def main():
    print(BANNER)

    parser = argparse.ArgumentParser(
        description="Instagram automation tool for tracking accounts."
    )
    parser.add_argument("action", nargs="?", default="track",
                        choices=["track", "summary", "unfollowers", "setup"],
                        help="Action to perform")
    parser.add_argument("-a", "--accounts", nargs="+",
                        help="Target account(s) to track (overrides config)")
    parser.add_argument("-i", "--interval", type=int, default=None,
                        help="Run in loop with N minute interval (omit = once)")
    parser.add_argument("--no-report", action="store_true",
                        help="Skip CSV report generation")
    args = parser.parse_args()

    config = cfg.load_config()

    if args.action == "setup":
        print("Setup mode. Edit config.json with your Instagram credentials.")
        print(f"  Username: {config.get('username', 'not set')}")
        print(f"  Track interval: {config.get('track_interval_minutes', 30)} min")
        print(f"  Target accounts: {config.get('target_accounts', [])}")
        return

    if not cfg.validate_config(config):
        sys.exit(1)

    db.init_db()

    target_accounts = args.accounts or config.get("target_accounts", [])
    if not target_accounts:
        print("No target accounts specified. Use -a or edit config.json.")
        sys.exit(1)

    tracker = InstagramTracker(config["username"], config["password"], generate_reports=not args.no_report)

    if args.action == "track":
        if args.interval is not None:
            if args.interval > 0:
                tracker.run_loop(target_accounts, args.interval)
            else:
                tracker.run_once(target_accounts)
        else:
            interval = config.get("track_interval_minutes", 0)
            if interval > 0:
                tracker.run_loop(target_accounts, interval)
            else:
                tracker.run_once(target_accounts)

    elif args.action == "summary":
        for account in target_accounts:
            summary = db.get_summary(account)
            if summary["posts"]["count"] == 0:
                print(f"No data for @{account}. Run 'track' first.")
                continue
            print(f"\n{'-'*60}")
            print(f"Summary for @{account}")
            print(f"{'-'*60}")
            print(f"  Posts tracked:       {summary['posts']['count']}")
            print(f"  Total likes:         {summary['posts']['total_likes']}")
            print(f"  Total comments:      {summary['posts']['total_comments']}")
            print(f"  Comments recorded:   {summary['comments']}")
            print(f"  Followers (stored):  {summary['followers_active']}")
            print(f"  Following (stored):  {summary['following_active']}")
            if summary["unfollowers"]:
                print(f"  Unfollowers:         {len(summary['unfollowers'])}")
            if summary["unfollowed_by_me"]:
                print(f"  Unfollowed by me:    {len(summary['unfollowed_by_me'])}")
            print(f"{'-'*60}")

    elif args.action == "unfollowers":
        for account in target_accounts:
            unfollowers = db.get_unfollowers_notification(account)
            if not unfollowers:
                print(f"No unfollowers detected for @{account}")
            else:
                print(f"\nRecent unfollowers for @{account}:")
                for username, last_seen in unfollowers:
                    print(f"  - @{username} (unfollowed {last_seen})")


if __name__ == "__main__":
    main()
