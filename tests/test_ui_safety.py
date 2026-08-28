import unittest
from unittest.mock import patch

from src.core.scenario_executor import ScenarioExecutor


class FakeADB:
    def __init__(self, dumps=None, focused="com.facebook.katana/.MainActivity"):
        self.dumps = list(dumps or [])
        self.focused = focused
        self.taps = []
        self.swipes = []
        self.shell_commands = []

    def dump_ui(self):
        if self.dumps:
            return self.dumps.pop(0)
        return '<hierarchy></hierarchy>'

    def is_screen_on(self):
        return True

    def ensure_screen_on(self):
        return True

    def get_focused_activity(self):
        return self.focused

    def screencap(self):
        return None

    def tap(self, x, y):
        self.taps.append((x, y))
        return True

    def swipe(self, *args):
        self.swipes.append(args)
        return True

    def setup_adb_keyboard(self):
        return True

    def input_text_utf8(self, text):
        return True

    def shell(self, command, timeout=30):
        self.shell_commands.append(command)
        return ""


class UISafetyTests(unittest.TestCase):
    def test_ready_timeout_is_fail_closed(self):
        executor = ScenarioExecutor(FakeADB())
        with patch("src.core.scenario_executor.time.sleep", return_value=None):
            self.assertFalse(executor.wait_for_facebook_ready(timeout_sec=0.01))

    def test_like_does_not_tap_when_like_control_is_absent(self):
        adb = FakeADB(['<hierarchy><node text="Loading" bounds="[0,0][100,100]"/></hierarchy>'] * 4)
        executor = ScenarioExecutor(adb)
        with patch("src.core.scenario_executor.time.sleep", return_value=None):
            self.assertFalse(executor._verify_and_click_post_like())
        self.assertEqual([], adb.taps)

    def test_like_pressed_semantic_is_already_liked_and_never_taps(self):
        pressed = (
            '<hierarchy><node class="android.view.ViewGroup" '
            'content-desc="Like button, pressed. Double tap and hold to change reaction." '
            'clickable="true" enabled="true" bounds="[0,1387][360,1503]"/></hierarchy>'
        )
        adb = FakeADB([pressed] * 5)
        executor = ScenarioExecutor(adb)
        with patch("src.core.scenario_executor.time.sleep", return_value=None):
            self.assertTrue(executor._verify_and_click_post_like())
        self.assertEqual([], adb.taps)

    def test_like_leaves_ambiguous_comments_sheet_before_reading_post_state(self):
        sheet = (
            '<hierarchy><node class="android.widget.EditText" content-desc="Write a comment…" '
            'bounds="[80,1700][900,1800]"/><node class="android.view.ViewGroup" '
            'clickable="true" bounds="[921,68][1080,185]"/></hierarchy>'
        )
        post = (
            '<hierarchy><node class="android.view.ViewGroup" content-desc="Like. Double tap and hold to react." '
            'clickable="true" enabled="true" bounds="[0,1387][360,1503]"/></hierarchy>'
        )
        adb = FakeADB([sheet, post])
        executor = ScenarioExecutor(adb)
        with patch("src.core.scenario_executor.time.sleep", return_value=None):
            control = executor._ensure_semantic_post_like_control()
        self.assertEqual((180, 1445, (0, 1387, 360, 1503)), control)
        self.assertTrue(any("keyevent 4" in command for command in getattr(adb, "shell_commands", [])))

    def test_comment_does_not_tap_when_composer_is_absent(self):
        adb = FakeADB(['<hierarchy><node text="Loading" bounds="[0,0][100,100]"/></hierarchy>'] * 4)
        executor = ScenarioExecutor(adb)
        with patch("src.core.scenario_executor.time.sleep", return_value=None):
            self.assertFalse(executor._verify_and_send_comment("Xin chào"))
        self.assertEqual([], adb.taps)

    def test_comment_opens_inline_post_composer_before_searching_edittext(self):
        inline_post = (
            '<hierarchy><node class="android.view.ViewGroup" content-desc="Comment" '
            'clickable="true" enabled="true" bounds="[360,1387][720,1503]"/></hierarchy>'
        )
        composer = (
            '<hierarchy><node class="android.widget.EditText" text="" '
            'content-desc="Write a comment…" clickable="true" enabled="true" '
            'bounds="[100,1700][900,1800]"/></hierarchy>'
        )
        adb = FakeADB([inline_post, composer])
        executor = ScenarioExecutor(adb)
        with patch("src.core.scenario_executor.time.sleep", return_value=None):
            self.assertEqual((500, 1750), executor._open_post_comment_composer())
        self.assertEqual([(540, 1445)], adb.taps)

    def test_seeding_returns_false_when_deeplink_never_reaches_post(self):
        adb = FakeADB(['<hierarchy><node text="News Feed" bounds="[0,0][100,100]"/></hierarchy>'] * 5)
        adb.shell = lambda command: "Starting: Intent"
        executor = ScenarioExecutor(adb)
        executor.wait_for_facebook_ready = lambda **kwargs: False
        result = executor.execute_seeding({"post_links": "https://facebook.com/123", "emojis": ["Like"]})
        self.assertFalse(result)
        self.assertEqual([], adb.taps)


if __name__ == "__main__":
    unittest.main()
