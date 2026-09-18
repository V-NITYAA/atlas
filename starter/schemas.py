from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict


class RecordRef(BaseModel):
    domain: str
    usubjid: str
    seq: int

    model_config = ConfigDict(frozen=True, extra="allow")

    def __init__(self, *args, **kwargs):
        if args:
            if len(args) == 3:
                kwargs["domain"] = str(args[0])
                kwargs["usubjid"] = str(args[1])
                kwargs["seq"] = int(args[2])
            elif len(args) == 1 and isinstance(args[0], (tuple, list)) and len(args[0]) == 3:
                kwargs["domain"] = str(args[0][0])
                kwargs["usubjid"] = str(args[0][1])
                kwargs["seq"] = int(args[0][2])
        super().__init__(**kwargs)

    def __hash__(self):
        return hash((self.domain, self.usubjid, self.seq))

    def __eq__(self, other):
        if isinstance(other, RecordRef):
            return (self.domain, self.usubjid, self.seq) == (other.domain, other.usubjid, other.seq)
        if isinstance(other, (tuple, list)) and len(other) == 3:
            return (self.domain, self.usubjid, self.seq) == (other[0], other[1], other[2])
        return False

    def to_tuple(self):
        return (self.domain, self.usubjid, self.seq)


class Question(BaseModel):
    id: Optional[str] = Field(default=None, alias="question_id")
    question_id: Optional[str] = None
    question: Optional[str] = Field(default=None, alias="text")
    text: Optional[str] = None
    type: Optional[str] = None
    category: Optional[str] = None
    cut: Optional[int] = None
    protocol_version: Optional[int] = None
    usubjid: Optional[str] = None
    siteid: Optional[str] = None
    visit: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.id and self.question_id:
            self.id = self.question_id
        if not self.question_id and self.id:
            self.question_id = self.id
        if not self.question and self.text:
            self.question = self.text
        if not self.text and self.question:
            self.text = self.question


class Answer(BaseModel):
    question_id: Optional[str] = None
    answer: Any = None
    evidence: List[RecordRef] = Field(default_factory=list)
    confidence: float = 1.0
    reasoning: Optional[str] = None
    cut: Optional[int] = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)
