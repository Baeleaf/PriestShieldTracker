# SoulShield

**Your shield strength, shield timer, and Weakened Soul countdown in one small display.**

SoulShield helps priests in **WoW Forever** see how much protection remains, when Power Word: Shield expires, and how long until Weakened Soul ends.

![SoulShield showing remaining absorption and shield countdowns](docs/images/soulshield-demo.gif)

*Demo mode with sample values, shown at 1.5x speed.*

## Features

- **Weakened Soul countdown:** See how long until you can shield yourself again.
- **Remaining protection:** Watch the purple bar and number decrease as your shields absorb damage.
- **Shield timer:** See how much time is left on Power Word: Shield, even if Weakened Soul is still counting down.
- **Make it fit your UI:** Move the bars and countdown separately, and adjust text, icon, and bar sizes.
- **Saved layouts:** Keep your settings for each character across logins and reloads.

## Make It Your Own

![SoulShield Edit Mode with movable groups and size controls](docs/images/soulshield-edit-mode.png)

*Move and resize your display in Edit Mode, with separate text and icon controls.*

Open **Esc > Edit Mode** or type `/ss`. Click either group to change its settings, drag it where you want it, then click **Save**.

## Usage

Cast **Power Word: Shield** on yourself to see the display. Shield yourself outside combat first so the bar learns what a full shield looks like. The display hides when there is nothing to track.

- `/ss` - Open Edit Mode.
- `/ss test` - Preview the animated bars. Run it again to stop.
- `/ss reset` - Restore the default layout.

## Installation

Version **0.2.4** supports **WoW Forever 1.60.1**.

1. Download the SoulShield ZIP from [GitHub Releases](https://github.com/Baeleaf/SoulShield/releases).
2. Extract the **SoulShield** folder into `World of Warcraft/_forever_/Interface/AddOns/`.
3. Restart WoW and enable SoulShield on your priest.

## Good to Know

SoulShield tracks your own character. The protection number includes all active shields. **Shield Ready** follows Weakened Soul; you still need enough mana to cast. See the [tracking notes](docs/REFERENCE.md#forever-restrictions) for limitations when another priest shields you.

## Feedback

Found a bug or have an idea? [Open a GitHub issue](https://github.com/Baeleaf/SoulShield/issues).

## More

[Detailed guide & troubleshooting](docs/REFERENCE.md) � [All Rights Reserved](LICENSE)
