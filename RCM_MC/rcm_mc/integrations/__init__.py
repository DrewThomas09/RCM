"""Integrations package — CRM sync, CSV export, webhook dispatch,
PMS connectors, and diligence-vendor sockets.

Diligence-vendor sockets (``chart_audit``, ``contract_digitization``)
follow the adapter pattern:

- One ``Protocol`` declaring the data contract
- A ``ManualAdapter`` that reads/writes a local JSON file (always
  offline, always inspectable — the analyst's default path)
- A ``StubVendorAdapter`` documenting what an eventual vendor HTTP
  client will look like. Stubs raise on remote-fetch attempts
  rather than silently returning fake data.

No network I/O in the new modules. Replace the stub with a real
HTTP client when a vendor is selected.
"""
from .chart_audit import (  # noqa: F401
    ChartAuditAdapter,
    ChartAuditFinding,
    ChartAuditJob,
    ChartAuditReport,
    ManualChartAuditAdapter,
    StubVendorChartAuditAdapter,
)
from .contract_digitization import (  # noqa: F401
    ContractDigitizationAdapter,
    ContractDigitizationJob,
    ContractDigitizationReport,
    ContractExtraction,
    ManualContractDigitizationAdapter,
    StubVendorContractDigitizationAdapter,
)

__all__ = [
    "ChartAuditAdapter",
    "ChartAuditFinding",
    "ChartAuditJob",
    "ChartAuditReport",
    "ContractDigitizationAdapter",
    "ContractDigitizationJob",
    "ContractDigitizationReport",
    "ContractExtraction",
    "ManualChartAuditAdapter",
    "ManualContractDigitizationAdapter",
    "StubVendorChartAuditAdapter",
    "StubVendorContractDigitizationAdapter",
]
