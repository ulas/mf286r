# mifi_en

**English + Turkish UI, a modern theme and a few fixes for the eko.one.pl "mifi" OpenWrt firmware.**

[eko.one.pl](https://eko.one.pl/?p=mifi) builds "mifi", an OpenWrt-based firmware for LTE routers with a lightweight web interface called **easyconfig**. The interface is Polish-only. `mifi_en.py` takes an official mifi `sysupgrade` image and produces a new image with:

- the whole interface translated to **English**,
- an optional **Turkish** translation with a language switch in the UI,
- a clean **Preline-style theme** (built with Tailwind CSS, works offline),
- **DD.MM.YYYY** date display,
- a fix for **SMS deletion** on Marvell-based modems (ZTE MF286R),
- stability helpers for low-RAM devices: automatic **zram swap**, lighter **adblock** defaults, DNS query logging off,
- an **operator auto-selection guard** for modems that get stuck in manual network selection,
- **Europe/Istanbul** as the default time zone.

It is a single Python file with no build step. Run it again on every new mifi release to keep the same result.

> **Unofficial.** This project is not affiliated with eko.one.pl. Flashing modified firmware is at your own risk. It has been tested on the **ZTE MF286R** only.

| Preline theme (light / dark / mobile) | Turkish UI and language switch |
|---|---|
| ![Preline theme](docs/preview-preline.png) | ![Turkish UI](docs/preview-turkish.png) |

---

## Features

### Translation
- Every Polish string in the easyconfig interface (`easyconfig.html`, `easyconfig.js`) is translated: menus, settings, buttons, dropdowns, dialogs, warnings, error and progress messages, day and month names.
- Backend strings from `rpcd` (battery, temperature, Yes/No), client types, the LuCI "Open easyconfig" page and the Huawei mode script are translated too.
- Translation is phrase-based, not line-based, so small upstream changes do not break it. At the end of each run the script lists any line that still looks Polish, so new strings are easy to spot.

### Turkish language (optional)
- A **Language** selector under *System → User interface*, next to *Theme*, and **English · Türkçe** links on the login page.
- The choice is stored in a cookie; switching reloads the page without logging you out.
- Each language is a separate pre-built copy (`easyconfig-tr.html`, `easyconfig.tr.js`), so there is no runtime translation cost.
- Durations use Turkish abbreviations (`1g 2sa 3dk`).

### Preline theme (optional)
- A stylesheet compiled with Tailwind CSS that restyles the existing Bootstrap 3 classes using the default [Preline UI](https://github.com/htmlstreamofficial/preline) tokens: gray / blue-600, neutral dark mode, rounded cards, Preline-style buttons, inputs, switches, sidebar and modals.
- Works with easyconfig's own *Theme* setting (light / dark / automatic).
- Ships the **Inter** variable font (latin subset, 48 KB) on the device, so nothing is loaded from the internet.
- Measured rendering cost is within noise of the original interface (~11 KB CSS).
- The markup is not rewritten, so easyconfig keeps working exactly as before and the theme survives upstream updates.

### Fixes
- **Dates** are shown as `DD.MM.YYYY HH:MM:SS` (also `MM.YYYY` for monthly summaries and on chart axes). Only display code is changed; stored data and date inputs are untouched.
- **SMS deletion on Marvell modems (ZTE MF286R):** the modem lists SIM messages starting at 1 but `AT+CMGD` counts from 0, so easyconfig failed to delete messages, or deleted the wrong one. The backend now sends the corrected index on Marvell modems with SIM storage. Other modems behave as before.
- **Empty SMS list:** some modems answer `AT+CMGL` on an empty storage with an error that `sms_tool` waits 10 s for. The backend now checks the message count first and returns an empty list immediately.
- **Browser cache:** asset URLs get a new version suffix, so browsers load the translated files instead of cached Polish ones.

### Stability and defaults
- **zram swap (auto-install):** the MF286R has ~117 MB RAM and no swap. While adblock processes its lists, free memory can drop to a few MB and the router can freeze. A boot script installs `zram-swap` from the firmware's own package feeds (which match the kernel of each build) once the internet is up, enables it, and clears the apk cache. It does nothing if zram-swap is already installed, so it re-installs automatically after every firmware update.
- **Operator auto-selection guard:** some modems remember a manual network selection (`AT+COPS=1`) across reboots; after a signal loss they can stay stuck on another operator in limited service. A small background check switches the modem back to automatic selection (`AT+COPS=0`) every 5 minutes if needed and logs it as `operator-auto`.
- **Defaults** (applied by mifi's first-boot scripts, so they also survive upgrades):
  - time zone `Europe/Istanbul` instead of `Europe/Warsaw` (mifi resets the zone on every upgrade),
  - DNS query logging **off** (it floods the log and the flash when a persistent log is used),
  - adblock without the large Polish `certpl` feed, and its backup stored on flash (`/root/adblock-backup`) instead of RAM.

---

## Supported images

| Image type | Example devices | Status |
|---|---|---|
| NAND `sysupgrade` (tar with `CONTROL`, `kernel`, `root`) | `ath79/nand`: ZTE MF286, MF286A, MF286R | ✅ supported |
| Single-file NOR images (kernel + squashfs, TP-Link / uImage headers) | `ath79/generic`, `ath79/tiny` | ❌ not yet |
| FIT (`.itb`), raw UBI, `factory.bin`, `initramfs` | various | ❌ not supported |

Unsupported files are skipped with a clear message; in batch mode the others are still processed.

The kernel is copied byte for byte. Only files under `/www` and a few backend scripts change. File permissions and ownership are preserved, and the `fwtool` metadata (including `supported_devices`) is re-attached, so `sysupgrade` accepts the image normally.

---

## Requirements

- Linux or **WSL** (tested on Debian)
- Python 3.8+
- `squashfs-tools` 4.4 or newer (`unsquashfs`, `mksquashfs`)
- root (via `sudo`), because the image contains device nodes such as `/dev/console`

Optional:
- `nodejs`: syntax check of the generated JavaScript
- `wordfreq` (Python): better detection of leftover Polish words in the report

### Setup on Debian / WSL

```bash
sudo apt update
sudo apt install -y python3 squashfs-tools nodejs wget
mkdir -p ~/mifi && cd ~/mifi
# put mifi_en.py here
```

On WSL, work inside the Linux filesystem (`~/...`), **not** on `/mnt/c/...`. Creating device nodes fails on NTFS, and it is much slower.

Optional `wordfreq`:

```bash
sudo apt install -y python3-venv
python3 -m venv ~/mifi-venv && ~/mifi-venv/bin/pip install wordfreq
# then run the script with ~/mifi-venv/bin/python instead of python3
```

---

## Usage

```bash
# one image -> mifi-...-sysupgrade-EN.bin next to it
sudo python3 mifi_en.py mifi-25.12-...-zte_mf286r-squashfs-sysupgrade.bin

# choose the output name
sudo python3 mifi_en.py input-sysupgrade.bin -o output.bin

# batch: every image gets its own ...-EN.bin
sudo python3 mifi_en.py *-sysupgrade.bin
```

| Option | Effect |
|---|---|
| `-o FILE` | output file name (single input only) |
| `--no-theme` | do not add the Preline theme |
| `--no-tr` | English only, no Turkish option |
| `--no-zram` | do not add the zram auto-install |
| `--no-operator-auto` | do not add the operator auto-selection guard |
| `--no-defaults` | keep mifi's original time zone, DNS logging and adblock defaults |

Arguments are always treated as inputs. The script refuses to overwrite an input file.

### Example output

```
=== mifi-25.12-snapshot-r33313-450459bef3-zte_mf286r-squashfs-sysupgrade.bin
Tamam: mifi-25.12-snapshot-r33313-450459bef3-zte_mf286r-squashfs-sysupgrade-EN.bin (9441541 bayt)
Kalan Lehce metin bulunmadi.
```

(The script's own messages are in Turkish.)

---

## Flashing

OpenWrt's `dropbear` has no SFTP, so use `scp -O`:

```bash
scp -O mifi-...-sysupgrade-EN.bin root@192.168.1.1:/tmp/fw.bin
ssh root@192.168.1.1 "sysupgrade -v /tmp/fw.bin"
```

`sysupgrade` keeps your settings by default; add `-n` to start clean. After the reboot, open the UI and press **Ctrl+F5** once.

**Do not use the "Update" button in easyconfig.** It downloads the original Polish image. Download new releases yourself, run the script, and flash the result.

---

## Updating to a new mifi release

1. Download the new `sysupgrade.bin` from eko.one.pl.
2. `sudo python3 mifi_en.py <file>`
3. If the report lists untranslated lines, add them to the `PHR` dictionary (Polish → English) and to `EN2TR` (English → Turkish) in the script, or open an issue with the output.
4. Flash the `-EN.bin` image.

---

## How it works

1. Splits the image into the tar part and the `fwtool` metadata trailer.
2. Extracts the root squashfs with `unsquashfs`.
3. Translates JavaScript **string literals** and HTML **text nodes / attributes** with a longest-match phrase dictionary (word-boundary aware), so code and identifiers are never touched.
4. Writes the English and Turkish copies, the theme and font, patches the `rpcd` backend, adds the zram and operator helper scripts, and adjusts mifi's first-boot defaults.
5. Checks the generated JS (`node --check`), shell scripts (`sh -n`) and JSON.
6. Rebuilds the squashfs with the original compression, block size and timestamp, rebuilds the tar, and re-attaches the metadata with the same CRC scheme as OpenWrt's `fwtool`.

---

## Credits

- [eko.one.pl](https://eko.one.pl): the mifi firmware and easyconfig
- [sms_tool](https://github.com/obsy/sms_tool): SMS/AT tool used by easyconfig
- [OpenWrt](https://openwrt.org): base system and the `fwtool` image format
- [Preline UI](https://github.com/htmlstreamofficial/preline): design tokens the theme follows
- [Tailwind CSS](https://tailwindcss.com): used to compile the theme
- [Inter](https://rsms.me/inter/) by Rasmus Andersson: SIL Open Font License 1.1

## License

MIT. The embedded Inter font is under the SIL Open Font License 1.1. Translated files remain part of easyconfig and keep its original license.
