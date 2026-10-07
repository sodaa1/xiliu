"""Capability discovery without eagerly loading external content."""

from xiliu.capabilities.manager import CapabilityManager
from xiliu.capabilities.models import CapabilityRef, CapabilitySpec

__all__ = ["CapabilityManager", "CapabilityRef", "CapabilitySpec"]
