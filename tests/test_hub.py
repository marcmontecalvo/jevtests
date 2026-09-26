from harness.hub import needs_base


def test_full_checkpoints_do_not_need_base():
    assert not needs_base(["config.json", "model.safetensors"])                        # laya, JevK5
    assert not needs_base(["model-00001-of-00004.safetensors", "config.json"])         # Qwen
    assert not needs_base(["model.safetensors-00001-of-00001.safetensors"])            # Qwen3.5
    assert not needs_base(["adapter/adapters.safetensors", "model.safetensors"])       # mpuig fused q8


def test_adapters_and_heads_need_base():
    assert needs_base(["adapter_config.json", "adapter_model.safetensors", "head.pt"])   # Kev
    assert needs_base(["package/checkpoint/adapter/adapter_model.safetensors"])          # Open-Jev
    assert needs_base(["adapter/model.safetensors"])                                     # adapter dir
    assert needs_base(["CLM_v0.1-8B.pt", "config.json"])                                 # CLM
