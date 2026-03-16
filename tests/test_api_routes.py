from __future__ import annotations

import unittest

from fastapi import HTTPException

from question_service.app.api.routes import _normalize_isbn


class ApiRouteUtilityTests(unittest.TestCase):
    def test_normalize_isbn_accepts_hyphenated(self):
        self.assertEqual("9780141439600", _normalize_isbn("978-0141439600"))

    def test_normalize_isbn_rejects_invalid(self):
        with self.assertRaises(HTTPException):
            _normalize_isbn("abc123")


if __name__ == "__main__":
    unittest.main()
