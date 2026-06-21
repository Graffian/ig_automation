import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import database as db


class BrowserTracker:
    def __init__(self, username, password, headless=False):
        self.ig_username = username
        self.ig_password = password
        self.headless = headless
        self.browser = None
        self.page = None
        self.playwright = None

    def start(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ]
        )
        context = self.browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            )
        )
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        self.page = context.new_page()

    def close(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def login(self):
        print("Logging in...")
        self.page.goto("https://www.instagram.com/accounts/login/")
        self.page.wait_for_load_state("networkidle")
        time.sleep(2)

        self.page.locator("input[name='email']").fill(self.ig_username)
        time.sleep(0.5)
        self.page.locator("input[name='pass']").fill(self.ig_password)
        time.sleep(0.5)
        self.page.get_by_role("button", name="Log In", exact=True).click()

        self.page.wait_for_load_state("networkidle")
        time.sleep(4)

        for _ in range(3):
            try:
                not_now = self.page.get_by_role("button", name="Not Now")
                if not_now.is_visible(timeout=3000):
                    not_now.click()
                    time.sleep(2)
            except:
                pass

        if self._is_challenge_visible():
            input("\n⚠️  reCAPTCHA/Challenge detected! Solve it in the browser window, then press Enter to continue...")
            time.sleep(3)

        print("Logged in successfully")

    def _is_challenge_visible(self):
        challenge_indicators = [
            "iframe[title*='challenge']",
            "iframe[src*='recaptcha']",
            "text=Suspicious Login Attempt",
            "text=Confirm It's You",
            "text=Enter the code",
            "div[role='dialog']:has-text('Challenge')",
        ]
        for selector in challenge_indicators:
            try:
                if self.page.locator(selector).is_visible(timeout=2000):
                    return True
            except:
                pass
        return False

    def navigate_to_profile(self, account_name):
        print(f"\n  Searching for @{account_name}...")
        search_icon = self.page.locator("svg[aria-label='Search']")
        search_icon.hover()
        time.sleep(0.5)
        search_icon.click()
        time.sleep(2)

        search_input = self.page.locator("input[placeholder='Search']")
        search_input.fill(account_name)
        time.sleep(2)

        result = self.page.locator(f"span:has-text('{account_name}')").first
        result.wait_for(state="visible", timeout=10000)
        result.click()
        time.sleep(4)

    def track_account(self, account_name):
        print(f"\n{'='*60}")
        print(f"Tracking @{account_name} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        db.add_tracked_account(account_name)

        try:
            self.navigate_to_profile(account_name)
        except Exception as e:
            print(f"  Search failed ({e}), trying direct URL...")
            try:
                self.page.goto(f"https://www.instagram.com/{account_name}/", timeout=30000)
            except Exception:
                print("  Page was closed, re-creating...")
                context = self.browser.new_context(
                    viewport={"width": 1366, "height": 768},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/125.0.0.0 Safari/537.36"
                    )
                )
                context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                """)
                self.page = context.new_page()
                self.page.goto(f"https://www.instagram.com/{account_name}/", timeout=30000)
            time.sleep(4)

        self._track_posts(account_name)

        follower_count, following_count = self._get_counts()
        print(f"  Followers: {follower_count}  Following: {following_count}")

        self._track_followers(account_name)
        self._track_following(account_name)

        summary = db.get_summary(account_name)
        self._print_summary(account_name, summary)

    def _get_counts(self):
        try:
            header = self.page.locator("header section ul")
            items = header.locator("li").all()
            counts = []
            for li in items:
                span = li.locator("span")
                if span.is_visible():
                    text = span.inner_text()
                    counts.append(self._parse_number(text))
            if len(counts) >= 3:
                return counts[1], counts[2]
            return counts[1] if len(counts) > 1 else 0, counts[2] if len(counts) > 2 else 0
        except Exception:
            return 0, 0

    def _parse_number(self, text):
        text = text.split("\n")[0].replace(",", "")
        if "k" in text:
            return int(float(text.replace("k", "")) * 1000)
        if "m" in text:
            return int(float(text.replace("m", "")) * 1000000)
        try:
            return int(text)
        except:
            return 0

    def _track_posts(self, account_name):
        print("\n[Posts] Scrolling and collecting posts...")
        try:
            self.page.wait_for_selector("article a", timeout=10000)
        except PlaywrightTimeout:
            print("  No posts found or account is private")
            return

        links = set()
        scroll_attempts = 0
        max_scrolls = 10

        while scroll_attempts < max_scrolls:
            articles = self.page.locator("article a").all()
            for a in articles:
                href = a.get_attribute("href")
                if href and "/p/" in href:
                    post_code = href.split("/p/")[1].strip("/")
                    links.add(post_code)

            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            scroll_attempts += 1

        print(f"  Found {len(links)} posts")

        for code in links:
            try:
                self.page.goto(f"https://www.instagram.com/p/{code}/")
                time.sleep(3)

                caption_el = self.page.locator("h1").first
                caption = caption_el.inner_text()[:500] if caption_el.is_visible(timeout=3000) else ""

                like_el = self.page.locator("article section span").first
                like_text = like_el.inner_text() if like_el.is_visible(timeout=3000) else "0"
                like_count = self._parse_number(like_text)

                comment_count = 0
                comments_section = self.page.locator("ul li span")
                all_comments = comments_section.all()
                comment_count = len(all_comments) if all_comments else 0

                post_id = f"post_{code}"
                db.upsert_post(account_name, post_id, code, caption, like_count, comment_count, str(datetime.now()), 1)

                self._track_comments(account_name, post_id)

            except Exception as e:
                print(f"  Skipping post {code}: {e}")

    def _track_comments(self, account_name, post_id):
        try:
            comment_items = self.page.locator("ul li").all()
            count = 0
            for li in comment_items:
                try:
                    username_el = li.locator("a").first
                    text_el = li.locator("span").first
                    if username_el.is_visible(timeout=1000) and text_el.is_visible(timeout=1000):
                        username = username_el.inner_text().strip()
                        text = text_el.inner_text().strip()[:500]
                        if username and username != self.ig_username:
                            comment_id = f"cmt_{post_id}_{username}_{count}"
                            db.upsert_comment(account_name, post_id, comment_id, username, text, str(datetime.now()))
                            count += 1
                except:
                    pass
        except Exception:
            pass

    def _track_followers(self, account_name):
        print("\n[Followers] Opening followers dialog...")
        try:
            followers_link = self.page.locator("a").filter(has_text=re.compile(r"follower", re.IGNORECASE)).first
            followers_link.click()
            time.sleep(3)

            dialog = self.page.locator("div[role='dialog']")
            dialog.wait_for(state="visible", timeout=8000)

            usernames = set()
            prev_count = 0
            stable_rounds = 0

            while stable_rounds < 3:
                links = dialog.locator("a").all()
                for a in links:
                    href = a.get_attribute("href")
                    if href and len(href) > 1 and "/" not in href[1:]:
                        usernames.add(href.lstrip("/"))

                dialog.locator("div").last.hover()
                time.sleep(1.5)

                if len(usernames) == prev_count:
                    stable_rounds += 1
                else:
                    stable_rounds = 0
                prev_count = len(usernames)

            print(f"  Scraped {len(usernames)} followers")
            new_followers, lost_followers = db.sync_followers(account_name, list(usernames))
            db.record_snapshot(account_name, "followers", len(usernames))

            if new_followers:
                print(f"  New ({len(new_followers)}): {', '.join(list(new_followers)[:10])}")
            if lost_followers:
                print(f"  Lost ({len(lost_followers)}): {', '.join(list(lost_followers)[:10])}")

            self.page.keyboard.press("Escape")
            time.sleep(1)

        except Exception as e:
            print(f"  Error scraping followers: {e}")
            self.page.keyboard.press("Escape")

    def _track_following(self, account_name):
        print("\n[Following] Opening following dialog...")
        try:
            following_link = self.page.locator("a").filter(has_text=re.compile(r"following", re.IGNORECASE)).first
            following_link.click()
            time.sleep(3)

            dialog = self.page.locator("div[role='dialog']")
            dialog.wait_for(state="visible", timeout=8000)

            usernames = set()
            prev_count = 0
            stable_rounds = 0

            while stable_rounds < 3:
                links = dialog.locator("a").all()
                for a in links:
                    href = a.get_attribute("href")
                    if href and len(href) > 1 and "/" not in href[1:]:
                        usernames.add(href.lstrip("/"))

                dialog.locator("div").last.hover()
                time.sleep(1.5)

                if len(usernames) == prev_count:
                    stable_rounds += 1
                else:
                    stable_rounds = 0
                prev_count = len(usernames)

            print(f"  Scraped {len(usernames)} following")
            new_follows, unfollowed = db.sync_following(account_name, list(usernames))
            db.record_snapshot(account_name, "following", len(usernames))

            if new_follows:
                print(f"  New follows ({len(new_follows)}): {', '.join(list(new_follows)[:10])}")
            if unfollowed:
                print(f"  Unfollowed ({len(unfollowed)}): {', '.join(list(unfollowed)[:10])}")

            self.page.keyboard.press("Escape")
            time.sleep(1)

        except Exception as e:
            print(f"  Error scraping following: {e}")
            self.page.keyboard.press("Escape")

    def _print_summary(self, account_name, summary):
        print(f"\n{'─'*60}")
        print(f"Summary for @{account_name}")
        print(f"{'─'*60}")
        print(f"  Posts tracked:     {summary['posts']['count']}")
        print(f"  Total likes:       {summary['posts']['total_likes']}")
        print(f"  Total comments:    {summary['posts']['total_comments']}")
        print(f"  Comments recorded: {summary['comments']}")
        print(f"  Current followers: {summary['followers_active']}")
        print(f"  Current following: {summary['following_active']}")
        if summary["unfollowers"]:
            print(f"  Unfollowers:       {len(summary['unfollowers'])} (last: {summary['unfollowers'][0]})")
        if summary["unfollowed_by_me"]:
            print(f"  Unfollowed by me:  {len(summary['unfollowed_by_me'])}")
        print(f"{'─'*60}")

    def _ensure_page(self):
        if not self.page or self.page.is_closed():
            context = self.browser.new_context(
                viewport={"width": 1366, "height": 768},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                )
            )
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """)
            self.page = context.new_page()

    def run_once(self, target_accounts):
        self.start()
        try:
            self.login()
            self._ensure_page()
            for account in target_accounts:
                try:
                    self.track_account(account)
                except Exception as e:
                    print(f"Error tracking @{account}: {e}")
        finally:
            self.close()
