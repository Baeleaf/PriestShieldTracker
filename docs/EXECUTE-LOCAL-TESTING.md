# Shadow Word: Death icon glow — local beta

Released in 0.3.4 after owner in-game testing and release approval on November 19, 2026.
The checks below remain useful for future regressions.

To diagnose the live GCD flicker, reload this build, reproduce the disappearance,
then run `/pst glowdebug`. The last transitions remain available after the glow
returns. Output includes the public usability/range and cooldown decisions,
icon matching/visibility, source opacity, and native animation state. Protected
values are represented only as `protected`; no target health, secret alpha value,
or clipping geometry is read or logged. The trace holds at most 24 transitions in
memory and prints the latest 16; it does not change saved settings or normal UI.

In `/pst settings`, **Shadow Word: Death > Enabled** turns the indicator on or
off. The note reads: **Ignores resistances, absorbs, and damage reduction.**

The indicator uses icon glows on matching action buttons and on the Essential
and Utility cooldown viewers. It has no separate popup, display selector, or
Edit Mode element. Upgrading preserves the old Enabled preference and removes
obsolete display and layout values from character settings.

## Behavior

The addon scans learned spellbook entries for Shadow Word: Death and selects
the highest learned level/rank. It reads an unambiguous integer damage range
from that rank's description and uses its minimum as the health threshold.
Missing or unfamiliar damage descriptions suppress the glow.

The glow requires a living hostile target, a living player, sufficient resources,
spell range, and no cooldown on the spell itself. It persists through only the
GCD, like a normal proc glow. A real cooldown is bootstrapped on reload. Once SWD
is known ready, only a successful player SWD cast arms another cooldown mask;
unrelated GCD updates cannot turn it into a new real cooldown. Cooldown events
complete that cast's capture, using `isOnGCD` only inside the event. The returned
native duration is copied before caching, so the client's live timer cannot
retime our snapshot during later GCDs. Its native expiration still masks an actual
SWD cooldown if it overlaps a GCD. Protected cast identities are not inspected;
they fall back to the native bootstrap cooldown check.
Protected health goes directly into native fill
and clipping setters. A potentially protected cooldown result goes to native
alpha evaluation; neither is compared by addon code. If an old client cannot
copy the duration, a SWD cast remains blocked until the public cooldown clears.

The overlays use Blizzard's proc art when available, with a pulsing gold border
as a fallback. They do not change button attributes, bindings, clicks, or native
proc alerts. Simple macros work when the client resolves their spell. Lower-rank
buttons do not glow using a higher rank's damage estimate.

Cooldown-viewer pools are checked for current spell identity. Native pooled icons
moved by layout addons remain supported. Hidden or inaccessible icons and
protected identities suppress their overlays. Entirely custom icons outside
those pools are not discovered. New overlay creation and sizing wait until out
of combat; existing overlays follow readable button and icon identity changes.

## In-game checks

1. Reload. Confirm that the settings contain only Enabled and the short note for
   SWD. Toggle it and check that both glow locations respond independently of
   shield bars. Reload again to verify the saved choice.
2. Put the highest learned SWD rank on an action bar and in the cooldown manager.
   Run `/pst glowtest` outside combat for a five-second preview in both locations.
   `/pst execute` reports the detected rank, threshold, and matching icon counts.
3. Test real target health in combat. For a minimum of 346 damage, glow should
   appear at 345 HP or less and be absent at 346 HP or more. Verify cooldown,
   mana, range, friendly/dead/missing targets, and target changes.
4. Check bar pages, icon reuse, viewer visibility, fading, position, and scale.
   Confirm other proc glows and the shield displays remain unaffected.

The Lua suite verifies logic and protected-value boundaries. Real game rendering
still requires an in-game check after changes.
