"""Mac-side test of the power V2 shutdown hook, with fake libgpiod v1 and v2 modules (no hardware).

python3 -m unittest test_duck_power_off   (in this directory)
"""
import io
import os
import subprocess
import sys
import types
import unittest
from contextlib import redirect_stderr
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import duck_power_off as dpo  # noqa: E402


class FakeV1:
    """python3-libgpiod 1.x surface used by the hook (Debian bullseye)."""
    LINE_REQ_DIR_OUT = 3

    def __init__(self, used=False, named=False):
        self.log, self.used, self.named = [], used, named
        mod = self

        class Line:
            def __init__(self, chip, off):
                self.chip, self.off = chip, off
            def request(self, consumer, type, default_vals):
                mod.log.append(("request", self.chip.name_, self.off, type, default_vals[0]))
            def set_value(self, v):
                mod.log.append(("set", v))
            def release(self):
                mod.log.append(("release",))
            def is_used(self):
                return mod.used
            def consumer(self):
                return "spi" if mod.used else None
            def name(self):
                return "PL5" if mod.named else None
            def offset(self):
                return self.off
            def owner(self):
                return self.chip

        class Chip:
            def __init__(self, name):
                self.name_ = name
            def get_line(self, off):
                return Line(self, off)
            def name(self):
                return self.name_

        self.Chip = Chip
        self._Line = Line

    def find_line(self, name):
        return self._Line(self.Chip("gpiochip7"), 9) if self.named and name == "PL5" else None


class FakeV2:
    """python3-gpiod 2.x surface used by the hook."""

    def __init__(self):
        self.log = []
        mod = self

        class Req:
            def set_value(self, off, v):
                mod.log.append(("set", off, v))
            def release(self):
                mod.log.append(("release",))

        def request_lines(path, consumer, config):
            (off, settings), = config.items()
            mod.log.append(("request", path, off, settings.direction, settings.output_value))
            return Req()

        class LineSettings:
            def __init__(self, direction, output_value):
                self.direction, self.output_value = direction, output_value

        self.request_lines = request_lines
        self.LineSettings = LineSettings


def install_fake_v2_line_module():
    line = types.ModuleType("gpiod.line")
    line.Direction = types.SimpleNamespace(OUTPUT="out")
    line.Value = types.SimpleNamespace(ACTIVE=1, INACTIVE=0)
    pkg = types.ModuleType("gpiod")
    pkg.line = line
    return {"gpiod": pkg, "gpiod.line": line}


def run_main(argv, gpiod=None, env=None):
    err = io.StringIO()
    with mock.patch.dict(os.environ, env or {}, clear=False), \
            mock.patch.object(dpo, "load_gpiod", lambda: gpiod), \
            mock.patch.object(dpo.time, "sleep", lambda s: None), redirect_stderr(err):
        for k in ("DUCK_OFF_CHIP", "DUCK_OFF_LINE"):
            if not env or k not in env:
                os.environ.pop(k, None)
        code = dpo.main(["duck_power_off.py"] + argv)
    return code, err.getvalue()


class Actions(unittest.TestCase):
    def test_reboot_and_kexec_never_touch_the_line(self):
        for action in ("reboot", "kexec"):
            g = FakeV1()
            code, text = run_main([action], g)
            self.assertEqual(code, 0)
            self.assertEqual(g.log, [])
            self.assertIn("power stays on", text)

    def test_poweroff_pulses_pl5_high_then_low_v1(self):
        g = FakeV1()
        code, text = run_main(["poweroff"], g)
        self.assertEqual(code, 0)
        self.assertEqual(g.log, [("request", "gpiochip1", 5, FakeV1.LINE_REQ_DIR_OUT, 1), ("set", 0), ("release",)])
        self.assertIn("header pin 22", text)
        self.assertIn("is the MR30 pin 3 wire", text)  # we are still alive after the pulse in the test

    def test_halt_also_pulses(self):
        g = FakeV1()
        run_main(["halt"], g)
        self.assertEqual(g.log[0][:3], ("request", "gpiochip1", 5))

    def test_line_name_wins_over_numbering(self):
        g = FakeV1(named=True)
        run_main(["poweroff"], g)
        self.assertEqual(g.log[0][:3], ("request", "gpiochip7", 9))

    def test_environment_override(self):
        g = FakeV1(named=True)
        run_main(["poweroff"], g, env={"DUCK_OFF_CHIP": "gpiochip0", "DUCK_OFF_LINE": "42"})
        self.assertEqual(g.log[0][:3], ("request", "gpiochip0", 42))

    def test_poweroff_v2_api(self):
        g = FakeV2()
        with mock.patch.dict(sys.modules, install_fake_v2_line_module()), \
                mock.patch.object(dpo, "find_by_name_v2", lambda gp: None):
            code, _ = run_main(["poweroff"], g)
        self.assertEqual(code, 0)
        self.assertEqual(g.log, [("request", "/dev/gpiochip1", 5, "out", 1), ("set", 5, 0), ("release",)])

    def test_gpioset_fallback_v1_and_v2_syntax(self):
        calls = []
        def fake_run(cmd, **kw):
            calls.append(cmd)
            out = "gpioset (libgpiod) v1.6.2" if fake_run.ver == 1 else "gpioset (libgpiod) v2.1"
            return types.SimpleNamespace(stdout=out, returncode=0)
        fake_run.ver = 1
        self.assertEqual(dpo.pulse(None, "gpiochip1", 5, run=fake_run), "gpioset --mode=time --sec=3 gpiochip1 5=1")
        fake_run.ver = 2
        self.assertEqual(dpo.pulse(None, "gpiochip1", 5, run=fake_run), "gpioset -c gpiochip1 -p 3s -t 0 5=1")

    def test_failure_never_blocks_shutdown(self):
        class Broken(FakeV1):
            pass
        g = Broken()
        g.Chip = lambda name: (_ for _ in ()).throw(OSError("no such chip"))
        code, text = run_main(["poweroff"], g)
        self.assertEqual(code, 0)
        self.assertIn("FAIL", text)
        self.assertIn("unplug the battery", text)

    def test_dry_run_touches_nothing(self):
        g = FakeV1()
        code, text = run_main(["--dry-run", "poweroff"], g)
        self.assertEqual((code, g.log), (0, []))
        self.assertIn("would drive gpiochip1 line 5 (header pin 22) high for 3 s", text)


class Check(unittest.TestCase):
    def test_free_line_passes(self):
        code, text = run_main(["--check"], FakeV1())
        self.assertEqual(code, 0)
        self.assertIn("ok: line 5 free", text)

    def test_line_held_by_a_driver_fails(self):
        code, text = run_main(["--check"], FakeV1(used=True))
        self.assertEqual(code, 1)
        self.assertIn("held by 'spi'", text)


class Hook(unittest.TestCase):
    """The shell hook as systemd-shutdown calls it, pointed at this copy, in dry-run mode."""

    def hook(self, *args):
        env = dict(os.environ, DUCK_POWER_OFF_PY=os.path.join(HERE, "duck_power_off.py"))
        return subprocess.run(["sh", os.path.join(HERE, "duck-power-off.sh"), *args], env=env,
                              capture_output=True, text=True)

    def test_hook_poweroff_and_reboot(self):
        p = self.hook("--dry-run", "poweroff")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("would drive gpiochip1 line 5 (header pin 22)", p.stderr)
        r = self.hook("--dry-run", "reboot")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("power stays on", r.stderr)

    def test_hook_is_executable_and_unit_points_at_installed_script(self):
        for f in ("duck-power-off.sh", "duck_power_off.py"):
            self.assertTrue(os.access(os.path.join(HERE, f), os.X_OK), f)
        with open(os.path.join(HERE, "duck-power-off-check.service")) as fh:
            unit = fh.read()
        self.assertIn("ExecStart=/usr/bin/python3 /usr/local/lib/duck/duck_power_off.py --check", unit)
        with open(os.path.join(HERE, "install.sh")) as fh:
            inst = fh.read()
        self.assertIn("/usr/lib/systemd/system-shutdown/duck-power-off", inst)


if __name__ == "__main__":
    unittest.main()
