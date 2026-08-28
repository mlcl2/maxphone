import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.core.scenario_executor import ScenarioExecutor


class FakeADB:
    def __init__(self, dumps):
        self.dumps = list(dumps)
        self.last = '<hierarchy></hierarchy>'
        self.taps = []
        self.inputs = []
        self.swipes = []

    def dump_ui(self):
        if self.dumps:
            self.last = self.dumps.pop(0)
        return self.last

    def tap(self, x, y):
        self.taps.append((x, y)); return True

    def setup_adb_keyboard(self): return True
    def input_text_utf8(self, text): self.inputs.append(text); return True
    def is_screen_on(self): return True
    def ensure_screen_on(self): return True
    def screencap(self): return b''
    def get_focused_activity(self): return 'com.facebook.katana/.MainActivity'
    def shell(self, command, timeout=30): return 'Physical size: 1080x1920' if 'wm size' in command else ''
    def press_back(self): return True

    def swipe(self, *args): self.swipes.append(args); return True


HOME = '<hierarchy><node content-desc="Make a post on Facebook"/>'+'<node class="android.view.View" clickable="true" selected="true" bounds="[0,179][180,295]"/><node class="android.view.View" clickable="true" selected="false" bounds="[180,179][360,295]"/><node class="android.view.View" clickable="true" selected="false" bounds="[360,179][540,295]"/><node class="android.view.View" clickable="true" selected="false" bounds="[540,179][720,295]"/><node class="android.view.View" clickable="true" selected="false" bounds="[720,179][900,295]"/><node class="android.view.View" clickable="true" selected="false" bounds="[900,179][1080,295]"/>'+'</hierarchy>'
NOTIFICATION_TAB = '<hierarchy><node class="android.view.ViewGroup" content-desc="Notifications" clickable="true" enabled="true" bounds="[800,0][1000,100]"/></hierarchy>'
NOTIFICATIONS = '<hierarchy><node text="Notifications"/><node text="New" clickable="true" bounds="[0,200][1000,300]"/></hierarchy>'
COMPOSER = '<hierarchy><node class="android.widget.EditText" content-desc="What\'s on your mind?" clickable="true" enabled="true" bounds="[0,100][900,300]"/></hierarchy>'
COMPOSER_TYPED = '<hierarchy><node class="android.widget.EditText" text="Hello" bounds="[0,100][900,300]"/><node class="android.widget.Button" content-desc="Post" clickable="true" enabled="true" bounds="[800,0][1000,100]"/></hierarchy>'
POSTED = '<hierarchy><node text="Your post is now published"/></hierarchy>'
STORY_HOME = '<hierarchy><node class="android.widget.Button" content-desc="Friend&apos;s story, Unseen" clickable="true" bounds="[300,500][600,1000]"/></hierarchy>'
STORY_VIEW = '<hierarchy><node text="More options for this item"/><node content-desc="Reply to Friend"/><node content-desc="Like Reaction"/></hierarchy>'
ADD_FRIEND = '<hierarchy><node class="android.widget.Button" content-desc="Add Friend as a friend" clickable="true" bounds="[100,300][500,400]"/></hierarchy>'
REQUEST_SENT = '<hierarchy><node content-desc="Cancel request"/></hierarchy>'
PROFILE_OPTIONS = '<hierarchy><node class="android.widget.Button" content-desc="See options" clickable="true" bounds="[900,600][1050,750]"/><node class="android.widget.Button" text="Message" clickable="true" bounds="[400,600][800,750]"/></hierarchy>'
OPTIONS_ADD_FRIEND = '<hierarchy><node class="android.widget.Button" text="Add friend" content-desc="Add friend" clickable="true" bounds="[0,200][1080,328]"/><node class="android.widget.Button" text="Invite friends" clickable="true" bounds="[0,840][1080,968]"/></hierarchy>'
OPTIONS_REQUESTED = '<hierarchy><node class="android.widget.Button" text="Requested" content-desc="Requested" clickable="true" bounds="[0,200][1080,328]"/></hierarchy>'
JOIN_GROUP = '<hierarchy><node class="android.view.ViewGroup" content-desc="Join, Safe Test Group" clickable="true" bounds="[100,300][500,400]"/></hierarchy>'
JOINED_GROUP = '<hierarchy><node content-desc="View, Safe Test Group"/></hierarchy>'


class PriorityActionTests(unittest.TestCase):
    def test_dispatch_supports_five_priority_and_legacy_names(self):
        executor = ScenarioExecutor(FakeADB([]))
        mapping = {
            'HDTuongTacNewsfeed': 'execute_newsfeed', 'HDXemReel': 'execute_reels',
            'HDDocThongBao': 'execute_notifications', 'HDDangBaiTuong': 'execute_post_wall',
            'HDDangBaiNhom': 'execute_post_group', 'HDStory': 'execute_story',
            'HDKetBan': 'execute_add_friends', 'HDKetBanGoiY': 'execute_add_friends_suggestions',
            'HDKetBanTepUid': 'execute_add_friends_uid_file', 'HDThamGiaNhom': 'execute_join_groups',
        }
        for action, method in mapping.items():
            with patch.object(executor, method, return_value=True) as called:
                self.assertTrue(executor.execute_action(action, {'x': 1}))
                called.assert_called_once_with({'x': 1})
        with self.assertRaises(ValueError):
            executor.execute_action('unknown', {})

    def test_story_opens_unseen_story_and_never_reacts(self):
        adb = FakeADB([STORY_HOME, STORY_VIEW, STORY_VIEW, STORY_VIEW])
        executor = ScenarioExecutor(adb)
        with patch('src.core.scenario_executor.time.sleep', return_value=None):
            self.assertTrue(executor.execute_story({'count_from': 1, 'count_to': 1, 'watch_from': 1, 'watch_to': 1}))
        self.assertEqual([(450, 750)], adb.taps)

    def test_friend_uid_file_parser_deduplicates_and_rejects_missing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder, 'uids.txt')
            path.write_text('123456\n123456\nhttps://facebook.com/profile.php?id=987654\ninvalid', encoding='utf-8')
            self.assertEqual(['123456', '987654'], ScenarioExecutor._load_friend_uid_targets({'uid_file': str(path)}))
        self.assertIsNone(ScenarioExecutor._load_friend_uid_targets({'uid_file': 'missing-uids.txt'}))

    def test_uid_friend_request_uses_exact_options_menu_add_friend_once(self):
        adb = FakeADB([PROFILE_OPTIONS, PROFILE_OPTIONS, OPTIONS_ADD_FRIEND, OPTIONS_REQUESTED])
        with tempfile.TemporaryDirectory() as folder:
            executor = ScenarioExecutor(adb, account_uid='42', receipt_dir=folder)
            with patch.object(executor, '_open_deep_link', return_value=True), \
                 patch('src.core.scenario_executor.time.sleep', return_value=None), \
                 patch('src.core.scenario_executor.random.shuffle', return_value=None):
                self.assertTrue(executor.execute_add_friends({'type': 'uid_file', 'target_list': '123456', 'count_from': 1, 'count_to': 1, 'delay_from': 0, 'delay_to': 0}))
            self.assertEqual([(975, 675), (540, 264)], adb.taps)

    def test_uid_without_direct_or_options_button_reports_and_skips(self):
        profile = '<hierarchy><node class="android.widget.Button" text="Message" clickable="true" bounds="[400,600][800,750]"/></hierarchy>'
        adb = FakeADB([profile] * 5)
        executor = ScenarioExecutor(adb, account_uid='42')
        messages = []
        executor.log = messages.append
        with patch.object(executor, '_open_deep_link', return_value=True), \
             patch('src.core.scenario_executor.time.sleep', return_value=None), \
             patch('src.core.scenario_executor.random.shuffle', return_value=None):
            self.assertFalse(executor.execute_add_friends({'type': 'uid_file', 'target_list': '123456', 'count_from': 1, 'count_to': 1, 'delay_from': 0, 'delay_to': 0}))
        self.assertEqual([], adb.taps)
        self.assertTrue(any('Không có nút kết bạn' in message for message in messages))

    def test_add_friend_taps_once_and_requires_pending_receipt(self):
        adb = FakeADB([ADD_FRIEND, ADD_FRIEND, REQUEST_SENT])
        with tempfile.TemporaryDirectory() as folder:
            executor = ScenarioExecutor(adb, account_uid='42', receipt_dir=folder)
            with patch('src.core.scenario_executor.time.sleep', return_value=None):
                self.assertTrue(executor.execute_add_friends({'count_from': 1, 'count_to': 1}))
            self.assertEqual([(300, 350)], adb.taps)
            self.assertEqual(1, len(list(Path(folder).glob('friend_request_*.json'))))

    def test_join_group_taps_once_and_requires_pending_receipt(self):
        adb = FakeADB([JOIN_GROUP, JOINED_GROUP, JOINED_GROUP])
        with tempfile.TemporaryDirectory() as folder:
            executor = ScenarioExecutor(adb, account_uid='42', receipt_dir=folder)
            with patch('src.core.scenario_executor.time.sleep', return_value=None):
                self.assertTrue(executor.execute_join_groups({'count_from': 1, 'count_to': 1}))
            self.assertEqual([(300, 350)], adb.taps)
            self.assertEqual(1, len(list(Path(folder).glob('join_group_*.json'))))

    def test_notifications_navigates_via_verified_six_tab_structure_without_opening_item(self):
        adb = FakeADB([HOME, NOTIFICATIONS, NOTIFICATIONS])
        adb.shell = lambda command, timeout=30: 'Physical size: 1080x1920' if 'wm size' in command else ''
        executor = ScenarioExecutor(adb)
        with patch('src.core.scenario_executor.time.sleep', return_value=None):
            self.assertTrue(executor.execute_notifications({'count_from': 1, 'count_to': 1, 'delay_from': 0, 'delay_to': 0}))
        self.assertEqual([(810, 237)], adb.taps)

    def test_spin_text_and_image_material_validation(self):
        with patch('src.core.scenario_executor.random.choice', side_effect=lambda items: items[0]):
            self.assertEqual('Xin bạn', ScenarioExecutor._spin_text('{Xin|Chào} {bạn|mọi người}'))
            self.assertEqual('Mẫu một\nnhiều dòng', ScenarioExecutor._choose_post_text(
                'Mẫu một\nnhiều dòng\n|\nMẫu hai\nnhiều dòng', 1))
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'a.jpg').write_bytes(b'a')
            Path(folder, 'b.png').write_bytes(b'b')
            Path(folder, 'skip.txt').write_text('x')
            with patch('src.core.scenario_executor.random.sample', side_effect=lambda items, count: items[:count]):
                images = ScenarioExecutor._choose_images(folder, 2, 2)
            self.assertEqual({'a.jpg', 'b.png'}, {Path(item).name for item in images})

    def test_group_targets_accept_multiline_links_and_uids_and_deduplicate(self):
        targets = ScenarioExecutor._parse_group_targets({
            'custom_group_list': '123456\nhttps://www.facebook.com/share/g/ABC/?mibextid=x',
            'group_id': '123456',
        })
        self.assertEqual([
            ('uid:123456', 'https://www.facebook.com/groups/123456'),
            ('https://www.facebook.com/share/g/abc', 'https://www.facebook.com/share/g/ABC/?mibextid=x'),
        ], targets)

    def test_image_and_background_are_mutually_exclusive_before_any_tap(self):
        adb = FakeADB([])
        executor = ScenarioExecutor(adb)
        self.assertFalse(executor.execute_post_wall({
            'use_text': True, 'text': 'Hello', 'use_images': True,
            'image_path': 'missing', 'use_background': True,
        }))
        self.assertEqual([], adb.taps)

    def test_wall_publish_is_one_shot_and_writes_verified_receipt(self):
        adb = FakeADB([COMPOSER, COMPOSER, COMPOSER_TYPED, COMPOSER_TYPED, POSTED])
        with tempfile.TemporaryDirectory() as folder:
            executor = ScenarioExecutor(adb, account_uid='42', receipt_dir=folder)
            with patch('src.core.scenario_executor.time.sleep', return_value=None):
                self.assertTrue(executor.execute_post_wall({'text': 'Hello', 'count_from': 1, 'count_to': 1}))
            self.assertEqual([(450, 200), (900, 50)], adb.taps)
            self.assertEqual(['Hello'], adb.inputs)
            self.assertEqual(1, len(list(Path(folder).glob('post_*.json'))))

    def test_publish_never_uses_coordinate_fallback_when_composer_missing(self):
        adb = FakeADB([HOME] * 5)
        executor = ScenarioExecutor(adb, account_uid='42')
        with patch('src.core.scenario_executor.time.sleep', return_value=None):
            self.assertFalse(executor.execute_post_wall({'text': 'Hello'}))
        self.assertEqual([], adb.taps)

    def test_newsfeed_swipe_uses_live_screen_size_and_verifies_home(self):
        adb = FakeADB([HOME] * 8)
        adb.shell = lambda command, timeout=30: 'Physical size: 1080x1920' if 'wm size' in command else ''
        executor = ScenarioExecutor(adb)
        clock = iter([0.0 + i * 0.25 for i in range(100)])
        with patch.object(executor, 'wait_for_facebook_ready', return_value=True), patch('src.core.scenario_executor.time.time', side_effect=lambda: next(clock)), patch('src.core.scenario_executor.time.sleep', return_value=None):
            self.assertTrue(executor.execute_newsfeed({'time_from': 1, 'time_to': 1, 'delay_from': 0, 'delay_to': 0, 'like': False, 'comment': False}))
        self.assertTrue(adb.swipes)
        self.assertEqual((540, 1497, 540, 537, 400), adb.swipes[0])

    def test_newsfeed_fails_when_home_postcondition_is_lost(self):
        adb = FakeADB([HOME, '<hierarchy><node text="People you may know"/></hierarchy>'])
        adb.shell = lambda command, timeout=30: 'Physical size: 1080x1920' if 'wm size' in command else ''
        executor = ScenarioExecutor(adb)
        with patch('src.core.scenario_executor.time.sleep', return_value=None):
            self.assertFalse(executor.execute_newsfeed({'time_from': 1, 'time_to': 1, 'delay_from': 0, 'delay_to': 0, 'like': False, 'comment': False}))


if __name__ == '__main__': unittest.main()
