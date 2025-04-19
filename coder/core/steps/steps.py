from enum import Enum

from coder.core.steps.development.development import Development
from coder.core.steps.entrypoint.entrypoint import Entrypoint
from coder.core.steps.healing.healing import Healing
from coder.core.steps.quality_assurance.quality_assurance import QualityAssurance
from coder.core.steps.specification.specification import Specification
from coder.core.steps.system_design.system_design import SystemDesign
from coder.core.steps.ui_design.ui_design import UIDesign


class StepType(str, Enum):
    NONE = "none"
    DEFAULT = "default"
    BUILD = "build"
    SPECIFICATION = "specification"
    SYSTEM_DESIGN = "system_design"
    DEVELOPMENT = "development"
    QUALITY_ASSURANCE = "quality_assurance"
    ENTRYPOINT = "entrypoint"
    UI_DESIGN = "ui_design"
    HEALING = "healing"


STEPS = {
    StepType.NONE: [],
    StepType.DEFAULT: [
        Specification,
        SystemDesign,
        UIDesign,
        Development,
        QualityAssurance,
        Entrypoint,
    ],
    StepType.BUILD: [
        Development,
        QualityAssurance,
        Entrypoint,
    ],
    StepType.SPECIFICATION: [Specification],
    StepType.SYSTEM_DESIGN: [SystemDesign],
    StepType.DEVELOPMENT: [Development],
    StepType.QUALITY_ASSURANCE: [QualityAssurance],
    StepType.ENTRYPOINT: [Entrypoint],
    StepType.UI_DESIGN: [UIDesign],
    StepType.HEALING: [Healing],
}
