# Appearance settings

These appearance controls are included in PriestShieldTracker 0.3.0 for WoW Forever 1.60.1.

Restart WoW once if this is your first installation of the bundled liquid textures.
For this settings update, reload the UI. Open **Options > AddOns > PriestShieldTracker** or
use `/pst settings`. The appearance page includes a live sample with sample values;
it does not replace your actual shield tracking.

The minimap shield button provides two shortcuts:

- **Left-click:** open PriestShieldTracker in Options > AddOns.
- **Right-click:** toggle Edit Mode. Opening selects **Shield Ready**; clicking
  again closes Edit Mode, including if a different group is selected.
- **Drag:** move the button around the minimap. Its position saves per character.

Open `/pst` to enter Edit Mode. Click a display group to adjust its size, font size,
and either icon size or bar dimensions, then click **Save**. Appearance controls
and the icon visibility toggle live in the AddOns options only.

- **Classic:** immediate fill changes with the original solid look.
- **Smooth:** the same solid look, with native easing when shield amounts change.
- **Liquid:** native easing plus a waving edge, drifting swirls, glow, and bubbles.
- **Color palette:** select Soul, Holy, Frost, Emerald, Ember, or Void from a dropdown.
  Each updates all display colors. The inactive Custom menu entry has been removed.
- **Bar color:** customize the absorb fill and thin shield timer together.
- **Text color:** customize display labels, numbers, countdowns, and the X together.
  These replace the seven individual color controls. Existing custom colors are
  preserved until a palette or combined color is selected. Cancel restores the
  original colors, including any differences between them.
- **Show crossed-out shield icon:** toggle the icon in the AddOns options.
- **Reset appearance:** restores Liquid and Soul colors without changing layout.
  It also shows the shield icon again. **Reset group** resets that group's layout
  and sizes while keeping colors, style, and icon visibility.

The absorb fill follows the client's own status-bar texture. The renderer never
reads its size, coordinates, or secret amount. The game still hides a depleted
shield immediately; cosmetic easing cannot keep an empty shield visible.
The thin duration bar keeps its game-controlled countdown and takes the chosen
color. It does not receive liquid effects.

Liquid textures are bundled, so neither Smooth addon is required. The generated
Swirl, Nebula, Core, Bubble, and Edge textures come from Smooth Animated Bars by
Jordan under MIT; the notice is retained in `licenses/SmoothAnimatedBars.txt`.
The renderer here is a small PriestShieldTracker implementation, inspired by the native
fill anchoring used by Smooth Animated Bars and Smooth Experience Bar.

Before release, check both minimap click shortcuts, the AddOns page, dragging the
minimap button, full/partial/empty shield, all three styles, palette changes and
color-picker Cancel, resized groups, reload persistence, and taking damage in
combat while both countdowns run. The 57 automated Lua checks cover the state
handling, but cannot certify WoW's rendering.
