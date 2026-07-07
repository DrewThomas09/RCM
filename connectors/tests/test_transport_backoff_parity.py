"""Behavioral parity of the 16 copy-pasted transport backoff cores.

The transports are deliberately self-contained copies (four stylistic
lineages exist), and history shows drift: the Retry-After clamp had to
be hand-swept "across seven connector transports" once already. This
suite pins the BEHAVIOR of ``_backoff_seconds`` identically for every
connector, so a future single-package fix that misses siblings fails
loudly — without forcing the copies to be byte-identical.

Contract pinned here:

* a numeric ``Retry-After`` wins, clamped to ``[0, backoff_cap_s]`` —
  negative/NaN values must never reach ``time.sleep`` (ValueError would
  abort the retry loop);
* a garbage / HTTP-date ``Retry-After`` falls through to exponential
  backoff with full jitter in ``[0, ceiling)``, ceiling capped at
  ``backoff_cap_s``.
"""
import importlib
import inspect
import math
import unittest

from .._spi import CONNECTOR_NAMES


def _transport_and_response(name):
    mod = importlib.import_module(f"connectors.{name}.transport")
    cls = next(c for _n, c in sorted(vars(mod).items())
               if inspect.isclass(c) and hasattr(c, "_backoff_seconds")
               and c.__module__ == mod.__name__)
    return cls(), mod.RawResponse


class TransportBackoffParityTests(unittest.TestCase):
    def _each(self):
        for name in CONNECTOR_NAMES:
            tr, raw_cls = _transport_and_response(name)
            yield name, tr, raw_cls

    def test_numeric_retry_after_wins_and_is_clamped(self):
        for name, tr, raw in self._each():
            resp = raw(status=429, headers={"retry-after": "7"})
            self.assertEqual(
                tr._backoff_seconds(0, resp, rand=lambda: 1.0), 7.0, name)
            # Enormous values clamp to the cap, never sleep for hours.
            resp = raw(status=429, headers={"retry-after": "999999"})
            self.assertEqual(
                tr._backoff_seconds(0, resp, rand=lambda: 1.0),
                tr.backoff_cap_s, name)
            # Negative must clamp to 0, not raise in time.sleep. (openfda,
            # the reference copy, returned -5.0 here until this suite.)
            resp = raw(status=429, headers={"retry-after": "-5"})
            self.assertEqual(
                tr._backoff_seconds(0, resp, rand=lambda: 1.0), 0.0, name)
            # NaN parses as float but must not leak to time.sleep either.
            resp = raw(status=429, headers={"retry-after": "nan"})
            got = tr._backoff_seconds(0, resp, rand=lambda: 1.0)
            self.assertTrue(math.isfinite(got) and got >= 0.0,
                            f"{name}: NaN retry-after produced {got!r}")

    def test_garbage_retry_after_falls_back_to_jittered_backoff(self):
        for name, tr, raw in self._each():
            resp = raw(status=429,
                       headers={"retry-after": "Fri, 31 Dec 2027 23:59:59"})
            got = tr._backoff_seconds(2, resp, rand=lambda: 1.0)
            ceiling = min(tr.backoff_cap_s, tr.backoff_base_s * 4)
            self.assertAlmostEqual(got, ceiling, msg=name)
            # Full jitter: rand()=0 → no sleep at all.
            self.assertEqual(
                tr._backoff_seconds(2, resp, rand=lambda: 0.0), 0.0, name)

    def test_no_response_uses_capped_exponential_backoff(self):
        for name, tr, raw in self._each():
            got = tr._backoff_seconds(50, None, rand=lambda: 1.0)
            self.assertAlmostEqual(got, tr.backoff_cap_s, msg=name)
            self.assertTrue(math.isfinite(got), name)


if __name__ == "__main__":
    unittest.main()
