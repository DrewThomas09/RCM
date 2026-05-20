"""PHI tokenization for the healthcare snapshot module.

Uploaded 835/837 files carry patient/member identifiers (MRNs, member
IDs). Per the V2 plan §6 we tokenize these **before** the CCD is
persisted or rendered: raw MRNs never hit disk, never reach an LLM, and
never appear in the UI.

Design:
- ``HMAC-SHA256(salt, mrn)`` → a stable token. Deterministic for a
  given salt, so the same MRN in an 837 and its 835 resolves to the
  same token (matching still works) without storing the raw value.
- A per-project random ``salt`` defeats cross-project correlation and
  rainbow-table attacks on the (small) MRN space.
- ``source_hash`` is an unsalted SHA-256 — a non-reversible fingerprint
  used only to dedupe token rows; it is NOT a way back to the MRN.

Tokenization is applied as a non-invasive pass over a built CCD
(:func:`tokenize_ccd`) so the existing ingester and its 139 tests are
untouched; the upload flow calls ``ingest_dataset`` then ``tokenize_ccd``
before persistence.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from ..ingest.ccd import CanonicalClaimsDataset

_TOKEN_PREFIX = "PT"


def new_salt() -> str:
    """A fresh per-project salt (hex). Persist this with the project so
    re-ingests of the same target produce stable tokens."""
    return secrets.token_hex(16)


@dataclass
class PhiTokenizer:
    """Holds a project salt and turns raw identifiers into stable tokens."""
    salt: str = field(default_factory=new_salt)

    def token(self, raw: Optional[str]) -> Optional[str]:
        v = (raw or "").strip()
        if not v:
            return None
        if v.startswith(_TOKEN_PREFIX + "-"):
            return v  # already tokenized — idempotent
        digest = hmac.new(
            self.salt.encode("utf-8"), v.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        return f"{_TOKEN_PREFIX}-{digest[:16]}"

    @staticmethod
    def source_hash(raw: Optional[str]) -> Optional[str]:
        v = (raw or "").strip()
        if not v:
            return None
        return hashlib.sha256(v.encode("utf-8")).hexdigest()


@dataclass
class TokenizationResult:
    ccd: CanonicalClaimsDataset
    # token -> source_hash, for the patients_tokenized persistence table.
    tokens: Dict[str, str] = field(default_factory=dict)
    tokenized_rows: int = 0
    empty_patient_rows: int = 0


def tokenize_ccd(
    ccd: CanonicalClaimsDataset, tokenizer: PhiTokenizer
) -> TokenizationResult:
    """Replace every claim's raw ``patient_id`` with a stable token,
    in place, logging the transformation. Idempotent. Returns the
    distinct (token, source_hash) pairs for downstream persistence.

    Raw MRNs are discarded here — only the token survives on the CCD.
    The transformation log records that tokenization happened (rule
    ``phi_tokenize:patient``) but NOT the raw value, so the audit trail
    itself stays PHI-free.
    """
    tokens: Dict[str, str] = {}
    tokenized = 0
    empties = 0
    for claim in ccd.claims:
        raw = claim.patient_id
        if not (raw or "").strip():
            empties += 1
            ccd.log.log(
                ccd_row_id=claim.ccd_row_id,
                source_file=claim.source_file,
                source_row=claim.source_row,
                target_field="patient_id",
                source_value=None,
                coerced_value=None,
                rule="phi_tokenize:missing",
                severity="WARN",
                note="no patient identifier present to tokenize",
            )
            continue
        if str(raw).startswith(_TOKEN_PREFIX + "-"):
            continue  # already tokenized
        tok = tokenizer.token(raw)
        sh = tokenizer.source_hash(raw)
        if tok and sh:
            tokens[tok] = sh
        claim.patient_id = tok or ""
        tokenized += 1
        ccd.log.log(
            ccd_row_id=claim.ccd_row_id,
            source_file=claim.source_file,
            source_row=claim.source_row,
            target_field="patient_id",
            source_value="<redacted-phi>",
            coerced_value=tok,
            rule="phi_tokenize:patient",
            severity="INFO",
            note="raw MRN tokenized (HMAC-SHA256); raw value discarded",
        )
    return TokenizationResult(
        ccd=ccd, tokens=tokens,
        tokenized_rows=tokenized, empty_patient_rows=empties,
    )
