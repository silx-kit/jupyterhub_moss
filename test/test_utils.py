import pytest

from jupyterhub_moss.utils import parse_gpu_resource


@pytest.mark.parametrize(
    "gres,expected_type,expected_count",
    [
        # Single GPU
        ("gpu:model:2", "model", 2),
        ("gpu:brand_model-pcie.10:2(S:0-1)", "brand_model-pcie.10", 2),
        # Multiple GPUs
        ("gpu:modelA:1,gpu:modelB:3", "modelA", 1),
        ("gpu:modelA:6(S:0-1),gpu:1g.10gb:28(S:0-1)", "modelA", 6),
        # Mixed GPU/other resources
        ("other:nameA:2,gpu:modelA:3,other:nameB:2", "modelA", 3),
    ],
)
def test_parse_gpu_gres(gres, expected_type, expected_count):
    """Test parse_gpu_gres function of valid GPU resources"""
    generated_template, generated_count = parse_gpu_resource(gres)
    assert generated_template == f"gpu:{expected_type}:{{}}"
    assert int(generated_count) == expected_count


@pytest.mark.parametrize("gres", ["(null)", "other:name:2"])
def test_parse_gpu_gres_failed(gres):
    """Test cases where parse_gpu_gres raises an exception"""
    with pytest.raises(ValueError):
        parse_gpu_resource(gres)
