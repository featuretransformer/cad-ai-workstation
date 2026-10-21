"""
CAD Assembly System — Core Module.
Provides data structures, decomposition, execution, and validation for multi-component mechanical assemblies.
"""
from .schema import (
    Placement3D,
    MatingInterface,
    ComponentSpec,
    AssemblySpec,
)

__all__ = [
    "Placement3D",
    "MatingInterface",
    "ComponentSpec",
    "AssemblySpec",
]
