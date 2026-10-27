from ai_meeting_companion.llm.models import FAST_MODE_BETA, make_chat_model


def _payload(model):
    return model._get_request_payload([("human", "hi")])


def test_fast_mode_sends_beta_flag_and_speed_but_keeps_default_effort():
    payload = _payload(make_chat_model("claude-opus-5-5", "key", max_tokens=2048, fast=True))
    assert payload["betas"] == [FAST_MODE_BETA]
    assert payload["speed"] == "fast"
    assert "output_config" not in payload


def test_effort_is_sent_only_when_set():
    payload = _payload(make_chat_model("claude-opus-5-5", "key", fast=True, effort="high"))
    assert payload["output_config"] == {"effort": "high"}
    assert "output_config" not in _payload(make_chat_model("claude-sonnet-5-5", "key"))


def test_standard_mode_has_no_fast_fields():
    payload = _payload(make_chat_model("claude-haiku-5-5", "key"))
    assert not {"betas", "speed", "output_config"} & payload.keys()


def test_conversor_fast_and_effort_are_read_from_settings():
    from ai_meeting_companion import config

    env = {"ANTHROPIC_API_KEY": "k", "CONVERSOR_MODEL": "claude-opus-5-5", "CONVERSOR_FAST": "true", "CONVERSOR_EFFORT": "High"}
    settings = config.load_settings(env)
    assert settings.conversor_model == "claude-opus-5-5" and settings.conversor_fast is True
    assert settings.conversor_effort == "high"
    defaults = config.load_settings({"ANTHROPIC_API_KEY": "k"})
    assert defaults.conversor_fast is False and defaults.conversor_effort == ""
