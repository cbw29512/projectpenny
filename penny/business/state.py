"""Fixed experiment schema. Counts are not revenue."""
from enum import Enum

class Category(Enum):
    DIGITAL_PRODUCT="digital_product"
    CONTENT="content"
    SOFTWARE_UTILITY="software_utility"
    SERVICE_RESEARCH="service_research"

class Metric(Enum):
    QUALIFIED_INTEREST="qualified_interest"
    PROTOTYPE_CHECKS_PASSED="prototype_checks_passed"
    VALIDATED_REQUIREMENTS="validated_requirements"

class Action(Enum):
    APPROVE="approved"
    REJECT="rejected"
    START="started"
    MEASURE="measured"
    STOP="stopped"

MAX_REVIEW=604800
MAX_OPEN=32
MAX_COUNT=1_000_000
