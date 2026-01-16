import asyncio
import unittest
import zipfile
from io import BytesIO

from mcp_server.app import (
    REPORT_FILENAME,
    build_report_artifact_uri,
    extract_file_from_zip_bytes,
    handle_list_tools,
    list_files_from_zip_bytes,
)


class TestReportTool(unittest.TestCase):
    def test_report_artifact_uri(self):
        session_id = "pxe_2025_01_01__abcd1234"
        expected_uri = f"planexe://sessions/{session_id}/out/{REPORT_FILENAME}"
        self.assertEqual(build_report_artifact_uri(session_id), expected_uri)

    def test_report_tool_listed(self):
        tools = asyncio.run(handle_list_tools())
        tool_names = {tool.name for tool in tools}
        self.assertIn("planexe.report.read", tool_names)

    def test_zip_helpers(self):
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(REPORT_FILENAME, "<html>ok</html>")
            zip_file.writestr("001-2-plan.txt", "Plan prompt")
        zip_bytes = buffer.getvalue()

        files = list_files_from_zip_bytes(zip_bytes)
        self.assertIn(REPORT_FILENAME, files)
        self.assertIn("001-2-plan.txt", files)

        report_bytes = extract_file_from_zip_bytes(zip_bytes, REPORT_FILENAME)
        self.assertEqual(report_bytes, b"<html>ok</html>")


if __name__ == "__main__":
    unittest.main()
