"""stt.py: the ElevenLabs backend fails cleanly without a key, auto falls back to local, local reads the bundled wavs."""
import pytest

from pet.voice import stt


def test_guess_lang():
    assert stt.guess_lang("把橙色方块叼来") == "zh"
    assert stt.guess_lang("Come here.") == "en"
    assert stt.guess_lang("...") == ""


def test_elevenlabs_without_key_reports_not_raises(monkeypatch):
    monkeypatch.setattr(stt, "_keychain_key", lambda: None)
    be = stt.ElevenLabsSTT()
    assert not be.configured
    out = be.transcribe((stt.np.zeros(16000, "float32"), 16000))
    assert out["text"] == "" and out["backend"] == "elevenlabs"
    assert "Keychain" in out["error"] and stt.KEYCHAIN_SERVICE in out["error"]


def test_elevenlabs_http_error_is_a_dict(monkeypatch):
    import io
    import urllib.error

    monkeypatch.setattr(stt, "_keychain_key", lambda: "k")

    def boom(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {},
                                     io.BytesIO(b'{"detail": {"status": "invalid_api_key"}}'))

    monkeypatch.setattr(stt.urllib.request, "urlopen", boom)
    out = stt.ElevenLabsSTT().transcribe((stt.np.zeros(8000, "float32"), 16000))
    assert out["error"] == "401 invalid_api_key" and out["text"] == ""


def _has(model):
    return stt.MODEL_DIRS[model].is_dir()


@pytest.mark.skipif(not _has("sense-voice"), reason="sense-voice model not downloaded")
def test_local_sense_voice_reads_bundled_wavs():
    d = stt.MODEL_DIRS["sense-voice"] / "test_wavs"
    zh = stt.transcribe(d / "zh.wav", "local", "sense-voice")
    en = stt.transcribe(d / "en.wav", "local", "sense-voice")
    assert zh["lang"] == "zh" and any("一" <= c <= "鿿" for c in zh["text"])
    assert en["lang"] == "en" and en["text"]
    assert zh["backend"] == "local:sense-voice" and zh["latency_s"] < 5
    assert zh["words"] and all("word" in w for w in zh["words"])


@pytest.mark.skipif(not _has("sense-voice"), reason="sense-voice model not downloaded")
def test_auto_falls_back_to_local(monkeypatch):
    monkeypatch.setattr(stt, "_keychain_key", lambda: None)
    monkeypatch.setattr(stt, "_ELEVEN", None)
    d = stt.MODEL_DIRS["sense-voice"] / "test_wavs"
    out = stt.transcribe(d / "en.wav", "auto", "sense-voice")
    assert out["backend"] == "local:sense-voice" and out["fallback_from"].startswith("elevenlabs:")
