from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, StrictBool, field_validator, model_validator


MAX_NEED_TEXT_LENGTH = 10_000
# Allow escaped Unicode and the rest of the intake envelope.
MAX_INTAKE_BODY_BYTES = 160_000


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Constraint(StrictModel):
    kind: Literal['cost', 'insurance', 'language', 'age', 'hours', 'documents',
                  'accessibility', 'access', 'food', 'service_area']
    value: str = Field(min_length=1, max_length=100)
    hard: StrictBool = True


ServiceChoice = Literal[
    'need:food.pantry', 'need:food.prepared_meals', 'need:housing.emergency_shelter',
    'need:utilities.bill_assistance', 'need:medical.general', 'need:mental_health.clinical',
    'need:employment.training_search', 'need:transportation.assistance',
]


class Intake(StrictModel):
    use_llm: StrictBool | None = None
    need_text: str = Field(default='', max_length=MAX_NEED_TEXT_LENGTH)
    selected_needs: list[ServiceChoice] = Field(default_factory=list, max_length=8)
    location: str | None = Field(default=None, max_length=120)
    constraints: list[Constraint] = Field(default_factory=list, max_length=12)
    limit: int = Field(default=10, ge=1, le=10, strict=True)

    @field_validator('need_text')
    @classmethod
    def trim_text(cls, value):
        return value.strip()

    @model_validator(mode='after')
    def require_service_or_text(self):
        if not self.selected_needs and not self.need_text:
            raise ValueError('Choose a service or describe a need.')
        return self

    # Offline mode is selected by the operator, never by an untrusted client.


class Extraction(StrictModel):
    _constraint_segments: list[tuple[str, list[str], list[Constraint]]] = PrivateAttr(default_factory=list)
    needs: list[str] = Field(max_length=96)
    urgency: Literal['emergency', 'today', 'soon', 'routine', 'unknown']
    location: str | None = Field(max_length=120)
    constraints: list[Constraint] = Field(max_length=12)
    safety: Literal['clear', 'crisis', 'uncertain']
    language: Literal['en', 'es']
    follow_up: list[Literal['need', 'food_type', 'location', 'diet', 'safety', 'eligibility']] = Field(max_length=2)
    out_of_scope: bool


class FeedbackInput(StrictModel):
    resource_id: int = Field(gt=0)
    helpful: StrictBool
    comment: str | None = Field(default=None, max_length=2000)
