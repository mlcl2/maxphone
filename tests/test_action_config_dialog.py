import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication
from src.gui.action_config_dialog import ActionConfigDialog


_APP = QApplication.instance() or QApplication([])


class ActionConfigDialogLegacySchemaTests(unittest.TestCase):
    def dialog(self, action, config=None):
        return ActionConfigDialog(None, action, action, config)

    def test_notifications_defaults_and_fields(self):
        dialog = self.dialog("notifications")
        self.assertEqual({
            "count_from": 1, "count_to": 1, "delay_from": 1,
            "delay_to": 1, "delete_spam_notifications": False,
        }, dialog.get_config())
        for name in ("spin_count_from", "spin_count_to", "spin_delay_from",
                     "spin_delay_to", "cb_delete_spam_notifications"):
            self.assertTrue(hasattr(dialog, name), name)

    def test_notifications_reads_legacy_aliases_and_round_trips(self):
        dialog = self.dialog("notifications", {
            "nudSoLuongFrom": 2, "nudSoLuongTo": 7,
            "nudDelayFrom": 3, "nudDelayTo": 9, "ckbXoaThongBaoSpam": True,
        })
        self.assertEqual({
            "count_from": 2, "count_to": 7, "delay_from": 3,
            "delay_to": 9, "delete_spam_notifications": True,
        }, dialog.get_config())

    def test_post_wall_full_legacy_schema_round_trip(self):
        legacy = {
            "nudSoLuongFrom": 2, "nudSoLuongTo": 4,
            "nudKhoangCachFrom": 6, "nudKhoangCachTo": 12,
            "ckbVanBan": True, "ckbUseBackground": True,
            "ckbXoaNguyenLieuDaDung": True, "txtNoiDung": "a\n|\nb",
            "typeNganCach": 1, "ckbAnh": True, "txtPathAnh": "C:/pics",
            "nudSoLuongAnhFrom": 2, "nudSoLuongAnhTo": 5,
            "ckbDangLink": True, "txtLinkShare": "https://example.test",
            "ckbXoaLink": True,
        }
        dialog = self.dialog("post_wall", legacy)
        expected = {
            "count_from": 2, "count_to": 4, "interval_from": 6,
            "interval_to": 12, "use_text": True, "use_background": False,
            "delete_used_content": True, "text": "a\n|\nb", "separator_type": 1,
            "use_images": True, "image_path": "C:/pics", "image_count_from": 2,
            "image_count_to": 5, "post_link": True,
            "share_links": "https://example.test", "remove_link_preview": True,
        }
        self.assertEqual(expected, dialog.get_config())
        for name in ("spin_interval_from", "cb_use_text", "cb_use_background",
                     "txt_post", "spin_separator_type", "cb_use_images",
                     "txt_image_path", "cb_post_link", "txt_share_links"):
            self.assertTrue(hasattr(dialog, name), name)

    def test_post_group_full_legacy_schema_round_trip(self):
        legacy = {
            "nudSoLuongFrom": 2, "nudSoLuongTo": 3,
            "nudKhoangCachFrom": 4, "nudKhoangCachTo": 8, "typeNhom": 2,
            "ckbChiShareNhomKKD": True, "ckbUuTienShareNhomNhieuThanhVien": True,
            "ckbBackupDanhSachNhom": True, "ckbKhongShareTrungNhom": True,
            "ckbChiShareNhomThuocDanhSach": True, "lstNhomTuNhap": "1\n2",
            "txtIdNhomChiDinh": "99", "ckbTuDongXoaUid": True,
            "txtTenNhom": "New group", "ckbVanBan": True,
            "ckbUseBackground": True, "ckbXoaNguyenLieuDaDung": True,
            "txtNoiDung": "hello", "typeNganCach": 0, "ckbAnh": True,
            "txtPathAnh": "D:/img", "nudSoLuongAnhFrom": 1,
            "nudSoLuongAnhTo": 3, "ckbDangLink": True,
            "txtLinkShare": "links", "ckbXoaLink": True, "ckbEvent": True,
            "txtEvent": "event", "ckbXuatLinkBaiViet": True,
        }
        dialog = self.dialog("post_group", legacy)
        config = dialog.get_config()
        self.assertEqual({
            "count_from", "count_to", "interval_from", "interval_to", "group_type",
            "only_unmoderated_groups", "prioritize_large_groups", "backup_group_list",
            "avoid_duplicate_groups", "only_listed_groups", "custom_group_list",
            "group_id", "auto_remove_group_id", "new_group_name", "use_text",
            "use_background", "delete_used_content", "text", "separator_type",
            "use_images", "image_path", "image_count_from", "image_count_to",
            "post_link", "share_links", "remove_link_preview", "use_event",
            "event_text", "export_post_links",
        }, set(config))
        self.assertEqual(2, config["group_type"])
        self.assertEqual("1\n2", config["custom_group_list"])
        self.assertEqual("99", config["group_id"])
        self.assertTrue(config["export_post_links"])

    def test_post_defaults_are_complete(self):
        wall = self.dialog("post_wall").get_config()
        group = self.dialog("post_group").get_config()
        self.assertEqual(16, len(wall))
        self.assertEqual(29, len(group))
        self.assertEqual(0, wall["separator_type"])
        self.assertEqual(0, group["group_type"])
        self.assertTrue(wall["use_text"])
        self.assertFalse(group["use_event"])


if __name__ == "__main__":
    unittest.main()
