# Changelog

## 0.3.2 - November 16, 2026

- Fix forbidden-object errors after dungeon combat by deferring layout and color changes while Blizzard's aura objects remain locked.
- Add Weakened Soul icons to Blizzard party and raid frames, with countdowns, cooldown swipes, and colored borders.
- Reuse the indicator implementation from Weakened Soul Tracker, with its MIT license included; that addon is no longer needed.
- Choose icon size, corner, countdown format, and the green countdown threshold in PriestShieldTracker's settings.
- Independently enable or disable party/raid icons, Shield Ready, and the absorb/expiration bars in settings.
- Add a live gameplay GIF showing the party-frame indicators, with names covered and the cursor cropped out.

## 0.3.1 - November 15, 2026

- Renamed the addon to PriestShieldTracker.
- Updated the addon folder, commands, settings page, minimap tooltip, artwork captions, and project links.
- Use `/pst` or `/priestshieldtracker`; the existing short command still works.
- Preserve existing character layouts and colors with the included settings importer.

## 0.3.0 - November 15, 2026

- Choose Classic, Smooth, or Liquid absorb bars, with swirling light and bubbles in Liquid mode.
- Pick from six color palettes or adjust bar and text colors in Options > AddOns > PriestShieldTracker, with a live preview.
- Use the new minimap shield: left-click for settings, right-click to open or close Edit Mode.
- Move and resize your display with simpler Edit Mode menus.
- Save appearance settings and minimap position for each character.

## 0.2.4 - November 14, 2026

First public release for WoW Forever 1.60.1.

- Track your remaining shield protection, Power Word: Shield duration, and Weakened Soul countdown together.
- Move and resize the bars and countdown in Edit Mode, with separate text and icon controls.
- Save your layout for each character.
- Preview the animated display with `/pst test`.

The protection amount includes all active shields. Weakened Soul tracking is designed for self-shielding; see the detailed guide for tracking limitations.
