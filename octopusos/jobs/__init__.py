"""Jobs module for OctopusOS."""

from octopusos.jobs.memory_gc import MemoryGCJob
from octopusos.jobs.lead_scan import LeadScanJob

__all__ = ["MemoryGCJob", "LeadScanJob"]
