from harness.config import benchmark_config, model_specs, select_models


def test_numeric_params_parse_as_numbers():
    for name, m in model_specs().items():
        assert m.get("params") is None or isinstance(m["params"], float), name
    assert isinstance(benchmark_config()["groups"]["small"]["max_parameters"], float)
    assert isinstance(benchmark_config()["seed"], int)


def test_group_selection_by_size_and_jev_inclusion():
    small = select_models(group="small")
    names = [m["name"] for m in small]
    assert "typesafe-jev-latest" in names and "kev-4b-qwen3.5" in names
    assert "kev-27b-qwen3.8" not in names
    assert "modernbert-sysone-149m" not in names          # disabled (blocker)
    assert all(m["params"] <= 4e9 for m in small if m.get("params"))
    assert "typesafe-jev-latest" not in [m["name"] for m in select_models(group="large",
                                                                          include_jev=False)]
