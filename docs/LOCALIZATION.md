# Localization

The addon reads `GetLocale()` at load time. English is the fallback; no network
requests, external translation service, or saved language override is involved.
English clients keep the English UI. Latin American Spanish (`esMX`) shares the
Spanish (`esES`) dictionary; British English (`enGB`) uses English.

`Localization.lua` contains UTF-8 dictionaries for German, French, Spanish,
Brazilian Portuguese, Italian, Russian, Korean, Simplified Chinese, and
Traditional Chinese. These are initial translations for local review, not
native-speaker-approved translations. Missing entries show their English source
text. The addon name and slash commands remain unchanged.

Use `ns.L["English source text"]` at display boundaries. Keep saved palette names,
style keys, group identifiers, and commands in English internally so existing
character settings continue to work. Translations must preserve format arguments
such as `%s` and `%d` in order. Unit labels and the sample countdown also use the
dictionary. The live countdown and spell icons are drawn by the game.

Fonts use the client's `STANDARD_TEXT_FONT`. Translated checkboxes are stacked,
long explanations wrap, and Shield Ready has extra space where needed. Logic
checks cover every locale, aliases, unknown-locale fallback, dropdown actions,
chat messages, format arguments, and unchanged settings keys. In-game font and
layout checks and a native-speaker wording review remain necessary before release.
