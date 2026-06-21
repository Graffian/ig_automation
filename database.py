import sqlite3
import os
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(__file__), "instagram_data.db")

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS tracked_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_name TEXT UNIQUE NOT NULL,
            added_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_name TEXT NOT NULL,
            post_id TEXT NOT NULL,
            code TEXT,
            caption TEXT,
            like_count INTEGER DEFAULT 0,
            comment_count INTEGER DEFAULT 0,
            taken_at TEXT,
            media_type INTEGER,
            last_checked TEXT DEFAULT (datetime('now')),
            UNIQUE(account_name, post_id)
        );

        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_name TEXT NOT NULL,
            post_id TEXT NOT NULL,
            comment_id TEXT NOT NULL,
            username TEXT,
            text TEXT,
            created_at TEXT,
            last_seen TEXT DEFAULT (datetime('now')),
            UNIQUE(account_name, comment_id)
        );

        CREATE TABLE IF NOT EXISTS followers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_name TEXT NOT NULL,
            follower_username TEXT NOT NULL,
            follower_id TEXT,
            full_name TEXT,
            first_seen TEXT DEFAULT (datetime('now')),
            last_seen TEXT DEFAULT (datetime('now')),
            is_active INTEGER DEFAULT 1,
            UNIQUE(account_name, follower_username)
        );

        CREATE TABLE IF NOT EXISTS following (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_name TEXT NOT NULL,
            follow_username TEXT NOT NULL,
            follow_id TEXT,
            full_name TEXT,
            first_seen TEXT DEFAULT (datetime('now')),
            last_seen TEXT DEFAULT (datetime('now')),
            is_active INTEGER DEFAULT 1,
            UNIQUE(account_name, follow_username)
        );

        CREATE TABLE IF NOT EXISTS tracking_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_name TEXT NOT NULL,
            snapshot_type TEXT NOT NULL,
            value INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()

def add_tracked_account(account_name):
    conn = get_connection()
    try:
        conn.execute("INSERT OR IGNORE INTO tracked_accounts (account_name) VALUES (?)", (account_name,))
        conn.commit()
    finally:
        conn.close()

def upsert_post(account_name, post_id, code, caption, like_count, comment_count, taken_at, media_type):
    conn = get_connection()
    conn.execute("""
        INSERT INTO posts (account_name, post_id, code, caption, like_count, comment_count, taken_at, media_type, last_checked)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(account_name, post_id) DO UPDATE SET
            like_count = excluded.like_count,
            comment_count = excluded.comment_count,
            caption = excluded.caption,
            last_checked = datetime('now')
    """, (account_name, post_id, code, caption, like_count, comment_count, taken_at, media_type))
    conn.commit()
    conn.close()

def upsert_comment(account_name, post_id, comment_id, username, text, created_at):
    conn = get_connection()
    conn.execute("""
        INSERT INTO comments (account_name, post_id, comment_id, username, text, created_at, last_seen)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(account_name, comment_id) DO UPDATE SET
            last_seen = datetime('now'),
            text = excluded.text
    """, (account_name, post_id, comment_id, username, text, created_at))
    conn.commit()
    conn.close()

def sync_followers(account_name, current_followers):
    conn = get_connection()
    existing = conn.execute(
        "SELECT follower_username FROM followers WHERE account_name = ? AND is_active = 1",
        (account_name,)
    ).fetchall()
    existing_set = {r["follower_username"] for r in existing}
    current_set = set(current_followers)

    new_followers = current_set - existing_set
    lost_followers = existing_set - current_set

    for username in new_followers:
        conn.execute(
            "INSERT OR IGNORE INTO followers (account_name, follower_username, first_seen, last_seen, is_active) VALUES (?, ?, datetime('now'), datetime('now'), 1)",
            (account_name, username)
        )
    for username in lost_followers:
        conn.execute(
            "UPDATE followers SET is_active = 0, last_seen = datetime('now') WHERE account_name = ? AND follower_username = ?",
            (account_name, username)
        )
    conn.commit()
    conn.close()
    return new_followers, lost_followers

def sync_following(account_name, current_following):
    conn = get_connection()
    existing = conn.execute(
        "SELECT follow_username FROM following WHERE account_name = ? AND is_active = 1",
        (account_name,)
    ).fetchall()
    existing_set = {r["follow_username"] for r in existing}
    current_set = set(current_following)

    new_follows = current_set - existing_set
    unfollowed = existing_set - current_set

    for username in new_follows:
        conn.execute(
            "INSERT OR IGNORE INTO following (account_name, follow_username, first_seen, last_seen, is_active) VALUES (?, ?, datetime('now'), datetime('now'), 1)",
            (account_name, username)
        )
    for username in unfollowed:
        conn.execute(
            "UPDATE following SET is_active = 0, last_seen = datetime('now') WHERE account_name = ? AND follow_username = ?",
            (account_name, username)
        )
    conn.commit()
    conn.close()
    return new_follows, unfollowed

def record_snapshot(account_name, snapshot_type, value):
    conn = get_connection()
    conn.execute(
        "INSERT INTO tracking_snapshots (account_name, snapshot_type, value) VALUES (?, ?, ?)",
        (account_name, snapshot_type, value)
    )
    conn.commit()
    conn.close()

def get_summary(account_name):
    conn = get_connection()
    summary = {}

    row = conn.execute(
        "SELECT COUNT(*) as count, COALESCE(SUM(like_count), 0) as total_likes, COALESCE(SUM(comment_count), 0) as total_comments FROM posts WHERE account_name = ?",
        (account_name,)
    ).fetchone()
    summary["posts"] = {"count": row["count"], "total_likes": row["total_likes"], "total_comments": row["total_comments"]}

    row = conn.execute(
        "SELECT COUNT(*) as count FROM comments WHERE account_name = ?", (account_name,)
    ).fetchone()
    summary["comments"] = row["count"]

    row = conn.execute(
        "SELECT COUNT(*) as count FROM followers WHERE account_name = ? AND is_active = 1", (account_name,)
    ).fetchone()
    summary["followers_active"] = row["count"]

    row = conn.execute(
        "SELECT COUNT(*) as count FROM following WHERE account_name = ? AND is_active = 1", (account_name,)
    ).fetchone()
    summary["following_active"] = row["count"]

    row = conn.execute(
        "SELECT follower_username FROM followers WHERE account_name = ? AND is_active = 0 ORDER BY last_seen DESC",
        (account_name,)
    ).fetchall()
    summary["unfollowers"] = [r["follower_username"] for r in row]

    row = conn.execute(
        "SELECT follow_username FROM following WHERE account_name = ? AND is_active = 0 ORDER BY last_seen DESC",
        (account_name,)
    ).fetchall()
    summary["unfollowed_by_me"] = [r["follow_username"] for r in row]

    conn.close()
    return summary

def get_unfollowers_notification(account_name):
    conn = get_connection()
    rows = conn.execute(
        "SELECT follower_username, last_seen FROM followers WHERE account_name = ? AND is_active = 0 ORDER BY last_seen DESC LIMIT 20",
        (account_name,)
    ).fetchall()
    conn.close()
    return [(r["follower_username"], r["last_seen"]) for r in rows]
