import time
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ClientError, RateLimitError

import database as db
import reports


class InstagramTracker:
    def __init__(self, username, password, generate_reports=True):
        self.username = username
        self.client = Client()
        self.client.delay_range = [3, 6]
        self.logged_in = False
        self.generate_reports = generate_reports
        self._login(username, password)

    def _login(self, username, password):
        try:
            self.client.login(username, password)
            self.logged_in = True
            print(f"Logged in as @{username}")
        except Exception as e:
            print(f"Login failed: {e}")
            sys.exit(1)

    def track_account(self, account_name):
        print(f"\n{'='*60}")
        print(f"Tracking @{account_name} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        try:
            user_id = self.client.user_id_from_username(account_name)
            user_info = self.client.user_info(user_id)
            actual_followers = user_info.follower_count
            actual_following = user_info.following_count
            print(f"  Profile: {actual_followers} followers, {actual_following} following")
        except Exception as e:
            print(f"Could not find user @{account_name}: {e}")
            return

        db.add_tracked_account(account_name)

        self._track_posts(account_name, user_id)
        self._track_followers(account_name, user_id, actual_followers)
        self._track_following(account_name, user_id, actual_following)

        summary = db.get_summary(account_name)
        self._print_summary(account_name, summary, actual_followers, actual_following)

        if self.generate_reports:
            reports.export_all(account_name)

    def _track_posts(self, account_name, user_id):
        print("\n[Posts] Fetching recent posts...")
        try:
            medias = self.client.user_medias(user_id, amount=20)
            print(f"  Found {len(medias)} recent posts")
            for m in medias:
                like_count = m.like_count or 0
                comment_count = m.comment_count or 0
                caption = m.caption_text[:500] if m.caption_text else ""
                db.upsert_post(
                    account_name, m.id, m.code, caption,
                    like_count, comment_count,
                    str(m.taken_at), m.media_type
                )
                if comment_count > 0:
                    self._track_comments(account_name, m.id)
                time.sleep(1)
        except Exception as e:
            print(f"  Error fetching posts: {e}")

    def _track_comments(self, account_name, media_id):
        try:
            comments = self.client.media_comments(media_id, amount=50)
            for c in comments:
                db.upsert_comment(account_name, media_id, c.id, c.user.username, c.text[:500], str(c.created_at_utc))
        except Exception as e:
            pass

    def _track_followers(self, account_name, user_id, actual_count):
        print("\n[Followers] Fetching follower list...")
        try:
            followers = self.client.user_followers(user_id, amount=0)
            usernames = [u.username for u in followers.values()]
            scraped = len(usernames)
            print(f"  Scraped: {scraped} / Profile says: {actual_count}")
            new_followers, lost_followers = db.sync_followers(account_name, usernames)
            db.record_snapshot(account_name, "followers", scraped)

            if new_followers:
                print(f"  New ({len(new_followers)}): {', '.join(list(new_followers)[:10])}{'...' if len(new_followers) > 10 else ''}")
            if lost_followers:
                print(f"  Lost ({len(lost_followers)}): {', '.join(list(lost_followers)[:10])}{'...' if len(lost_followers) > 10 else ''}")
        except Exception as e:
            print(f"  Error fetching followers: {e}")

    def _track_following(self, account_name, user_id, actual_count):
        print("\n[Following] Fetching following list...")
        try:
            following = self.client.user_following(user_id, amount=0)
            usernames = [u.username for u in following.values()]
            scraped = len(usernames)
            print(f"  Scraped: {scraped} / Profile says: {actual_count}")
            new_follows, unfollowed = db.sync_following(account_name, usernames)
            db.record_snapshot(account_name, "following", scraped)

            if new_follows:
                print(f"  New follows ({len(new_follows)}): {', '.join(list(new_follows)[:10])}{'...' if len(new_follows) > 10 else ''}")
            if unfollowed:
                print(f"  Unfollowed ({len(unfollowed)}): {', '.join(list(unfollowed)[:10])}{'...' if len(unfollowed) > 10 else ''}")
        except Exception as e:
            print(f"  Error fetching following: {e}")

    def _print_summary(self, account_name, summary, actual_followers, actual_following):
        print(f"\n{'-'*60}")
        print(f"Summary for @{account_name}")
        print(f"{'-'*60}")
        print(f"  Posts tracked:       {summary['posts']['count']}")
        print(f"  Total likes:         {summary['posts']['total_likes']}")
        print(f"  Total comments:      {summary['posts']['total_comments']}")
        print(f"  Comments recorded:   {summary['comments']}")
        print(f"  Followers (profile): {actual_followers}  (stored: {summary['followers_active']})")
        print(f"  Following (profile): {actual_following}  (stored: {summary['following_active']})")
        if summary["unfollowers"]:
            print(f"  Unfollowers:         {len(summary['unfollowers'])}")
        if summary["unfollowed_by_me"]:
            print(f"  Unfollowed by me:    {len(summary['unfollowed_by_me'])}")
        print(f"{'-'*60}")

    def run_once(self, target_accounts):
        print(f"\nTracking {len(target_accounts)} accounts in parallel...")
        with ThreadPoolExecutor(max_workers=len(target_accounts)) as executor:
            futures = {executor.submit(self.track_account, acc): acc for acc in target_accounts}
            for future in as_completed(futures):
                acc = futures[future]
                try:
                    future.result()
                except Exception as e:
                    print(f"Error tracking @{acc}: {e}")

    def run_loop(self, target_accounts, interval_minutes):
        print(f"\nStarting continuous tracking every {interval_minutes} minutes")
        print("Press Ctrl+C to stop\n")
        while True:
            self.run_once(target_accounts)
            next_run = datetime.now().timestamp() + interval_minutes * 60
            print(f"\nNext run at {datetime.fromtimestamp(next_run).strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Waiting {interval_minutes} minutes...\n")
            try:
                time.sleep(interval_minutes * 60)
            except KeyboardInterrupt:
                print("\nTracking stopped by user.")
                break
