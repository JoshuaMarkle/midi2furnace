# audio/synth.py
import collections
import numpy as np
import pygame

_INITIALIZED = False
_CACHE_MAX = 512
_cache = collections.OrderedDict()

WAVEFORMS = ("Square", "Sawtooth", "Triangle", "Pluck")


def _cache_get(key):
    try:
        _cache.move_to_end(key)
        return _cache[key]
    except KeyError:
        return None


def _cache_put(key, snd):
    _cache[key] = snd
    if len(_cache) > _CACHE_MAX:
        _cache.popitem(last=False)


def _to_sound(mono_i16, ch):
    if ch <= 1:
        return pygame.mixer.Sound(buffer=mono_i16.tobytes())
    stereo = np.column_stack([mono_i16] * ch).astype(np.int16)
    return pygame.mixer.Sound(buffer=stereo.tobytes())


def init_audio():
    global _INITIALIZED
    if _INITIALIZED and pygame.mixer.get_init():
        return

    gi = pygame.mixer.get_init()
    if not gi:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

    try:
        pygame.mixer.set_num_channels(64)
    except Exception:
        pass
    _INITIALIZED = True


def _make_wave(freq_hz, ms, volume, waveform):
    gi = pygame.mixer.get_init()
    if not gi:
        sr, _, ch = 44100, -16, 2
    else:
        sr, _, ch = gi

    n = max(1, int(sr * (ms / 1000.0)))
    freq_hz = max(1.0, float(freq_hz))
    amp = max(0.0, min(1.0, volume))

    t = np.arange(n, dtype=np.float64)
    period = sr / freq_hz

    if waveform == "Triangle":
        phase = np.fmod(t, period) / period
        mono = amp * 32767.0 * (4.0 * np.abs(phase - 0.5) - 1.0)

    elif waveform == "Sawtooth":
        phase = np.fmod(t, period) / period
        mono = amp * 32767.0 * (2.0 * phase - 1.0)

    elif waveform == "Pluck":
        p = max(1, int(period))
        duty = p // 4
        pulse = np.where(np.fmod(t, p) < duty, 1.0, -1.0)
        decay_s = min(ms / 1000.0, 0.3)
        env = np.exp(-t / (sr * decay_s))
        mono = amp * 32767.0 * pulse * env

    else:  # Square
        p = max(1, int(period))
        half = p // 2
        mono = np.where(np.fmod(t, p) < half, amp * 32767.0, -amp * 32767.0)

    mono_i16 = np.clip(mono, -32767, 32767).astype(np.int16)
    return _to_sound(mono_i16, ch)


def tone(freq_hz, ms, volume=0.2, waveform="Square"):
    gi = pygame.mixer.get_init()
    if gi:
        sr, _, ch = gi
    else:
        sr, ch = 44100, 2
    key = (int(freq_hz), int(ms), int(volume * 1000), sr, ch, waveform)
    snd = _cache_get(key)
    if snd is not None:
        return snd
    snd = _make_wave(freq_hz, ms, volume, waveform)
    _cache_put(key, snd)
    return snd
