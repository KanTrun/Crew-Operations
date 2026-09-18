"""HTTP router — Self-Explaining System (Causal Memory).

Nguồn: `plans/260918-y-tuong-dot-pha-nho.md` mục 3.

Endpoints:
- POST /api/v1/ops/explain — trả chuỗi nhân quả cho câu hỏi "tại sao"
- GET  /api/v1/ops/explain/chains — danh sách chuỗi nhân quả đã tạo
"""

from __future__ import annotations

from typing import Annotated, Any

from ca_agents.ag_explain import answer_reflection, build_causal_chain
from fastapi import APIRouter, Header
from pydantic import BaseModel, Field

from ca_api.interfaces.http.sprint3 import _require_role
from ca_api.persist import kv_get, kv_mutate

router = APIRouter(tags=["ops_explain"])


class ExplainBody(BaseModel):
    cau_hoi: str = Field(min_length=1, max_length=500)


class ReflectBody(BaseModel):
    cau_hoi: str = Field(min_length=1, max_length=500)


@router.post("/api/v1/ops/explain")
def explain_endpoint(
    body: ExplainBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Trả chuỗi nhân quả cho câu hỏi "tại sao" (tất định, có bằng chứng)."""
    _require_role(authorization)

    # Đọc dữ liệu thật từ KV store
    luat_list = kv_get("cam_nang", []) or kv_get("ops_predict_rules", [])
    audit_list = kv_get("audit", []) or []
    ket_qua_list = kv_get("ops_twin_scenarios", []) or []

    chain = build_causal_chain(
        cau_hoi=body.cau_hoi,
        luat_list=luat_list,
        audit_list=audit_list,
        ket_qua_list=ket_qua_list,
    )
    chain_dict = chain.model_dump(mode="json")

    def mut_chains(cur: list[dict[str, Any]]) -> list[dict[str, Any]]:
        res = [c for c in cur if c.get("chain_id") != chain.chain_id]
        res.insert(0, chain_dict)
        return res

    kv_mutate("ops_explain_chains", mut_chains, [])
    return {"ok": True, "chain": chain_dict}


@router.get("/api/v1/ops/explain/chains")
def list_chains(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Lấy danh sách chuỗi nhân quả đã tạo."""
    _require_role(authorization)
    chains = kv_get("ops_explain_chains", [])
    return {"items": chains}


@router.post("/api/v1/ops/reflect")
def reflect_endpoint(
    body: ReflectBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Suy ngẫm nguyên nhân gốc từ episodic memory (tất định, không LLM)."""
    _require_role(authorization)

    # Đọc episodes từ KV store (phàn nàn, doanh thu, sự cố...)
    rows = kv_get("ops_episodes", []) or []
    result = answer_reflection(cau_hoi=body.cau_hoi, rows=rows)
    return {"ok": True, "result": result.model_dump(mode="json")}