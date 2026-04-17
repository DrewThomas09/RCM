"""Tests for bulk notes CSV upload (Brick 112)."""
from __future__ import annotations

import io
import os
import tempfile
import unittest
import urllib.request as _u

from rcm_mc.deals.deal_notes import import_notes_csv, list_notes
from rcm_mc.portfolio.store import PortfolioStore


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


def _write_csv(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class TestImportNotesCsv(unittest.TestCase):
    def test_basic_ingest(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            csv_path = os.path.join(tmp, "n.csv")
            _write_csv(csv_path, (
                "deal_id,body,author\n"
                "ccf,board meeting,AT\n"
                "aaa,q1 close discussion,\n"
            ))
            summary = import_notes_csv(store, csv_path)
            self.assertEqual(summary["rows_ingested"], 2)
            self.assertEqual(summary["rows_skipped"], 0)
            self.assertEqual(len(list_notes(store)), 2)

    def test_skips_empty_body_and_missing_deal_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            csv_path = os.path.join(tmp, "n.csv")
            _write_csv(csv_path, (
                "deal_id,body,author\n"
                "ccf,good,AT\n"
                ",no-deal-id,AT\n"
                "aaa,,AT\n"
            ))
            summary = import_notes_csv(store, csv_path)
            self.assertEqual(summary["rows_ingested"], 1)
            self.assertEqual(summary["rows_skipped"], 2)
            self.assertEqual(len(summary["errors"]), 2)

    def test_missing_columns_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            csv_path = os.path.join(tmp, "n.csv")
            _write_csv(csv_path, "deal_id,author\nccf,AT\n")
            with self.assertRaises(ValueError):
                import_notes_csv(store, csv_path)

    def test_missing_file_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            with self.assertRaises(FileNotFoundError):
                import_notes_csv(store, os.path.join(tmp, "does_not_exist.csv"))


class TestNotesUploadHttp(unittest.TestCase):
    def _start(self, tmp):
        import socket as _socket, threading, time as _time
        from rcm_mc.server import build_server
        s = _socket.socket(); s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]; s.close()
        server, _ = build_server(port=port,
                                 db_path=os.path.join(tmp, "p.db"))
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start(); _time.sleep(0.05)
        return server, port

    def _multipart(self, filename: str, content: bytes):
        boundary = "----WebKitFormBoundaryRcmMcNotesTest"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: text/csv\r\n\r\n"
        ).encode()
        body += content + b"\r\n"
        body += f"--{boundary}--\r\n".encode()
        ct = f"multipart/form-data; boundary={boundary}"
        return body, ct

    def test_post_upload_notes_happy_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                csv = (
                    b"deal_id,body,author\n"
                    b"ccf,urgent covenant reset,AT\n"
                    b"aaa,quarterly call,\n"
                )
                body, ct = self._multipart("notes.csv", csv)
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/upload-notes",
                    data=body, method="POST",
                    headers={"Content-Type": ct},
                )
                with _u.urlopen(req) as r:
                    html_body = r.read().decode()
                    self.assertIn("Notes upload complete", html_body)
                    self.assertIn("Notes ingested", html_body)
                    self.assertIn("2", html_body)

                # Verify notes landed
                store = PortfolioStore(os.path.join(tmp, "p.db"))
                self.assertEqual(len(list_notes(store)), 2)
            finally:
                server.shutdown(); server.server_close()

    def test_upload_page_has_notes_form(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/upload") as r:
                    body = r.read().decode()
                    self.assertIn("Upload notes", body)
                    self.assertIn('action="/api/upload-notes"', body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
