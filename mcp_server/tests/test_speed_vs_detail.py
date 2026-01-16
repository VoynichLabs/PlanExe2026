import unittest

from mcp_server.app import resolve_speed_vs_detail, SPEED_VS_DETAIL_DEFAULT


class TestResolveSpeedVsDetail(unittest.TestCase):
    def test_default(self):
        self.assertEqual(resolve_speed_vs_detail(None), SPEED_VS_DETAIL_DEFAULT)

    def test_fast_alias(self):
        self.assertEqual(resolve_speed_vs_detail({"speed_vs_detail": "fast"}), "fast_but_skip_details")

    def test_all_alias(self):
        self.assertEqual(resolve_speed_vs_detail({"speed": "all"}), "all_details_but_slow")

    def test_passthrough(self):
        self.assertEqual(resolve_speed_vs_detail({"speed_vs_detail": "ping_llm"}), "ping_llm")


if __name__ == "__main__":
    unittest.main()
