from __future__ import annotations

import re
from typing import Dict, Optional

from pydantic import (
    constr,
    field_validator,
    BaseModel,
    ConfigDict,
    FieldValidationInfo,
    NonNegativeInt,
    PositiveInt,
    RootModel,
)

# Validators


def check_match_gpu(v: Optional[int], info: FieldValidationInfo) -> Optional[int]:
    if v is not None and v > 0 and info.data.get("gpu") == "":
        return 0  # GPU explicitly disabled
    return v


# models


class PartitionResources(BaseModel, frozen=True, extra="allow"):
    """SLURM partition required resources information

    This information retrieved from SLURM is used to constraint user's selection.
    Extra fields (e.g., as in :class:`PartitionAllResources`) can be used to display
    information about available resources.
    """

    max_nprocs: PositiveInt
    max_mem: PositiveInt
    gpu: str
    max_ngpus: NonNegativeInt
    max_runtime: PositiveInt

    # validators
    _check_match_gpu = field_validator("max_ngpus")(check_match_gpu)


class PartitionAllResources(PartitionResources, frozen=True, extra="forbid"):
    """SLURM partition resources information

    Extends resource constraints information with information
    used to display available resources.
    """

    nnodes_total: NonNegativeInt
    nnodes_idle: NonNegativeInt
    ncores_total: NonNegativeInt
    ncores_idle: NonNegativeInt


class JupyterEnvironment(BaseModel, frozen=True, extra="forbid"):
    """Single Jupyter environement description"""

    add_to_path: bool = True
    # See https://github.com/pydantic/pydantic/issues/156 for type: ignore
    description: constr(strip_whitespace=True, min_length=1)  # type: ignore[valid-type]
    path: str = ""
    modules: str = ""
    prologue: str = ""

    # validators
    @field_validator("modules")
    def check_path_or_mods(cls, v: str, info: FieldValidationInfo) -> str:
        if not v and not info.data.get("path"):
            raise ValueError("Jupyter environment path or modules is required")
        return v


class PartitionConfig(BaseModel, frozen=True, extra="forbid"):
    """Information about partition description and available environments"""

    architecture: str = ""
    description: str = ""
    jupyter_environments: Dict[str, JupyterEnvironment]
    simple: bool = True


class PartitionInfo(PartitionConfig, PartitionResources):
    """Complete information about a partition: config and resources"""

    model_config = ConfigDict(frozen=True, extra="allow")


class _PartitionTraits(PartitionConfig, frozen=True, extra="forbid"):
    """Configuration of a single partition passed as ``partitions`` traits"""

    gpu: Optional[str] = None
    max_ngpus: Optional[int] = None
    max_nprocs: Optional[int] = None
    max_runtime: Optional[int] = None

    # validators
    _check_match_gpu = field_validator("max_ngpus")(check_match_gpu)

    @field_validator("max_ngpus")
    def check_is_positive_or_none(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("Value must be positive")
        return v

    @field_validator("max_nprocs", "max_runtime")
    def check_is_strictly_positive_or_none(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("Value must be strictly positive")
        return v


class PartitionsTrait(RootModel):
    """Configuration passed as ``partitions`` trait"""

    root: Dict[str, _PartitionTraits]

    model_config = ConfigDict(frozen=True)

    def model_dump(self, *args, **kwargs):
        return {k: v.model_dump(*args, **kwargs) for k, v in self.root.items()}

    def items(self):
        return self.root.items()


_MEM_REGEXP = re.compile("^[0-9]*([0-9]+[KMGT])?$")
"""Memory input regular expression"""


class UserOptions(BaseModel):
    """Options passed as `Spawner.user_options`"""

    # Options received through the form or GET request
    partition: str
    runtime: str = ""
    nprocs: PositiveInt = 1
    memory: str = ""
    reservation: str = ""
    ngpus: NonNegativeInt = 0
    options: str = ""
    output: str = "/dev/null"
    environment_id: str = ""
    environment_path: str = ""
    environment_modules: str = ""
    default_url: str = ""
    root_dir: str = ""
    # Extra fields
    gres: str = ""
    prologue: str = ""

    @classmethod
    def parse_formdata(cls, formdata: dict[str, list[str]]) -> UserOptions:
        # Those keys should not come from the request, they are set later by the spawner
        excluded_keys = "gres", "prologue"
        fields = {
            k: v[0].strip() for k, v in formdata.items() if k not in excluded_keys
        }

        # Compatibility with mem query param renamed memory
        if "mem" in fields and "memory" not in fields:
            fields["memory"] = fields["mem"]

        # Convert output boolean query param to file pattern
        fields["output"] = (
            "slurm-%j.out" if fields.get("output", "false") == "true" else "/dev/null"
        )
        return cls.model_validate(fields)

    @field_validator(
        "partition",
        "runtime",
        "memory",
        "reservation",
        "options",
        "output",
        "environment_id",
        "environment_path",
        "environment_modules",
        "default_url",
        "root_dir",
    )
    def has_no_newline(cls, v: str) -> str:
        if "\n" in v:
            raise ValueError("Must not contain newline")
        return v

    @field_validator("default_url")
    def is_absolute_path(cls, v: str) -> str:
        if v and not v.startswith("/"):
            raise ValueError("Must start with /")
        return v

    @field_validator("runtime")
    def check_timelimit(cls, v: str) -> str:
        from .utils import parse_timelimit  # avoid circular imports

        if v:
            parse_timelimit(v)  # Raises exception if malformed
        return v

    @field_validator("memory")
    def check_memory(cls, v: str) -> str:
        if v and _MEM_REGEXP.match(v) is None:
            raise ValueError("Error in memory syntax")
        return v
