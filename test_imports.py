"""Test script to verify ag_pricing imports."""
import sys
sys.path.insert(0, 'packages/agents/src')
sys.path.insert(0, 'packages/contracts/src')

try:
    from ca_agents.ag_pricing.job_manager import InvalidJobTransitionError, JobStore, SurveyJob
    print('✓ job_manager import OK')
except Exception as e:
    print(f'✗ job_manager import FAILED: {e}')

try:
    from ca_agents.ag_pricing.orchestrator import run_catchment_price_survey
    print('✓ orchestrator import OK')
except Exception as e:
    print(f'✗ orchestrator import FAILED: {e}')

try:
    from ca_agents.ag_pricing.orchestrator_v2 import SurveyExecutionError, SurveyOrchestrator
    print('✓ orchestrator_v2 import OK')
except Exception as e:
    print(f'✗ orchestrator_v2 import FAILED: {e}')

try:
    from ca_agents.ag_pricing.qualifier import calculate_bayesian_rating, calculate_distance_decay_weight, compute_price_distribution, qualify_stores
    print('✓ qualifier import OK')
except Exception as e:
    print(f'✗ qualifier import FAILED: {e}')

try:
    from ca_agents.ag_pricing import __all__
    print(f'✓ __init__.py import OK, exports: {len(__all__)} symbols')
except Exception as e:
    print(f'✗ __init__.py import FAILED: {e}')
