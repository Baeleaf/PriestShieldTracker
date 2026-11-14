# SoulShield

**A simple Weakened Soul tracker and Power Word: Shield display for priests.**

SoulShield keeps your remaining shield absorption, shield duration, and Weakened Soul countdown together in one small display. Made for **WoW Forever**.

![SoulShield showing remaining absorption and shield countdowns](docs/images/soulshield-demo.gif)

*Demo mode with sample values, shown at 1.5x speed.*

## Features

- **Weakened Soul countdown:** See how long remains before the debuff ends.
- **Remaining shield absorption:** Watch the purple bar and number decrease as damage uses up your shields.
- **Shield duration:** See how much time is left on Power Word: Shield.
- **Flexible layout:** Move the shield bars and Weakened Soul countdown separately, then adjust text, icon, and bar sizes.
- **Saved settings:** Your layout is remembered for each character.

## Make It Your Own

![SoulShield Edit Mode with movable groups and size controls](docs/images/soulshield-edit-mode.png)

*Move and resize your display in Edit Mode, with separate text and icon controls.*

Open **Esc > Edit Mode** or type `/ss`. Click either group to change its settings, drag it where you want it, then click **Save**.

## Usage

Cast **Power Word: Shield** on yourself to see the display. Cast a fresh shield outside combat first so the absorb bar can learn its full size.

- `/ss` — Open Edit Mode.
- `/ss test` — Preview the animated bars. Run it again to stop.
- `/ss reset` — Restore the default layout.

## Installation

Supports **WoW Forever 1.60.1**.

1. Download the SoulShield ZIP from [GitHub Releases](https://github.com/Baeleaf/SoulShield/releases).
2. Extract the **SoulShield** folder into `World of Warcraft/_forever_/Interface/AddOns/`.
3. Restart WoW and enable SoulShield on your priest.

## Good to Know

The absorb number includes all active shields. The **Shield Ready** countdown follows Weakened Soul; you still need enough mana to cast. SoulShield is designed for shielding yourself, and game restrictions can affect debuff tracking. See the [tracking notes](docs/REFERENCE.md#forever-restrictions) for details.

## Feedback

Found a bug or have an idea? [Open a GitHub issue](https://github.com/Baeleaf/SoulShield/issues).

## More

[Detailed guide & troubleshooting](docs/REFERENCE.md) · [All Rights Reserved](LICENSE)
