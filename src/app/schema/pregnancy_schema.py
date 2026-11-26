from pydantic import BaseModel, Field
from datetime import datetime
from app.enum.pregnancy_enum import PregnancyStatus
from app.schema.fetus_schema import FetusCreateDTO

# VO (ERD 테이블: pregnancies / 임신 정보)
class PregnancyVO(BaseModel):
    id: int

    pregnancy_previous_pregnancy: int = 0
    pregnancy_previous_birth: int = 0
    pregnancy_gestational_weeks: int
    pregnancy_gestational_reference: datetime | None = None
    pregnancy_due_date: datetime | None = None
    pregnancy_status: PregnancyStatus
    pregnancy_ended_on: datetime | None = None
    pregnancy_code: str

    user_id: int

class PregnancyCreateDTO(BaseModel):
    pregnancy_previous_pregnancy: int = Field(default=0, ge=0)  # 이전 임신 횟수 (0 이상)
    pregnancy_previous_birth: int = Field(default=0, ge=0)  # 이전 출산 횟수 (0 이상)
    pregnancy_gestational_weeks: int = Field(ge=1, le=42)  # 등록 당시 임신 주수 (1~42)
    pregnancy_gestational_reference: datetime | None = None
    pregnancy_due_date: datetime | None = None

    fetuses: list[FetusCreateDTO] = Field(min_length=1)  # 태아 최소 1명 (쌍둥이 등 여러 명 가능)


class PregnancyUpdateDTO(BaseModel):
    pregnancy_previous_pregnancy: int = 0
    pregnancy_previous_birth: int = 0
    pregnancy_gestational_weeks: int
    pregnancy_gestational_reference: datetime | None = None
    pregnancy_due_date: datetime | None = None
    pregnancy_status: PregnancyStatus
    
    fetuses: list[FetusCreateDTO] = Field(min_length=1)