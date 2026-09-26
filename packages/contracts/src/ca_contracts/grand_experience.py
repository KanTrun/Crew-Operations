"""Hợp đồng dữ liệu — Grand AI Experience Portfolio (plan 260920-1442 Phase 01).

Ranh giới sản phẩm: một bề mặt trải nghiệm AI độc lập (`/quanverse`) đọc dữ
liệu NHỊP QUÁN qua adapter chỉ-đọc. Module này KHÔNG import DB internals và
KHÔNG mô tả suy luận nghiệp vụ.

Nguyên tắc contracts-first (ADR-003): module + unit test phải tồn tại và được
validate TRƯỚC khi bất kỳ logic nghiệp vụ của phase 02-06 được viết.

ADR-002 (tất định): hợp đồng chỉ mô tả hình dạng dữ liệu; mọi con số do tầng
toán thuần ở `ca_agents` sinh ra, không phải LLM.

ADR-008 (con người quyết định): `ExperienceActionProposal` là kênh GỢI Ý — không
field nào mang nghĩa "thay đổi đã được áp dụng". Mọi mutation phải qua xác nhận
người dùng và ghi audit.

Invariants bắt buộc (plan Phase 01): proposal status, evidence refs, snapshot
hash, source, actor scope và consent KHÔNG được phép thiếu.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from ca_contracts.ops_predict import PositiveRuleStatus

# ── Enum nghiệp vụ ───────────────────────────────────────────────────────────


class ExperienceRole(StrEnum):
    """Vai trò trong không gian trải nghiệm (bản chiếu theo quyền hạn)."""

    KHACH = "khach"
    NHAN_VIEN = "nhan_vien"
    QUAN_LY = "quan_ly"
    CHU_QUAN = "chu_quan"


class ExperienceProposalStatus(StrEnum):
    """Vòng đời của một đề xuất (proposal) — mọi mutation là proposal trước."""

    DRAFT = "draft"
    READY = "ready"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ExperienceEventType(StrEnum):
    """Loại sự kiện trải nghiệm (đóng — fail-closed tại write boundary)."""

    ANCHOR_STATUS = "anchor_status"
    INCIDENT = "incident"
    PROCESS = "process"
    VOICE_NOTE = "voice_note"
    PRAISE = "praise"
    OPERATION_MEMORY = "operation_memory"
    DECISION = "decision"
    MODE_CHANGE = "mode_change"
    PROPOSAL_CONFIRMED = "proposal_confirmed"
    PROPOSAL_REJECTED = "proposal_rejected"


class MemoryConsentStatus(StrEnum):
    """Đồng thuận lưu trữ ký ức — không bao giờ ngầm định là đã đồng thuận."""

    REQUIRED = "required"
    GRANTED = "granted"
    REVOKED = "revoked"
    EXPIRED = "expired"


class MemoryVisibility(StrEnum):
    """Phạm vi hiển thị của ký ức (chiếu theo vai trò ở read boundary)."""

    PRIVATE = "private"
    STAFF = "staff"
    MANAGER = "manager"
    PUBLIC = "public"


class MemoryStatus(StrEnum):
    """Trạng thái ký ức. "Pending" là nhãn UI cho `draft`, không phải enum riêng."""

    DRAFT = "draft"
    CONFIRMED = "confirmed"
    SUPERSEDED = "superseded"
    DELETED = "deleted"


class ExperienceCapability(StrEnum):
    """Capability của bề mặt trải nghiệm — UI button không bao giờ là authorization."""

    READ = "experience.read"
    SIMULATE = "experience.simulate"
    PROPOSE = "experience.propose"
    CONFIRM = "experience.confirm"
    MEMORY_DELETE = "experience.memory.delete"
    MODE_ACTIVATE = "experience.mode.activate"

    @property
    def requires_manager(self) -> bool:
        return self in {
            ExperienceCapability.SIMULATE,
            ExperienceCapability.CONFIRM,
            ExperienceCapability.MEMORY_DELETE,
            ExperienceCapability.MODE_ACTIVATE,
        }


EXPERIENCE_ROLE_CAPABILITIES: dict[ExperienceRole, frozenset[str]] = {
    # R0_READ — mọi vai trò đã xác thực
    ExperienceRole.KHACH: frozenset({ExperienceCapability.READ.value}),
    ExperienceRole.NHAN_VIEN: frozenset(
        {ExperienceCapability.READ.value, ExperienceCapability.PROPOSE.value}
    ),
    # R2_CONFIRM + simulation — quản lý/chủ quán
    ExperienceRole.QUAN_LY: frozenset(
        {
            ExperienceCapability.READ.value,
            ExperienceCapability.SIMULATE.value,
            ExperienceCapability.PROPOSE.value,
            ExperienceCapability.CONFIRM.value,
            ExperienceCapability.MEMORY_DELETE.value,
            ExperienceCapability.MODE_ACTIVATE.value,
        }
    ),
    ExperienceRole.CHU_QUAN: frozenset(
        {
            ExperienceCapability.READ.value,
            ExperienceCapability.SIMULATE.value,
            ExperienceCapability.PROPOSE.value,
            ExperienceCapability.CONFIRM.value,
            ExperienceCapability.MEMORY_DELETE.value,
            ExperienceCapability.MODE_ACTIVATE.value,
        }
    ),
}


def experience_capabilities_for_role(role: str | ExperienceRole) -> frozenset[str]:
    """Fail-closed: vai trò lạ → rỗng (không ai được gọi capability)."""
    try:
        enum_role = ExperienceRole(role) if isinstance(role, str) else role
    except ValueError:
        return frozenset()
    return EXPERIENCE_ROLE_CAPABILITIES.get(enum_role, frozenset())


def experience_role_can(role: str | ExperienceRole, capability: str) -> bool:
    """Kiểm tra một vai trò có capability hay không. Fail-closed."""
    return capability in experience_capabilities_for_role(role)


# ── Event source (Literal duy trì tương thích TS) ─────────────────────────────

ExperienceEventSource = Literal["replay", "user", "system", "agent"]

# ── Spatial anchor ─────────────────────────────────────────────────────────────


class SpatialAnchor(BaseModel):
    """Một khu vực hoặc đồ vật trong quán, gắn toạ độ không gian."""

    anchor_id: str = Field(min_length=1)
    khu_vuc: str = Field(min_length=1)
    label: str = Field(min_length=1)
    x: float = Field(ge=-1000.0, le=1000.0)
    y: float = Field(ge=-1000.0, le=1000.0)
    z: float = Field(default=0.0, ge=-1000.0, le=1000.0)
    kind: str = Field(min_length=1)
    active: bool = True


# ── Experience event ──────────────────────────────────────────────────────────


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ExperienceEvent(BaseModel):
    """Sự kiện trải nghiệm gắn với anchor (nếu có), có nguồn và bằng chứng."""

    event_id: str = Field(min_length=1)
    event_type: str
    occurred_at: datetime
    actor_id: str | None = None
    role: ExperienceRole | None = None
    anchor_id: str | None = None
    payload: dict[str, object] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    source: ExperienceEventSource

    @field_validator("event_type")
    @classmethod
    def _event_type_must_be_known(cls, v: str) -> str:
        # Fail-closed tại write boundary: sự kiện lạ bị từ chối, không ghi nhận
        # "unknown" vào dữ liệu.
        known = cls._known_event_types()
        if v not in known:
            raise ValueError(f"event_type không nằm trong registry: {v}")
        return v

    @classmethod
    def _known_event_types(cls) -> frozenset[str]:
        return frozenset(e.value for e in ExperienceEventType)


class VoiceTurn(BaseModel):
    """Một lượt hội thoại voice/text — transcript + phản hồi + intent + proposal."""

    turn_id: str = Field(min_length=1)
    conversation_id: str = Field(min_length=1)
    transcript: str = Field(min_length=1, max_length=4000)
    response_text: str = ""
    audio_ref: str | None = None
    intent: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    proposal_id: str | None = None


class ExperienceMemory(BaseModel):
    """Ký ức vận hành — mọi bản ghi phải có owner, consent, visibility, retention."""

    memory_id: str = Field(min_length=1)
    anchor_id: str | None = None
    owner_scope: str = Field(min_length=1)
    content: str = Field(min_length=1, max_length=4000)
    source_event_ids: list[str] = Field(default_factory=list)
    consent_status: MemoryConsentStatus = MemoryConsentStatus.REQUIRED
    visibility: MemoryVisibility = MemoryVisibility.STAFF
    status: MemoryStatus = MemoryStatus.DRAFT
    retention_until: datetime | None = None
    created_by: str = ""


class ExperienceActionProposal(BaseModel):
    """Đề xuất hành động — bắt buộc trước mọi mutation. Có snapshot hash + evidence."""

    proposal_id: str = Field(min_length=1)
    action_type: str = Field(min_length=1)
    status: ExperienceProposalStatus = ExperienceProposalStatus.DRAFT
    snapshot_hash: str = Field(min_length=8)
    evidence_refs: list[str] = Field(default_factory=list)
    deterministic_result: dict[str, object] = Field(default_factory=dict)
    explanation: str = ""
    requested_by: str = Field(min_length=1)
    store_id: str = "quan_01"
    created_at: datetime = Field(default_factory=_utc_now)
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def _fail_closed_if_no_evidence(self) -> ExperienceActionProposal:
        # Invariant: proposal không bao giờ thiếu evidence refs (fail-closed).
        if not self.evidence_refs:
            raise ValueError("proposal phải có ít nhất một evidence_ref")
        return self


# ── War Room (Phase 02) ───────────────────────────────────────────────────────


class WarRoomScenarioType(StrEnum):
    """Kịch bản War Room — đóng, tham số hoá rõ ràng (không nhận tham số lạ)."""

    DEMAND_SURGE = "demand_surge"
    ADD_STAFF_TO_SHIFT = "add_staff_to_shift"
    REMOVE_STAFF_FROM_SHIFT = "remove_staff_from_shift"
    EQUIPMENT_OUTAGE = "equipment_outage"
    HEAVY_RAIN = "heavy_rain"
    LARGE_GROUP_ARRIVAL = "large_group_arrival"


class WarRoomScenario(BaseModel):
    """Một kịch bản "nếu... thì..." với tham số đã xác thực."""

    scenario_id: str = Field(min_length=1)
    loai: WarRoomScenarioType
    tham_so: dict[str, str | int | float | bool] = Field(default_factory=dict)


class WarRoomOption(BaseModel):
    """Một phương án tất định so sánh với baseline."""

    option_id: str = Field(min_length=1)
    scenario_id: str = Field(min_length=1)
    input_assumptions: dict[str, str | int | float | bool] = Field(default_factory=dict)
    outputs: dict[str, float] = Field(default_factory=dict)
    staffing: dict[str, int] = Field(default_factory=dict)
    load: dict[str, float] = Field(default_factory=dict)
    fairness_impact: dict[str, float] = Field(default_factory=dict)
    estimated_cost: float | None = None
    estimated_revenue: float | None = None
    risk: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    stale_data: bool = False
    constraint_violations: list[str] = Field(default_factory=list)
    labels: list[Literal["mo_phong", "uoc_tinh"]] = Field(default_factory=list)


class WarRoomComparison(BaseModel):
    """Kết quả so sánh đa phương án: baseline + ít nhất hai option."""

    simulation_id: str = Field(min_length=1)
    baseline_snapshot_hash: str = Field(min_length=8)
    baseline: dict[str, object] = Field(default_factory=dict)
    options: list[WarRoomOption] = Field(default_factory=list)


class ExperienceMode(StrEnum):
    """Chế độ vận hành của quán — kích hoạt cần proposal + xác nhận quản lý."""

    TROI_MUA = "troi_mua"
    GIO_CAO_DIEM = "gio_cao_diem"
    KHACH_DOAN = "khach_doan"
    THIEU_NHAN_SU = "thieu_nhan_su"
    QUAN_YEN_TINH = "quan_yen_tinh"
    DEM_NHAC = "dem_nhac"


class RobustProposalMixin(BaseModel):
    """Mixin chung: proposal luôn có snapshot hash + evidence + explanation."""

    snapshot_hash: str = Field(min_length=8)
    evidence_refs: list[str] = Field(default_factory=list)
    explanation: str = ""

    @model_validator(mode="after")
    def _fail_closed_if_no_evidence(self) -> RobustProposalMixin:
        # Invariant: proposal không bao giờ thiếu evidence refs (fail-closed).
        if not self.evidence_refs:
            raise ValueError("proposal phải có ít nhất một evidence_ref")
        return self


# ── Rule learning (Phase 04) ──────────────────────────────────────────────────


class RuleConditionKey(StrEnum):
    """Registry đóng của key điều kiện luật — cấm biểu thức thực thi tuỳ ý."""

    DAY_PART = "day_part"
    STATION = "station"
    SKILL = "skill"
    DEMAND_BAND = "demand_band"
    ABSENCE_TYPE = "absence_type"


RuleConditionValue = str | int | float | bool
RuleConditionMap = dict[str, RuleConditionValue]


class ShadowTestResult(BaseModel):
    """Kết quả shadow test — chỉ đọc, không bao giờ mutation sản xuất."""

    before: dict[str, float] = Field(default_factory=dict)
    after: dict[str, float] = Field(default_factory=dict)
    diffs: dict[str, float] = Field(default_factory=dict)
    hard_constraints_ok: bool = True
    fairness_delta: float = 0.0
    workload_delta: float = 0.0
    operational_delta: float = 0.0
    notes: list[str] = Field(default_factory=list)


class RuleCandidate(BaseModel):
    """Một luật đề xuất: điều kiện/effect có cấu trúc + câu từ + bằng chứng."""

    candidate_id: str = Field(min_length=1)
    condition: RuleConditionMap
    effect: RuleConditionMap
    sentence: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)
    counterexample_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source_kind: Literal["decision", "rescue", "twin", "episode"]
    playbook_status: PositiveRuleStatus = PositiveRuleStatus.DE_XUAT
    shadow_result: ShadowTestResult | None = None
    rule_version: str = "v1"
    created_from_snapshot_hash: str = Field(min_length=8)


# ── Shift Rescue (Phase 03) ───────────────────────────────────────────────────


class RescueCaseStatus(StrEnum):
    """State machine của một ca cứu hộ thiếu người."""

    REPORTED = "reported"
    RESOLVING = "resolving"
    CANDIDATES_READY = "candidates_ready"
    PROPOSED = "proposed"
    INVITED = "invited"
    RESPONDED = "responded"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class RescueCandidate(BaseModel):
    """Ứng viên thay ca hợp lệ/không hợp lệ kèm lý do từng ràng buộc."""

    candidate_id: str = Field(min_length=1)
    nv_id: str = Field(min_length=1)
    nv_ten: str = ""
    safe: bool = True
    reason_passes: list[str] = Field(default_factory=list)
    reason_blocks: list[str] = Field(default_factory=list)
    fairness_delta: float = 0.0
    added_hours: float = 0.0
    skill_coverage: dict[str, bool] = Field(default_factory=dict)


class RescueCase(BaseModel):
    """Một ca cứu hộ hoàn chỉnh (state machine)."""

    case_id: str = Field(min_length=1)
    store_id: str = "quan_01"
    status: RescueCaseStatus = RescueCaseStatus.REPORTED
    absence_nv_id: str = Field(min_length=1)
    shift_id: str = Field(min_length=1)
    reported_by: str = Field(min_length=1)
    schedule_snapshot_hash: str = Field(min_length=8)
    candidates: list[RescueCandidate] = Field(default_factory=list)
    selected_candidate_id: str | None = None


# ── Living Cafe OS (Phase 06) ─────────────────────────────────────────────────


class ZoneProjection(BaseModel):
    """Một khu vực trên Living Map — bản chiếu theo vai trò."""

    zone_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    active: bool = True
    load_signal: float = Field(default=0.0, ge=0.0, le=1.0)


class PublicEventProjection(BaseModel):
    """Một sự kiện công khai trên Living Map — không chứa dữ liệu riêng tư.

    `zone_id` gắn sự kiện với một khu vực trên mặt bằng. Để trống khi sự kiện
    là toàn quán: UI phải nói thẳng "không thuộc khu vực nào", không suy diễn.
    """

    event_id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    status: str = Field(min_length=1)
    occurred_at: datetime
    source: ExperienceEventSource
    summary: str = ""
    zone_id: str | None = None


class ModeProjection(BaseModel):
    """Một chế độ vận hành — kích hoạt cần proposal + xác nhận."""

    mode: ExperienceMode
    active: bool = False
    proposed_by: str | None = None
    proposal_status: ExperienceProposalStatus | None = None


class HorizonItem(BaseModel):
    """Một mục trong tầm nhìn 15 phút tới."""

    item_id: str = Field(min_length=1)
    kind: Literal["event", "signal", "handover", "mode_proposal"] = "event"
    title: str = Field(min_length=1)
    starts_at: datetime
    source: ExperienceEventSource


class DataQualityNotice(BaseModel):
    """Cảnh báo chất lượng dữ liệu — fixture, stale, unavailable phải hiển thị."""

    code: str = Field(min_length=1)
    level: Literal["info", "warning", "error"] = "info"
    message: str = Field(min_length=1)


class LivingCafeSnapshot(BaseModel):
    """Bản chụp toàn quán theo vai trò — server strip fields trước khi trả."""

    snapshot_id: str = Field(min_length=1)
    store_id: str = "quan_01"
    generated_at: datetime = Field(default_factory=_utc_now)
    role: ExperienceRole
    zones: list[ZoneProjection] = Field(default_factory=list)
    events: list[PublicEventProjection] = Field(default_factory=list)
    modes: list[ModeProjection] = Field(default_factory=list)
    next_horizon: list[HorizonItem] = Field(default_factory=list)
    data_quality: list[DataQualityNotice] = Field(default_factory=list)


# ── Trợ lý Quánverse — lớp tường thuật trên dữ liệu TẤT ĐỊNH ────────────────
#
# ADR-002 vẫn nguyên vẹn: mọi CON SỐ ở đây do tầng toán thuần ở `ca_agents`
# sinh ra (`quanverse_brief.py`), KHÔNG do LLM. LLM chỉ được diễn đạt lại
# `QuanverseBrief.facts` — nó không được thêm số, không được bịa kết luận.
# Vì vậy `grounded_refs` là bằng chứng máy kiểm được: rỗng nghĩa là "không có
# gì để nói", và `grounded=False` khi câu trả lời không bám vào ref nào.


class QuanversePage(StrEnum):
    """Trang Quánverse mà một bản tổng hợp/brief thuộc về."""

    LIVING_MAP = "living_map"
    WAR_ROOM = "war_room"
    SHIFT_RESCUE = "shift_rescue"
    RULES = "rules"
    SPATIAL_MEMORY = "spatial_memory"


class QuanverseMetric(BaseModel):
    """Một chỉ số đọc thẳng từ hệ thống (không suy diễn).

    `value=None` nghĩa là CHƯA CÓ DỮ LIỆU — khác hẳn 0. UI phải in "—" cho
    `None`, không được in "0" (quy ước số của dự án, xem plan hao hụt).
    """

    key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    value: float | None = None
    unit: str = ""
    tone: Literal["default", "ok", "warn", "danger"] = "default"


class QuanverseBrief(BaseModel):
    """Tóm tắt TẤT ĐỊNH của một trang Quánverse — nguồn duy nhất cho cả UI lẫn LLM.

    Bất biến: mỗi phần tử của `facts` phải truy được về `grounded_refs` (id bản
    ghi hệ thống: zone_id, event_id, candidate_id, anchor_id…). LLM nhận đúng
    khối này làm ngữ cảnh, nên không có đường nào để nó sinh số mới.
    """

    page: QuanversePage
    headline: str = Field(min_length=1)
    facts: list[str] = Field(default_factory=list)
    metrics: list[QuanverseMetric] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    grounded_refs: list[str] = Field(default_factory=list)
    data_quality: list[DataQualityNotice] = Field(default_factory=list)


class QuanverseAskRequest(BaseModel):
    """Câu hỏi cho Trợ lý Quánverse — luôn gắn với MỘT trang cụ thể."""

    page: QuanversePage
    question: str = Field(min_length=1, max_length=500)


class QuanverseAskResponse(BaseModel):
    """Câu trả lời có căn cứ cho một trang Quánverse.

    `grounded` là bằng chứng máy kiểm: `False` nghĩa là câu trả lời KHÔNG bám
    vào bản ghi nào của quán → UI phải nói rõ "chưa có dữ liệu", không được
    trình bày như một kết luận. `provider` cho biết ai diễn đạt (`replay` =
    tất định tại chỗ, tên provider = LLM thật).
    """

    page: QuanversePage
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    brief: QuanverseBrief
    citations: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    grounded: bool = False
    provider: str = "replay"