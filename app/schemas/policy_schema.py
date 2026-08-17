from typing import Optional, List
from pydantic import BaseModel, field_validator

class ExtractedField(BaseModel):
    status: str = "not_found"         
    value: Optional[str] = None        
    source_page: Optional[int] = None

    @field_validator("value", mode="before")
    @classmethod
    def coerce_value_to_string(cls, v):
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return str(v)
        if isinstance(v, list):
            return ", ".join(str(item) for item in v)
        return v


class InsurerInfo(BaseModel):
    insurer_name: ExtractedField = ExtractedField()
    tpa_name: ExtractedField = ExtractedField()
    is_gmc_policy: ExtractedField = ExtractedField()


class PreviousPolicyInfo(BaseModel):
    inception_date: ExtractedField = ExtractedField()
    renewal_date: ExtractedField = ExtractedField()
    policy_tenure: ExtractedField = ExtractedField()
    inception_premium: ExtractedField = ExtractedField()


class PolicyStructure(BaseModel):
    family_structure: ExtractedField = ExtractedField()
    sum_insured_tiers: List[str] = []


class Demographics(BaseModel):
    total_employees: ExtractedField = ExtractedField()
    total_spouses: ExtractedField = ExtractedField()
    total_children: ExtractedField = ExtractedField()
    total_parents: ExtractedField = ExtractedField()
    total_lives_covered: ExtractedField = ExtractedField()


class RoomRentHospitalization(BaseModel):
    room_rent_percentage: ExtractedField = ExtractedField()
    room_rent_max_limit: ExtractedField = ExtractedField()
    icu_percentage: ExtractedField = ExtractedField()
    icu_max_limit: ExtractedField = ExtractedField()
    pre_hospitalization_days: ExtractedField = ExtractedField()
    post_hospitalization_days: ExtractedField = ExtractedField()


class Maternity(BaseModel):
    nine_month_waiting_period: ExtractedField = ExtractedField()
    baby_day_one_cover: ExtractedField = ExtractedField()
    vaccination_coverage: ExtractedField = ExtractedField()
    normal_delivery_metro: ExtractedField = ExtractedField()
    normal_delivery_non_metro: ExtractedField = ExtractedField()
    c_section_metro: ExtractedField = ExtractedField()
    c_section_non_metro: ExtractedField = ExtractedField()


class WaitingPeriods(BaseModel):
    thirty_day_waiting_period: ExtractedField = ExtractedField()
    first_second_year_waiting_period: ExtractedField = ExtractedField()
    pre_existing_disease_waiting_period: ExtractedField = ExtractedField()


class OtherBenefits(BaseModel):
    day_care_expenses: ExtractedField = ExtractedField()
    opd_benefit: ExtractedField = ExtractedField()
    teleconsultation: ExtractedField = ExtractedField()
    pharmacy_discount: ExtractedField = ExtractedField()
    domiciliary_hospitalization: ExtractedField = ExtractedField()
    annual_health_checkup: ExtractedField = ExtractedField()
    modern_treatment: ExtractedField = ExtractedField()
    bariatric_treatment: ExtractedField = ExtractedField()
    psychiatric_treatment: ExtractedField = ExtractedField()
    ayush_treatment: ExtractedField = ExtractedField()
    lgbtq_coverage: ExtractedField = ExtractedField()
    live_in_partner_coverage: ExtractedField = ExtractedField()
    organ_donor_expenses: ExtractedField = ExtractedField()


class InfertilityAmbulance(BaseModel):
    infertility_treatment: ExtractedField = ExtractedField()
    surrogacy: ExtractedField = ExtractedField()
    ambulance_charges: ExtractedField = ExtractedField()
    air_ambulance_charges: ExtractedField = ExtractedField()


class BufferWaiver(BaseModel):
    corporate_buffer_limit: ExtractedField = ExtractedField()
    disease_wise_capping: ExtractedField = ExtractedField()
    waiver_conditions: ExtractedField = ExtractedField()


class GMCPolicyOutput(BaseModel):
    source_file: str
    insurer: InsurerInfo = InsurerInfo()
    previous_policy: PreviousPolicyInfo = PreviousPolicyInfo()
    policy_structure: PolicyStructure = PolicyStructure()
    demographics: Demographics = Demographics()
    room_rent_hospitalization: RoomRentHospitalization = RoomRentHospitalization()
    maternity: Maternity = Maternity()
    waiting_periods: WaitingPeriods = WaitingPeriods()
    other_benefits: OtherBenefits = OtherBenefits()
    infertility_ambulance: InfertilityAmbulance = InfertilityAmbulance()
    buffer_waiver: BufferWaiver = BufferWaiver()
    additional_notable_information: List[str] = []
    extraction_summary: dict = {}