#!/usr/bin/env python3
"""Read the USB descriptors out of the built firmware ELF and check what the host will be told.

Plain Python, no packages and no toolchain: a small ELF32 reader finds the symbols desc_device, desc_configuration
and usb_audio_sample_rates and reads their bytes from the image, so the check is on what was linked, not on the
source macros.

    python3 tools/check_descriptors.py build/head_usb.elf [--uf2 build/head_usb.uf2] [--json out.json]

Checks: one configuration with Audio Class 2 (capture 4 channels, playback 2 channels, 16 bit, 48000 Hz) and exactly
one CDC-ACM port; endpoint sizes that fit a full-speed frame. Exit status 0 only if every check passes.
"""
import argparse
import json
import struct
import sys

EXPECT = {"capture_channels": 4, "playback_channels": 2, "rate_hz": 48000, "bits": 16, "cdc_ports": 1}

DT_DEVICE, DT_CONFIG, DT_INTERFACE, DT_ENDPOINT, DT_IAD = 1, 2, 4, 5, 0x0B
DT_CS_INTERFACE, DT_CS_ENDPOINT = 0x24, 0x25
CLASS_AUDIO, CLASS_CDC, CLASS_CDC_DATA, CLASS_MISC = 0x01, 0x02, 0x0A, 0xEF
AUDIO_SUB_CONTROL, AUDIO_SUB_STREAMING = 1, 2
AUDIO_PROTOCOL_V2 = 0x20
UF2_MAGIC0, UF2_MAGIC1, UF2_MAGIC_END, UF2_FAMILY_RP2040 = 0x0A324655, 0x9E5D5157, 0x0AB16F30, 0xE48BFF56


class Elf32:
    def __init__(self, data):
        if data[:4] != b"\x7fELF" or data[4] != 1 or data[5] != 1:
            raise SystemExit("not a little-endian ELF32 file")
        self.data = data
        shoff, = struct.unpack_from("<I", data, 0x20)
        shentsize, shnum, _ = struct.unpack_from("<HHH", data, 0x2E)
        self.sections = [struct.unpack_from("<10I", data, shoff + i * shentsize) for i in range(shnum)]
        self.symbols = {}
        for sec in self.sections:
            if sec[1] != 2:  # SHT_SYMTAB
                continue
            strtab = self.sections[sec[6]]
            for off in range(sec[4], sec[4] + sec[5], 16):
                name_off, value, size, _info, _other, shndx = struct.unpack_from("<IIIBBH", data, off)
                end = data.index(b"\0", strtab[4] + name_off)
                name = data[strtab[4] + name_off:end].decode("ascii", "replace")
                if name and 0 < shndx < len(self.sections):
                    self.symbols[name] = (value, size, shndx)

    def read(self, name):
        if name not in self.symbols:
            raise SystemExit(f"symbol {name} is not in the ELF")
        value, size, shndx = self.symbols[name]
        sec = self.sections[shndx]
        start = sec[4] + (value - sec[3])
        return self.data[start:start + size]


def walk(config):
    """Split a configuration descriptor into (type, bytes) items."""
    items, pos = [], 0
    while pos < len(config):
        length = config[pos]
        if length < 2 or pos + length > len(config):
            raise SystemExit(f"bad descriptor length {length} at offset {pos}")
        items.append((config[pos + 1], config[pos:pos + length]))
        pos += length
    return items


def parse(config):
    out = {"interfaces": [], "iads": [], "audio_control": {"clocks": [], "input_terminals": [], "output_terminals": []}}
    cur = None
    for dtype, d in walk(config):
        if dtype == DT_CONFIG:
            out["config"] = {"total_length": d[2] | d[3] << 8, "interfaces": d[4], "attributes": d[7], "max_power_ma": d[8] * 2}
        elif dtype == DT_IAD:
            out["iads"].append({"first": d[2], "count": d[3], "class": d[4], "subclass": d[5], "protocol": d[6]})
        elif dtype == DT_INTERFACE:
            cur = {"number": d[2], "alt": d[3], "endpoints_declared": d[4], "class": d[5], "subclass": d[6],
                   "protocol": d[7], "endpoints": []}
            out["interfaces"].append(cur)
        elif dtype == DT_ENDPOINT:
            cur["endpoints"].append({"address": d[2], "attributes": d[3], "max_packet": d[4] | d[5] << 8, "interval": d[6]})
        elif dtype == DT_CS_INTERFACE and cur and cur["class"] == CLASS_AUDIO:
            sub = d[2]
            if cur["subclass"] == AUDIO_SUB_CONTROL:
                ac = out["audio_control"]
                if sub == 0x01:
                    ac["bcdADC"] = d[3] | d[4] << 8
                    ac["category"] = d[5]
                elif sub == 0x0A:
                    ac["clocks"].append({"id": d[3], "attributes": d[4], "controls": d[5]})
                elif sub == 0x02:
                    ac["input_terminals"].append({"id": d[3], "type": d[4] | d[5] << 8, "clock": d[7], "channels": d[8],
                                                  "channel_config": struct.unpack_from("<I", d, 9)[0]})
                elif sub == 0x03:
                    ac["output_terminals"].append({"id": d[3], "type": d[4] | d[5] << 8, "source": d[7], "clock": d[8]})
                elif sub == 0x06:
                    ac.setdefault("feature_units", []).append({"id": d[3], "source": d[4]})
            elif cur["subclass"] == AUDIO_SUB_STREAMING:
                if sub == 0x01:
                    cur["as_general"] = {"terminal": d[3], "format_type": d[5], "formats": struct.unpack_from("<I", d, 6)[0],
                                         "channels": d[10], "channel_config": struct.unpack_from("<I", d, 11)[0]}
                elif sub == 0x02:
                    cur["format"] = {"format_type": d[3], "subslot_bytes": d[4], "bits": d[5]}
    return out


def check_uf2(path):
    data = open(path, "rb").read()
    if len(data) % 512 or not data:
        return {"ok": False, "why": f"size {len(data)} is not a multiple of 512"}
    blocks, addrs = len(data) // 512, []
    for i in range(blocks):
        m0, m1, flags, addr, size, num, total, family = struct.unpack_from("<8I", data, i * 512)
        end, = struct.unpack_from("<I", data, i * 512 + 508)
        if (m0, m1, end) != (UF2_MAGIC0, UF2_MAGIC1, UF2_MAGIC_END) or num != i or total != blocks:
            return {"ok": False, "why": f"block {i} malformed"}
        if not flags & 0x2000 or family != UF2_FAMILY_RP2040:
            return {"ok": False, "why": f"block {i}: family {family:#x} is not RP2040"}
        addrs.append((addr, size))
    lo, hi = min(a for a, _ in addrs), max(a + s for a, s in addrs)
    ok = lo == 0x10000000 and hi <= 0x10000000 + 2 * 1024 * 1024
    return {"ok": ok, "blocks": blocks, "flash_start": f"{lo:#x}", "flash_end": f"{hi:#x}", "bytes": hi - lo,
            "why": "" if ok else "image is outside the 2 MB flash at 0x10000000"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("elf")
    ap.add_argument("--uf2")
    ap.add_argument("--json")
    args = ap.parse_args()

    elf = Elf32(open(args.elf, "rb").read())
    device = elf.read("desc_device")
    config = elf.read("desc_configuration")
    rates_raw = elf.read("usb_audio_sample_rates")
    rates = list(struct.unpack(f"<{len(rates_raw) // 4}I", rates_raw))
    p = parse(config)

    checks = []

    def check(name, got, want):
        ok = got == want
        checks.append({"check": name, "got": got, "want": want, "ok": ok})

    def check_true(name, cond, detail):
        checks.append({"check": name, "got": detail, "want": True, "ok": bool(cond)})

    dev = {"bcdUSB": device[2] | device[3] << 8, "class": tuple(device[4:7]), "vid": device[8] | device[9] << 8,
           "pid": device[10] | device[11] << 8, "configurations": device[17]}
    check("device descriptor length", (device[0], device[1]), (18, DT_DEVICE))
    check("device class Misc/Common/IAD (composite with interface associations)", list(dev["class"]), [CLASS_MISC, 2, 1])
    check("one configuration", dev["configurations"], 1)
    check("configuration total length equals the table", p["config"]["total_length"], len(config))

    numbers = sorted({i["number"] for i in p["interfaces"]})
    check("interface numbers are 0..n-1 and match bNumInterfaces", numbers, list(range(p["config"]["interfaces"])))

    # ---- audio function ----
    audio_iads = [a for a in p["iads"] if a["class"] == CLASS_AUDIO]
    check("one audio interface association", len(audio_iads), 1)
    check("audio association is UAC2 and spans control + 2 streaming interfaces",
          (audio_iads[0]["protocol"], audio_iads[0]["count"]) if audio_iads else None, (AUDIO_PROTOCOL_V2, 3))
    ac = p["audio_control"]
    check("audio control header says Audio Class 2.00", ac.get("bcdADC"), 0x0200)
    check("one clock source", len(ac["clocks"]), 1)
    check("sample rates reported by the clock source (usb_audio_sample_rates)", rates, [EXPECT["rate_hz"]])
    check("no feature unit (no device-side volume)", len(ac.get("feature_units", [])), 0)

    streaming = [i for i in p["interfaces"] if i["class"] == CLASS_AUDIO and i["subclass"] == AUDIO_SUB_STREAMING]
    active = [i for i in streaming if i["alt"] != 0]
    capture = [i for i in active if i["endpoints"] and i["endpoints"][0]["address"] & 0x80]
    playback = [i for i in active if i["endpoints"] and not i["endpoints"][0]["address"] & 0x80]
    check("one capture streaming setting", len(capture), 1)
    check("one playback streaming setting", len(playback), 1)
    for itf in streaming:
        if itf["alt"] == 0:
            check(f"interface {itf['number']} alt 0 has no endpoint (zero bandwidth)", len(itf["endpoints"]), 0)

    in_terms = {t["id"]: t for t in ac["input_terminals"]}
    out_terms = {t["id"]: t for t in ac["output_terminals"]}
    frames_per_ms = EXPECT["rate_hz"] // 1000
    for label, group, want_ch in (("capture", capture, EXPECT["capture_channels"]),
                                  ("playback", playback, EXPECT["playback_channels"])):
        if len(group) != 1:
            continue
        itf, ep = group[0], group[0]["endpoints"][0]
        gen, fmt = itf.get("as_general", {}), itf.get("format", {})
        check(f"{label}: channels", gen.get("channels"), want_ch)
        check(f"{label}: Type I PCM", (gen.get("format_type"), gen.get("formats")), (1, 1))
        check(f"{label}: bits per sample", fmt.get("bits"), EXPECT["bits"])
        check(f"{label}: bytes per sample slot", fmt.get("subslot_bytes"), EXPECT["bits"] // 8)
        check(f"{label}: isochronous endpoint", ep["attributes"] & 3, 1)
        nominal = frames_per_ms * want_ch * EXPECT["bits"] // 8
        check_true(f"{label}: packet size holds {frames_per_ms}+1 frames of {EXPECT['rate_hz']} Hz and fits full speed",
                   nominal < ep["max_packet"] <= 1023 and ep["max_packet"] == (frames_per_ms + 1) * want_ch * EXPECT["bits"] // 8,
                   ep["max_packet"])
        check(f"{label}: one packet per 1 ms frame", ep["interval"], 1)
        # terminal wiring: capture = microphone input terminal -> USB streaming output terminal, playback the reverse
        if label == "capture":
            term = out_terms.get(gen.get("terminal"))
            src = in_terms.get(term["source"]) if term else None
            check("capture: stream terminal is fed by an input terminal with the same channel count",
                  src["channels"] if src else None, want_ch)
            check("capture: asynchronous endpoint (the board's crystal sets the rate)", (ep["attributes"] >> 2) & 3, 1)
        else:
            term = in_terms.get(gen.get("terminal"))
            check("playback: stream terminal channel count", term["channels"] if term else None, want_ch)

    # ---- CDC function ----
    comm = [i for i in p["interfaces"] if i["class"] == CLASS_CDC and i["alt"] == 0]
    data = [i for i in p["interfaces"] if i["class"] == CLASS_CDC_DATA and i["alt"] == 0]
    check("CDC communication interfaces (serial ports)", len(comm), EXPECT["cdc_ports"])
    check("CDC data interfaces", len(data), EXPECT["cdc_ports"])
    if len(comm) == 1 and len(data) == 1:
        check("CDC is Abstract Control Model", comm[0]["subclass"], 2)
        check("CDC notification endpoint is interrupt IN",
              [(e["attributes"] & 3, e["address"] >> 7) for e in comm[0]["endpoints"]], [(3, 1)])
        check("CDC data endpoints are bulk OUT and bulk IN",
              sorted((e["attributes"] & 3, e["address"] >> 7) for e in data[0]["endpoints"]), [(2, 0), (2, 1)])

    # ---- endpoints overall ----
    eps = [e["address"] for i in p["interfaces"] for e in i["endpoints"]]
    check_true("no endpoint address used twice", len(eps) == len(set(eps)), [f"{a:#04x}" for a in eps])
    check_true("endpoint numbers within the RP2040's 15", all(0 < (a & 0x7F) < 16 for a in eps), [a & 0x7F for a in eps])

    uf2 = check_uf2(args.uf2) if args.uf2 else None
    if uf2 is not None:
        check_true("UF2: RP2040 family, contiguous numbering, inside the 2 MB flash", uf2["ok"], uf2)

    failed = [c for c in checks if not c["ok"]]
    summary = {
        "elf": args.elf, "device": {**dev, "class": list(dev["class"]), "vid": f"{dev['vid']:#06x}", "pid": f"{dev['pid']:#06x}"},
        "config_bytes": len(config), "max_power_ma": p["config"]["max_power_ma"], "sample_rates": rates,
        "capture": capture[0] if len(capture) == 1 else None, "playback": playback[0] if len(playback) == 1 else None,
        "cdc_ports": len(comm), "uf2": uf2, "checks": checks, "passed": len(checks) - len(failed), "failed": len(failed),
    }
    if args.json:
        with open(args.json, "w") as f:
            json.dump(summary, f, indent=1)
    for c in checks:
        print(f"{'PASS' if c['ok'] else 'FAIL'}  {c['check']}: {c['got']}" + ("" if c["ok"] else f"  (want {c['want']})"))
    print(f"descriptors: {summary['passed']} of {len(checks)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
