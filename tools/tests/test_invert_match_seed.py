import soundfile as sf
import torch

from invert.model import InverseModel
from match.audio import SAMPLE_RATE
from match.bfxr_io import ParamSpace
from match.match import main


def _write_random_ckpt(path, version: int = 1) -> None:
    space = ParamSpace()
    m = InverseModel(version=version)
    torch.save(
        {
            "model_state": m.state_dict(),
            "version": version,
            "wave_types_order": sorted(space.wave_types),
            "space_names": space.names,
        },
        path,
    )


def _write_short_wav(path) -> None:
    t = torch.linspace(0, 0.15, int(SAMPLE_RATE * 0.15))
    wave = (0.2 * torch.sin(2 * 3.14159 * 440 * t)).numpy().astype("float32")
    sf.write(path, wave, SAMPLE_RATE)


def test_match_seed_model_smoke(tmp_path):
    ckpt = tmp_path / "ckpt.pt"
    wav = tmp_path / "target.wav"
    out = tmp_path / "out"
    _write_random_ckpt(ckpt)
    _write_short_wav(wav)

    rc = main(
        [
            str(wav),
            "--budget",
            "20",
            "--seed-model",
            str(ckpt),
            "-o",
            str(out),
            "--jobs",
            "1",
        ]
    )
    assert rc == 0
    assert (out / "match.bfxr").is_file()


def test_match_one_shot_smoke(tmp_path):
    ckpt = tmp_path / "ckpt.pt"
    wav = tmp_path / "target.wav"
    out = tmp_path / "out_os"
    _write_random_ckpt(ckpt)
    _write_short_wav(wav)

    rc = main(
        [
            str(wav),
            "--seed-model",
            str(ckpt),
            "--one-shot",
            "-o",
            str(out),
            "--jobs",
            "1",
        ]
    )
    assert rc == 0
    assert (out / "match.bfxr").is_file()
