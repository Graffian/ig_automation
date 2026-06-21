import csv
import os
from datetime import datetime

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")

def ensure_dir():
    os.makedirs(REPORTS_DIR, exist_ok=True)

def export_followers(account_name, followers_active, followers_inactive):
    ensure_dir()
    path = os.path.join(REPORTS_DIR, f"{account_name}_followers.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["username", "status", "first_seen", "last_seen"])
        for u in followers_active:
            w.writerow([u["follower_username"], "active", u["first_seen"], u["last_seen"]])
        for u in followers_inactive:
            w.writerow([u["follower_username"], "unfollowed", u["first_seen"], u["last_seen"]])
    print(f"  Report: {path}")

def export_following(account_name, following_active, following_inactive):
    ensure_dir()
    path = os.path.join(REPORTS_DIR, f"{account_name}_following.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["username", "status", "first_seen", "last_seen"])
        for u in following_active:
            w.writerow([u["follow_username"], "active", u["first_seen"], u["last_seen"]])
        for u in following_inactive:
            w.writerow([u["follow_username"], "unfollowed", u["first_seen"], u["last_seen"]])
    print(f"  Report: {path}")

def export_posts(account_name, posts):
    ensure_dir()
    path = os.path.join(REPORTS_DIR, f"{account_name}_posts.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["post_id", "code", "likes", "comments", "caption", "taken_at"])
        for p in posts:
            w.writerow([p["post_id"], p["code"], p["like_count"], p["comment_count"], p["caption"], p["taken_at"]])
    print(f"  Report: {path}")

def export_comments(account_name, comments):
    ensure_dir()
    path = os.path.join(REPORTS_DIR, f"{account_name}_comments.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["post_id", "username", "text", "created_at"])
        for c in comments:
            w.writerow([c["post_id"], c["username"], c["text"], c["created_at"]])
    print(f"  Report: {path}")

def export_all(account_name):
    import database as db
    conn = db.get_connection()

    active_followers = conn.execute(
        "SELECT follower_username, first_seen, last_seen FROM followers WHERE account_name=? AND is_active=1 ORDER BY follower_username",
        (account_name,)
    ).fetchall()
    inactive_followers = conn.execute(
        "SELECT follower_username, first_seen, last_seen FROM followers WHERE account_name=? AND is_active=0 ORDER BY last_seen DESC",
        (account_name,)
    ).fetchall()
    export_followers(account_name, active_followers, inactive_followers)

    active_following = conn.execute(
        "SELECT follow_username, first_seen, last_seen FROM following WHERE account_name=? AND is_active=1 ORDER BY follow_username",
        (account_name,)
    ).fetchall()
    inactive_following = conn.execute(
        "SELECT follow_username, first_seen, last_seen FROM following WHERE account_name=? AND is_active=0 ORDER BY last_seen DESC",
        (account_name,)
    ).fetchall()
    export_following(account_name, active_following, inactive_following)

    posts = conn.execute(
        "SELECT post_id, code, like_count, comment_count, caption, taken_at FROM posts WHERE account_name=? ORDER BY taken_at DESC",
        (account_name,)
    ).fetchall()
    export_posts(account_name, posts)

    comments = conn.execute(
        "SELECT post_id, username, text, created_at FROM comments WHERE account_name=? ORDER BY created_at DESC",
        (account_name,)
    ).fetchall()
    export_comments(account_name, comments)

    conn.close()
