.PHONY: setup contracts dev test test-unit lint demo demo-local demo-reset seed seed-ops bench eval ab replay budget metrics llm-probe \
	docker-up docker-down docker-logs docker-smoke docker-ps docker-reset docker-seed-ops

setup:
	python -m pip install -e ./packages/contracts -e ./packages/solver -e ./packages/agents -e ./packages/gates -e ./packages/opsengine -e ./packages/playbook -e ./apps/api pytest httpx ruff pyyaml
	cd apps/web && npm install

contracts:
	python scripts/export_contracts.py

dev:
	docker compose -f infra/docker/compose.yml up --build

demo-local:
	python scripts/demo_api.py

demo: demo-local

demo-reset:
	docker compose -f infra/docker/compose.yml down -v
	docker compose -f infra/docker/compose.yml up --build -d

test:
	CA_AGENT_MODE=replay python -m pytest -q

test-unit:
	CA_AGENT_MODE=replay python -m pytest -q

lint:
	ruff check apps/api/src packages scripts
	cd apps/web && npm run lint

seed:
	python scripts/generate_fixture_data.py

# Nạp 6 bề mặt vận hành (việc treo · hộp thư · cẩm nang · hao phí · kiểm kê ·
# ghi nhận sửa) vào store. Idempotent; mọi bản ghi mang nhãn `mo_phong_fixture`.
seed-ops:
	python scripts/seed_operational.py

bench:
	python -m pip install -e ./packages/solver -e ./packages/playbook -q
	python scripts/solve_tuan.py
	python scripts/verify_hard.py

eval:
	CA_AGENT_MODE=replay python scripts/eval_ag_tkb.py
	CA_AGENT_MODE=replay python scripts/eval_ag_msg.py
	CA_AGENT_MODE=replay python -c "from fastapi.testclient import TestClient; from ca_api.interfaces.http.main import app; c=TestClient(app); t=c.post('/api/v1/auth/login', json={'username':'lan','password':'nhipquan'}).json()['token']; r=c.get('/api/v1/sop/golden', headers={'Authorization': f'Bearer {t}'}).json(); print('SOP', r['n'], r['moi_cau_co_nguon_hoac_chua_co'], r['co_cau_chua_co']); assert r['n']==20 and r['moi_cau_co_nguon_hoac_chua_co'] and r['co_cau_chua_co']"

llm-probe:
	python scripts/probe_llm.py

ab:
	python scripts/ab_report.py

# Bảy con số §18.2 cần quán thật, đo trên fixture ADR-012. Tất định: chạy lại
# cho cùng kết quả. Mọi bản ghi mang nhãn nguồn `mo_phong_fixture`.
metrics:
	python scripts/do_metrics.py

replay:
	@test -n "$(PHIEN)" || (echo "usage: make replay PHIEN=<idempotency-key>" && exit 1)
	CA_AGENT_MODE=replay python scripts/replay_orc.py "$(PHIEN)"

budget:
	@echo "budget stub — xem THIRD_PARTY.md; dùng OpenRouter dashboard khi bật live LLM"

# ── Docker toàn tuyến: postgres · redis · api · worker · web ──────────────────
#
# Gọi qua scripts/docker_stack.py, KHÔNG gọi `docker compose` trực tiếp.
# Lý do: nếu repo nằm trong thư mục có dấu (ví dụ D:\CA-CÔNG-BẰNG) thì BuildKit
# nhét đường dẫn vào header HTTP/2 và build vỡ ngay:
#   header key "x-docker-expose-session-sharedkey" contains value with
#   non-printable ASCII characters
# Wrapper tắt BuildKit, ghim tên project về ASCII, và ép stdout UTF-8.

docker-up:
	python scripts/docker_stack.py up

docker-down:
	python scripts/docker_stack.py down

docker-ps:
	python scripts/docker_stack.py ps

docker-logs:
	python scripts/docker_stack.py logs

docker-smoke:
	python scripts/docker_stack.py smoke

# Store ghi được của container nằm trong volume `nhipquan_var`; `make seed-ops`
# ở host chỉ chạm data/quan.db của máy dev. Muốn 6 bề mặt trên web Docker có dữ
# liệu thì nạp từ trong container bằng target này (sau `make docker-up`).
docker-seed-ops:
	python scripts/docker_stack.py seed-ops

docker-reset:
	python scripts/docker_stack.py reset
