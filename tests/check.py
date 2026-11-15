"""Run real Lua 5.1 against a small, strict WoW UI boundary model.

This verifies addon logic, not the game's rendering or secret execution engine.
Run with Python and lupa installed: python tests/check.py
"""
from pathlib import Path
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "PriestShieldTracker.lua").read_text(encoding="utf-8")
COMPATIBILITY = (ROOT / "Compatibility.lua").read_text(encoding="utf-8")
APPEARANCE = (ROOT / "Appearance.lua").read_text(encoding="utf-8")
OPTIONS = (ROOT / "Options.lua").read_text(encoding="utf-8")
STUBS = r'''
frames = {}
messages = {}
combat = false
clock = 100
absorb = 0
healthMaximum = 2400
cursorX, cursorY = 0, 0
class = "PRIEST"
neverSecret = false
nativeAvailable = true
SlashCmdList = {}
Enum = { SecrecyLevel = { NeverSecret = 0 }, StatusBarTimerDirection = { RemainingTime = 1 },
    StatusBarInterpolation = { ExponentialEaseOut = 1 },
    LuaCurveType = { Step = 1 }, NumericRuleFormatRounding = { Nearest = 1 } }
CustomAuraContainerSlotDefaultOptions = {}
C_AuraContainerUtil = {}
GameTooltip = { SetOwner = function() end, SetText = function() end, AddLine = function() end,
    Show = function() end, Hide = function() end }
DEFAULT_CHAT_FRAME = { AddMessage = function(_, text) table.insert(messages, text) end }
function UnitClass() return class, class end
function InCombatLockdown() return combat end
function GetTime() return clock end
function GetCursorPosition() return cursorX, cursorY end
function UnitGetTotalAbsorbs() return absorb end
function UnitHealthMax() return healthMaximum end
function issecretvalue(v) return type(v) == "table" and rawget(v, "secret") == true end
local function forbidden() error("Lua tried to inspect a secret value") end
secret = setmetatable({ secret = true }, {
    __lt = forbidden, __le = forbidden, __add = forbidden, __sub = forbidden,
    __div = forbidden, __mul = forbidden, __concat = forbidden, __tostring = forbidden,
})
secretZero = setmetatable({ secret = true, nativeValue = 0 }, getmetatable(secret))
-- These stand in for C-side operations, keeping the addon-facing input opaque.
C_CurveUtil = { CreateCurve = function()
    return { SetType = function(self, value) self.curveType = value end,
        AddPoint = function() end,
        Evaluate = function(self, value)
            assert(not issecretvalue(value), "Secret values are only allowed during untainted execution")
            return value > 0 and 1 or 0
        end }
end }
C_StringUtil = { CreateNumericRuleFormatter = function()
    return { SetBreakpoints = function(self, value) self.breakpoints = value end,
        FormatNumber = function(self, value)
            local point = self.breakpoints[1]
            local rounded = math.floor(value / point.step + 0.5) * point.step
            return string.format(point.format, rounded)
        end }
end }
C_DurationUtil = { CreateDurationTextBinding = function()
    return { SetFormatter = function(self, formatter) self.formatter = formatter end,
        SetUpdateInterval = function(self, value) self.updateInterval = value end }
end }
C_Secrets = { GetSpellAuraSecrecy = function() return neverSecret and 0 or 1 end }
local Frame = {}
Frame.__index = Frame
local function RequireWritable(frame)
    local ancestor = frame
    while ancestor do
        assert(not (combat and ancestor.kind == "Button" and ancestor.restricted),
            "Attempt to access forbidden object from addon code")
        ancestor = ancestor.parent
    end
end
function Frame:SetHeight(v) self.height = v end
function Frame:SetWidth(v) self.width = v end
function Frame:SetBackdrop(value) self.backdrop = value end
function Frame:SetBackdropColor(...) end
function Frame:SetBackdropBorderColor(...) end
function Frame:SetOrientation(value) self.orientation = value end
function Frame:SetValueStep(value) self.valueStep = value end
function Frame:SetObeyStepOnDrag(value) self.obeyStep = value end
function Frame:SetThumbTexture(value) self.thumb = value end
function Frame:SetChecked(value) self.checked = value end
function Frame:GetChecked() return self.checked end
function Frame:SetParent(v)
    assert(not self.nativeOwned, "Cannot reparent an adopted aura subtree")
    self.parent = v
    self.nativeOwned = v and (v.nativeOwned or v.kind == "Button")
end
function Frame:SetSize(w,h) self.width = w; self.height = h end
function Frame:SetScale(v) self.scale = v end
function Frame:SetFrameStrata(v) end
function Frame:SetFrameLevel(v) self.level = v end
function Frame:GetFrameLevel() return self.level or 1 end
function Frame:SetMovable(v) end
function Frame:SetClampedToScreen(v) end
function Frame:RegisterForDrag(v) end
function Frame:RegisterForClicks(...) self.clickTypes = {...} end
function Frame:SetHighlightTexture(value) self.highlight = value end
function Frame:SetupMenu(generator) self.menuGenerator = generator end
function Frame:SetDefaultText(text) self.defaultText = text end
function Frame:GenerateMenu()
    self.choices = {}
    local root = { CreateRadio = function(_, text, selected, action)
        local choice = { text = text, selected = selected, action = action }
        table.insert(self.choices, choice)
        return { SetEnabled = function() end }
    end }
    self.menuGenerator(self, root)
end
function Frame:Choose(text)
    self:GenerateMenu()
    for _, choice in ipairs(self.choices) do if choice.text == text then choice.action(); return end end
    error("Missing dropdown choice: " .. text)
end
function Frame:EnableMouse(v) self.mouse = v end
function Frame:SetScript(event, fn) self.scripts[event] = fn end
function Frame:GetScript(event) return self.scripts[event] end
function Frame:RegisterEvent(event) self.events[event] = true end
function Frame:RegisterUnitEvent(event, unit) self.events[event] = unit end
function Frame:SetAllPoints(v) self.allPoints = v end
function Frame:SetClipsChildren(value) self.clipsChildren = value end
function Frame:SetPoint(...)
    assert(not self.restricted, "Cannot change an aura button after initialization")
    table.insert(self.points, {...})
end
function Frame:ClearAllPoints() self.points = {} end
function Frame:SetStatusBarTexture(v)
    self.texture = self:CreateTexture(nil, "ARTWORK")
end
function Frame:GetStatusBarTexture() return self.texture end
function Frame:SetStatusBarColor(...) RequireWritable(self); self.barColor = {...} end
function Frame:SetMinMaxValues(lo, hi) RequireWritable(self); self.minimum = lo; self.maximum = hi end
function Frame:SetValue(v, interpolation)
    RequireWritable(self); self.value = v; self.interpolation = interpolation
    if self.kind == "Slider" and self.scripts.OnValueChanged then self.scripts.OnValueChanged(self, v) end
end
function Frame:SetAlpha(value) RequireWritable(self); self.alpha = value end
function Frame:SetColorTexture(...) self.color = {...} end
function Frame:SetVertexColor(...) self.vertexColor = {...} end
function Frame:SetBlendMode(value) self.blend = value end
function Frame:SetTexture(value) self.asset = value end
function Frame:SetTexCoord(...) self.texCoord = {...} end
function Frame:SetFont(font, size, flags) RequireWritable(self); self.fontSize = size end
function Frame:SetTextColor(...) RequireWritable(self); self.textColor = {...} end
function Frame:SetShadowOffset(...) end
function Frame:SetJustifyH(value) self.justifyH = value end
function Frame:SetText(v) self.text = v end
function Frame:SetFormattedText(fmt, v)
    RequireWritable(self)
    self.formattedValue = v
    if not issecretvalue(v) then self.text = string.format(fmt, v) end
end
function Frame:SetShown(v)
    assert(not (self.kind == "AuraContainer" and self.restricted), "Do not toggle a restricted container")
    local wasShown = self.shown
    self.shown = v
    if wasShown and not v and self.scripts.OnHide then self.scripts.OnHide(self) end
    if not wasShown and v and self.scripts.OnShow then self.scripts.OnShow(self) end
end
function Frame:Show() self:SetShown(true) end
function Frame:Hide() self:SetShown(false) end
function Frame:IsVisible() return self.shown and (not self.parent or self.parent:IsVisible()) end
function Frame:IsShown() return self.shown end
function Frame:IsMouseOver() return self.mouseOver == true end
function Frame:IsRendered()
    local alphaVisible = self.alpha == nil or (issecretvalue(self.alpha) and rawget(self.alpha, "rendered"))
        or (not issecretvalue(self.alpha) and self.alpha ~= 0)
    -- Model the renderer's clip rectangle without exposing any measurement
    -- back to addon code. A clip tied to a native fill is empty at value zero.
    local clipVisible = true
    if self.clipsChildren and self.allPoints and self.allPoints.kind == "Texture" then
        local meter = self.allPoints.parent
        local value = meter.value
        local nativeValue = issecretvalue(value) and (rawget(value, "nativeValue") or 1) or value
        clipVisible = nativeValue ~= nil and nativeValue > 0
    end
    return alphaVisible and clipVisible and self.shown and (not self.parent or self.parent:IsRendered())
end
function Frame:StartMoving() self.moving = true end
function Frame:StopMovingOrSizing() self.moving = false end
function Frame:GetWidth() return self.width end
function Frame:GetHeight() return self.height end
function Frame:GetCenter() return 1200, 700 end
function Frame:GetEffectiveScale() return self.scale or 1 end
function Frame:CreateTexture() return CreateFrame("Texture", nil, self) end
function Frame:CreateFontString() return CreateFrame("FontString", nil, self) end
function Frame:SetDurationBar(v, opts)
    assert(v.parent == self and opts.direction == Enum.StatusBarTimerDirection.RemainingTime)
    self.durationBar = v
end
function Frame:SetDurationText(v, options)
    assert(v.parent == self)
    self.durationText = v; self.durationOptions = options
end
function Frame:SetSpellName(v) assert(v.parent == self); self.spellName = v end
function Frame:SetUnit(v) self.unit = v end
function Frame:SetEnabled(v) self.enabled = v; self.restricted = self.kind == "AuraContainer" end
function Frame:AddAuraSlot(key, filter, opts)
    local button = CreateFrame("Button", nil, self)
    opts.initializeFrame(button)
    button:Hide() -- Native engine owns whether the aura is active.
    button.restricted = true
    self.slots[key] = { button = button, filter = filter, options = opts }
    return button
end
function CreateFrame(kind, name, parent, template)
    local frame = setmetatable({ kind = kind, name = name, parent = parent,
        nativeOwned = parent and (parent.nativeOwned or parent.kind == "Button"),
        template = template, scripts = {}, events = {}, points = {}, slots = {}, shown = true }, Frame)
    table.insert(frames, frame)
    if name then _G[name] = frame end
    return frame
end
UIParent = CreateFrame("Frame", "UIParent")
UIParent:SetSize(1920, 1080)
Minimap = CreateFrame("Frame", "Minimap", UIParent)
Minimap:SetSize(140, 140)
SettingsPanel = CreateFrame("Frame", "SettingsPanel", UIParent)
SettingsPanel:Hide()
Settings = { categories = {} }
function Settings.RegisterCanvasLayoutCategory(canvas, title)
    local category = { ID = #Settings.categories + 1, name = title, panel = canvas }
    function category:GetID() return self.ID end
    canvas:SetParent(SettingsPanel)
    return category
end
function Settings.RegisterAddOnCategory(category) table.insert(Settings.categories, category) end
function Settings.OpenToCategory(id)
    Settings.opened = id; SettingsPanel:Show(); Settings.categories[id].panel:Show()
end
function Fire(event, argument)
    for _, f in ipairs(frames) do
        if f.events[event] and f.scripts.OnEvent then f.scripts.OnEvent(f, event, argument or "player") end
    end
end
function Find(kind, parent)
    for _, f in ipairs(frames) do
        if f.kind == kind and (not parent or f.parent == parent) then return f end
    end
end
function Command(text) SlashCmdList.PRIESTSHIELDTRACKER(text) end
function ClickGroup(key)
    for _, frame in ipairs(frames) do
        if frame.groupKey == key then frame.scripts.OnMouseUp(frame, "LeftButton"); return end
    end
    error("Missing group " .. key)
end
function ShowUIPanel(frame)
    frame:Show()
    if EventRegistry and frame == EditModeManagerFrame then EventRegistry:TriggerEvent("EditMode.Enter") end
end
function HideUIPanel(frame)
    frame:Hide()
    if EventRegistry and frame == EditModeManagerFrame then EventRegistry:TriggerEvent("EditMode.Exit") end
end
function EnableNativeEditMode()
    EditModeManagerFrame = CreateFrame("Frame", "EditModeManagerFrame", UIParent)
    EditModeManagerFrame:Hide()
    EventRegistry = { callbacks = {} }
    function EventRegistry:RegisterCallback(event, callback, owner)
        self.callbacks[event] = self.callbacks[event] or {}
        table.insert(self.callbacks[event], { callback = callback, owner = owner })
    end
    function EventRegistry:TriggerEvent(event)
        for _, entry in ipairs(self.callbacks[event] or {}) do entry.callback(entry.owner) end
    end
end
function FindText(parent, text)
    for _, f in ipairs(frames) do
        if f.parent == parent and f.text == text then return f end
    end
end
function Tick(elapsed)
    clock = clock + elapsed
    for _, f in ipairs(frames) do
        if f.scripts.OnUpdate then f.scripts.OnUpdate(f, elapsed) end
    end
end
'''


def new(setup=""):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(STUBS)
    lua.execute(setup)
    namespace = lua.table()
    lua.execute(COMPATIBILITY, "PriestShieldTracker", namespace)
    lua.execute(APPEARANCE, "PriestShieldTracker", namespace)
    lua.execute(OPTIONS, "PriestShieldTracker", namespace)
    lua.execute(SOURCE, "PriestShieldTracker", namespace)
    lua.execute('''Fire("PLAYER_LOGIN"); hud = PriestShieldTrackerHUD
for _, f in ipairs(frames) do
    if f.parts then sample = f end
    if f.kind == "StatusBar" and f.absorbLabel and not f.parent.parts then bar = f end
end
''')
    return lua


def case(name, setup, assertions):
    lua = new(setup)
    lua.execute(assertions)
    print("PASS", name)


case("fresh initialization and native timer ownership", "", r'''
assert(hud.mouse == false)
assert(bar.value == 0 and bar.maximum == 2400)
local ct = Find("AuraContainer")
assert(ct.unit == "player" and ct.enabled)
assert(ct.slots.weakenedSoul.filter == "HARMFUL|PLAYER")
assert(ct.slots.weakenedSoul.options.candidateFilters.maxDuration == 15.5)
assert(ct.slots.weakenedSoul.button.durationText)
assert(ct.slots.shield.filter == "HELPFUL")
assert(ct.slots.shield.button.durationBar)
assert(ct.slots.shield.options.candidateFilters.includeSpellIDs[10901])
''')
case("native identity filter when allowed", "neverSecret = true", r'''
local ct = Find("AuraContainer")
assert(ct.slots.weakenedSoul.filter == "HARMFUL")
assert(ct.slots.weakenedSoul.options.candidateFilters.includeSpellIDs[6788])
''')
case("absorption depletion preserves full reference", "", r'''
absorb = 1100; Fire("UNIT_ABSORB_AMOUNT_CHANGED")
absorb = 700; Fire("UNIT_ABSORB_AMOUNT_CHANGED")
assert(bar.maximum == 1100 and bar.value == 700)
assert(PriestShieldTrackerDB.reference == 1100)
absorb = 0; Fire("UNIT_ABSORB_AMOUNT_CHANGED")
assert(bar.value == 0 and bar.maximum == 1100)
absorb = 800; Fire("UNIT_ABSORB_AMOUNT_CHANGED")
assert(bar.maximum == 800)
''')
case("secret combat values remain native and unsaved", "", r'''
absorb = 1100; Fire("UNIT_ABSORB_AMOUNT_CHANGED")
combat = true; Fire("PLAYER_REGEN_DISABLED")
absorb = secret; Fire("UNIT_ABSORB_AMOUNT_CHANGED")
assert(rawequal(bar.value, secret))
assert(PriestShieldTrackerDB.reference == 1100)
combat = false; absorb = 600; Fire("PLAYER_REGEN_ENABLED")
assert(bar.maximum == 1100 and bar.value == 600)
''')
case("login during combat without calibration", "absorb = secret; combat = true", r'''
assert(rawequal(bar.value, secret))
assert(bar.maximum == 2400)
assert(PriestShieldTrackerDB.reference == nil)
''')
case("active shield on reload retains calibration", "PriestShieldTrackerDB = { reference = 1100 }; absorb = 500", r'''
assert(bar.maximum == 1100 and bar.value == 500)
''')
case("preview restores live values and reference", "", r'''
absorb = 1100; Fire("UNIT_ABSORB_AMOUNT_CHANGED")
absorb = 600; Fire("UNIT_ABSORB_AMOUNT_CHANGED")
Command("test"); assert(hud.scripts.OnUpdate)
clock = 105; hud.scripts.OnUpdate()
assert(sample.absorb.value == 810 and bar.value == 600)
Command("test")
assert(hud.scripts.OnUpdate == nil and bar.value == 600 and bar.maximum == 1100)
''')
case("entering combat stops preview and dragging", "", r'''
Command("unlock"); Command("test")
hud.scripts.OnDragStart(hud); assert(hud.moving)
combat = true; absorb = secret; Fire("PLAYER_REGEN_DISABLED")
assert(not hud.moving and not hud.mouse and hud.scripts.OnUpdate == nil)
assert(rawequal(bar.value, secret))
Command("test"); assert(hud.scripts.OnUpdate == nil)
combat = false; absorb = 0; Fire("PLAYER_REGEN_ENABLED")
assert(hud.mouse)
''')
case("scaled drag and saved layout", "", r'''
Command("scale 1.5"); Command("unlock"); hud.scripts.OnDragStop(hud)
assert(PriestShieldTrackerDB.x == 560 and PriestShieldTrackerDB.y == 340)
Command("width 310"); assert(hud.width == 310)
Command("scale 99"); assert(hud.scale == 1.5)
Command("reset"); assert(hud.scale == 1 and hud.width == 260 and hud.mouse)
Command("lock"); assert(not hud.mouse)
''')
case("non-priest has no HUD", 'class = "MAGE"', r'''
assert(PriestShieldTrackerHUD == nil)
Command("test")
assert(#messages == 1)
''')
case("native API failure leaves working absorb HUD", "C_AuraContainerUtil = nil", r'''
assert(hud and #messages == 1)
absorb = 500; Fire("UNIT_ABSORB_AMOUNT_CHANGED")
assert(bar.value == 500)
Command("status"); assert(#messages == 2)
''')
first = new()
first.execute('Command("scale 1.3"); Command("width 320"); Command("unlock")')
saved = dict(first.globals().PriestShieldTrackerDB.items())
second = new("PriestShieldTrackerDB = {scale = %s, width = %s, locked = false}" % (saved["scale"], saved["width"]))
second.execute('assert(hud.scale == 1.3 and hud.width == 320 and hud.mouse == false and not sample:IsVisible())')
print("PASS settings persist across reload")
case("native shield visibility and independent debuff", "", r'''
local ct = Find("AuraContainer")
local shield, debuff = ct.slots.shield.button, ct.slots.weakenedSoul.button
assert(not bar.nativeOwned and not bar:IsRendered())
absorb = 1100; shield:Show(); debuff:Show(); Fire("UNIT_ABSORB_AMOUNT_CHANGED")
assert(bar:IsRendered() and debuff:IsVisible())
combat = true; absorb = secret; Fire("PLAYER_REGEN_DISABLED")
shield:Hide(); absorb = secretZero; Fire("UNIT_ABSORB_AMOUNT_CHANGED")
assert(not bar:IsRendered() and debuff:IsVisible())
combat = false; absorb = 0; Fire("PLAYER_REGEN_ENABLED")
assert(not bar:IsRendered())
Command("test"); assert(sample.absorb:IsVisible() and not bar.nativeOwned and not bar:IsRendered())
Command("test"); assert(not bar.nativeOwned and not bar:IsRendered())
''')
case("two draggable groups preserve spacing and native ownership", "", r'''
Command("scale 1.5"); Command("unlock")
local handle, debuffHandle, count = nil, nil, 0
for _, f in ipairs(frames) do
    if f.groupKey then
        count = count + 1
        if f.groupKey == "shield" then handle = f else debuffHandle = f end
    end
end
assert(count == 2 and handle.shown and sample:IsVisible())
cursorX, cursorY = 100, 100; handle.scripts.OnDragStart(handle)
cursorX, cursorY = 145, 70; handle.scripts.OnUpdate()
handle.scripts.OnDragStop(handle)
assert(PriestShieldTrackerDB.groups.shield.x == 30 and PriestShieldTrackerDB.groups.shield.y == -20)
assert(bar.points[1][4] == 30 and bar.points[1][5] == -47)
local ct = Find("AuraContainer")
local duration = ct.slots.shield.button.durationBar
local shieldTime = ct.slots.shield.button.durationText
assert(duration.points[1][4] == 30 and duration.points[1][5] == -68)
assert(shieldTime.points[1][4] == 30 and shieldTime.points[1][5] == -76)
assert(bar.absorbLabel.points[1][2] == bar and bar.absorbLabel.points[1][4] == 6)
assert(PriestShieldTrackerDB.groups.weakenedSoul.x == 0)
cursorX, cursorY = 0, 0; debuffHandle.scripts.OnDragStart(debuffHandle)
cursorX, cursorY = -30, 60; debuffHandle.scripts.OnUpdate()
debuffHandle.scripts.OnDragStop(debuffHandle)
local ws = ct.slots.weakenedSoul.button
local label = FindText(ws, "Shield Ready")
assert(label.points[1][4] == -46 and label.points[1][5] == 27)
assert(ws.durationText.points[1][4] == -208 and ws.durationText.points[1][5] == 27)
assert(PriestShieldTrackerDB.groups.shield.x == 30)
assert(ct.slots.weakenedSoul.button.durationText.parent == ct.slots.weakenedSoul.button)
assert(ct.slots.shield.button.durationText.parent == ct.slots.shield.button)
Command("lock"); assert(not handle.shown and not bar.nativeOwned)
Command("reset"); assert(PriestShieldTrackerDB.groups.shield.x == 0)
''')
case("combat interrupts component drag and restores edit mode", "", r'''
Command("unlock")
local handle
for _, f in ipairs(frames) do
    if f.parent == hud and f.scripts.OnEnter then handle = f; break end
end
handle.scripts.OnDragStart(handle); assert(handle.scripts.OnUpdate)
combat = true; Fire("PLAYER_REGEN_DISABLED")
assert(not handle.scripts.OnUpdate and not handle.shown and not hud.moveHandle.shown)
combat = false; Fire("PLAYER_REGEN_ENABLED")
assert(handle.shown and hud.moveHandle.shown and sample:IsVisible())
''')
case("fallback hides readable zero absorbs", "C_AuraContainerUtil = nil", r'''
assert(not bar:IsRendered())
absorb = 500; Fire("UNIT_ABSORB_AMOUNT_CHANGED"); assert(bar:IsRendered())
absorb = 0; Fire("UNIT_ABSORB_AMOUNT_CHANGED"); assert(not bar:IsRendered())
''')
case("saved group positions restore to native and preview regions", '''
PriestShieldTrackerDB = { groups = { weakenedSoul = { x = 35, y = -20 },
    shield = { x = -40, y = -15 } } }
''', r'''
local ct = Find("AuraContainer")
local timer = ct.slots.weakenedSoul.button.durationText
local duration = ct.slots.shield.button.durationBar
assert(timer.points[1][4] == -153 and timer.points[1][5] == -33)
assert(duration.points[1][4] == -40 and duration.points[1][5] == -63)
Command("unlock")
local matched = false
for _, f in ipairs(frames) do
    if f.parent == hud and f.parts then
        matched = true
        assert(f.parts.weakenedTime.points[1][4] == timer.points[1][4])
        assert(f.parts.duration.points[1][5] == duration.points[1][5])
    end
end
assert(matched)
''')
case("locking discards sample and preserves live absorption", "", r'''
local ct = Find("AuraContainer")
local shield = ct.slots.shield.button
absorb = 600; shield:Show(); Fire("UNIT_ABSORB_AMOUNT_CHANGED")
Command("unlock")
assert(sample.absorb.value == 1100 and bar.value == 600)
assert(not ct:IsVisible() and sample:IsVisible())
Command("lock")
assert(not sample:IsVisible() and ct:IsVisible() and bar:IsRendered())
assert(bar.value == 600 and bar.amountText.formattedValue == 600)
shield:Hide(); absorb = 0; Fire("UNIT_ABSORB_AMOUNT_CHANGED")
Command("unlock"); Command("lock")
for _, f in ipairs(frames) do
    if f.absorbLabel then assert(not f:IsRendered()) end
end
''')
case("combat restores native countdowns after editing", "", r'''
local ct = Find("AuraContainer")
local ws, shield = ct.slots.weakenedSoul.button, ct.slots.shield.button
ws:Show(); shield:Show()
local timer = ws.durationText
Command("unlock")
assert(sample:IsVisible() and not ct:IsVisible())
combat = true; absorb = secret; Fire("PLAYER_REGEN_DISABLED")
assert(not sample:IsVisible() and ct:IsVisible())
assert(ws:IsVisible() and timer:IsVisible() and ws.durationText == timer)
assert(bar:IsRendered() and rawequal(bar.value, secret))
shield:Hide(); absorb = secretZero; Fire("UNIT_ABSORB_AMOUNT_CHANGED")
assert(not bar:IsRendered() and ws:IsVisible() and timer:IsVisible())
''')
case("login locks old edit state and migrates group positions", '''
PriestShieldTrackerDB = { locked = false, positions = {
    weakenedLabel = { x = 35, y = -10 }, weakenedTime = { x = 120, y = 70 },
    absorb = { x = -40, y = -15 }, shieldTime = { x = 100, y = 80 } } }
''', r'''
assert(PriestShieldTrackerDB.locked and not sample:IsVisible() and not bar:IsRendered())
assert(PriestShieldTrackerDB.positions == nil)
local ct = Find("AuraContainer")
local ws, shield = ct.slots.weakenedSoul.button, ct.slots.shield.button
local label = FindText(ws, "Shield Ready")
assert(label.points[1][4] == 9 and ws.durationText.points[1][4] == -153)
assert(label.points[1][5] == -23 and ws.durationText.points[1][5] == -23)
assert(bar.points[1][4] == -40 and shield.durationText.points[1][4] == -40)
assert(shield.durationText.points[1][5] == -71)
''')
case("Shield Ready label aligns right and countdown aligns left", "", r'''
local ct = Find("AuraContainer")
local ws = ct.slots.weakenedSoul.button
local label = FindText(ws, "Shield Ready")
assert(label and label.justifyH == "RIGHT" and ws.spellName == nil)
assert(label.points[1][1] == "RIGHT" and label.points[1][3] == "TOPRIGHT")
assert(ws.durationText.justifyH == "LEFT")
assert(ws.durationText.points[1][1] == "LEFT" and ws.durationText.points[1][3] == "TOPRIGHT")
assert(ws.durationText.points[1][4] == -188 and label.width == 112)
local icon
for _, f in ipairs(frames) do
    if f.parent == ws and f.asset == "Interface\\Icons\\Spell_Holy_PowerWordShield" then icon = f end
end
assert(icon and icon.width == 20 and icon.height == 20)
assert(icon.points[1][1] == "LEFT" and icon.points[1][2] == label and icon.points[1][3] == "RIGHT" and icon.points[1][4] == 6)
local cross = FindText(ws, "X")
assert(cross and cross.points[1][2] == icon)
assert(sample.readyIcon.asset == icon.asset and sample.readyCross.text == "X")
assert(sample.ws.text == "Shield Ready" and sample.ws.justifyH == "RIGHT")
assert(sample.wsTime.justifyH == "LEFT" and sample.wsTime.points[1][1] == "LEFT")
''')
case("absorb polling repairs missed or early damage events", "", r'''
absorb = 158; Fire("UNIT_ABSORB_AMOUNT_CHANGED")
-- The event arrives before the cached unit value changes.
Fire("UNIT_ABSORB_AMOUNT_CHANGED"); absorb = 92
Tick(0.05); assert(bar.value == 158)
Tick(0.05); assert(bar.value == 92 and bar.amountText.formattedValue == 92)
-- No event at all for the next damage tick.
absorb = 61; Tick(0.1)
assert(bar.value == 61 and bar.amountText.formattedValue == 61)
assert(bar.maximum == 158)
absorb = 40; Fire("UNIT_AURA"); assert(bar.value == 40)
absorb = 22; Fire("UNIT_HEALTH"); assert(bar.value == 22)
''')
case("combat absorb polling forwards secret values independently of preview", "", r'''
absorb = 158; Fire("UNIT_ABSORB_AMOUNT_CHANGED")
Command("unlock"); combat = true; absorb = secret; Fire("PLAYER_REGEN_DISABLED")
local reduced = setmetatable({ secret = true }, getmetatable(secret))
absorb = reduced; Tick(0.1)
assert(rawequal(bar.value, reduced) and rawequal(bar.amountText.formattedValue, reduced))
assert(PriestShieldTrackerDB.reference == 158 and not sample:IsVisible())
combat = false; absorb = 20; Fire("PLAYER_REGEN_ENABLED")
assert(sample:IsVisible() and sample.absorb.value == 1100 and bar.value == 20)
absorb = 12; Tick(0.1); assert(bar.value == 12 and sample.absorb.value == 1100)
''')
case("maximum health updates uncalibrated absorb scale", "absorb = secret", r'''
healthMaximum = 5200; Fire("UNIT_MAXHEALTH")
assert(bar.maximum == 5200 and rawequal(bar.value, secret))
''')
case("both native timers use nearest tenths with frequent updates", "", r'''
local ct = Find("AuraContainer")
for _, slot in pairs(ct.slots) do
    local binding = slot.button.durationOptions.binding
    local point = binding.formatter.breakpoints[1]
    assert(binding.updateInterval == 0.05)
    assert(point.step == 0.1 and point.rounding == Enum.NumericRuleFormatRounding.Nearest)
    assert(binding.formatter:FormatNumber(10.46) == "10.5")
    assert(binding.formatter:FormatNumber(8.24) == "8.2")
    assert(binding.formatter:FormatNumber(9.66) == "9.7")
    assert(binding.formatter:FormatNumber(5) == "5.0")
end
assert(hud.moveHint.text == "Move entire display  |  Click a group for settings")
''')
case("repeated combat polling never writes protected aura widgets", "combat = true; absorb = secret", r'''
assert(not bar.nativeOwned and not bar.amountText.nativeOwned)
for i = 1, 200 do Tick(0.1) end
assert(rawequal(bar.value, secret) and bar.maximum == healthMaximum)
assert(rawequal(bar.amountText.formattedValue, secret))
absorb = secretZero; Tick(0.1); assert(not bar:IsRendered())
''')
case("reload with secret zero absorbs uses native clipping without curve evaluation", "absorb = secretZero", r'''
local clip, gate = bar.parent, bar.parent.parent
assert(clip.clipsChildren and clip.allPoints == gate:GetStatusBarTexture())
assert(gate.minimum == 0 and gate.maximum == 1)
assert(gate.points[1][4] == bar.points[1][4] and gate.points[1][5] == bar.points[1][5])
for i = 1, 600 do Tick(0.1) end
assert(not bar:IsRendered() and rawequal(gate.value, secretZero))
absorb = secret; Tick(0.1)
assert(bar:IsRendered() and rawequal(bar.value, secret) and rawequal(gate.value, secret))
absorb = secretZero; Tick(0.1); assert(not bar:IsRendered())
Command("width 320")
assert(gate.width == 320 and bar.width == 320)
''')
case("native Edit Mode opens settings and closing it clears previews", "EnableNativeEditMode()", r'''
ShowUIPanel(EditModeManagerFrame)
assert(not PriestShieldTrackerDB.locked and sample:IsVisible() and PriestShieldTrackerEditSettings == nil)
ClickGroup("weakenedSoul")
assert(PriestShieldTrackerEditSettings:IsVisible())
local buttons = 0
for _, frame in ipairs(frames) do
    if frame.parent == PriestShieldTrackerEditSettings and frame.kind == "Button" then buttons = buttons + 1 end
end
assert(buttons == 2 and PriestShieldTrackerEditSettings.saveButton.text == "Save")
assert(PriestShieldTrackerEditSettings.controls.iconSize:IsVisible())
assert(not PriestShieldTrackerEditSettings.controls.width:IsVisible())
HideUIPanel(EditModeManagerFrame)
assert(PriestShieldTrackerDB.locked and not sample:IsVisible() and not PriestShieldTrackerEditSettings:IsVisible())
Command("edit"); assert(EditModeManagerFrame:IsShown() and sample:IsVisible())
assert(not PriestShieldTrackerEditSettings:IsVisible())
ClickGroup("shield")
assert(PriestShieldTrackerEditSettings.subtitle.text == "Absorb display")
PriestShieldTrackerEditSettings.saveButton.scripts.OnClick()
assert(not EditModeManagerFrame:IsShown() and PriestShieldTrackerDB.locked)
''')
case("Edit Mode adjusts ready group scale fonts and right-side icon", "EnableNativeEditMode()", r'''
Command("edit")
ClickGroup("weakenedSoul")
local controls = PriestShieldTrackerEditSettings.controls
controls.groupScale:SetValue(150)
controls.fontSize:SetValue(20)
controls.iconSize:SetValue(28)
assert(PriestShieldTrackerDB.groupOptions.weakenedSoul.scale == 1.5)
local ws = Find("AuraContainer").slots.weakenedSoul.button
local label = FindText(ws, "Shield Ready")
assert(label.fontSize == 30 and ws.durationText.fontSize == 33.75)
assert(label.points[1][4] == -51)
assert(sample.readyIcon.width == 42 and sample.readyIcon.points[1][3] == "RIGHT")
assert(sample.readyIcon.points[1][4] == 9)
assert(controls.showIcon == nil and PriestShieldTrackerEditSettings.appearanceButton == nil)
''')
case("clicking absorb group selects independent size and text controls", "EnableNativeEditMode()", r'''
Command("edit")
local shieldHandle
for _, f in ipairs(frames) do if f.groupKey == "shield" then shieldHandle = f end end
shieldHandle.scripts.OnMouseUp(shieldHandle, "LeftButton")
local controls = PriestShieldTrackerEditSettings.controls
assert(controls.width:IsVisible() and controls.barHeight:IsVisible() and not controls.iconSize:IsVisible())
controls.width:SetValue(350); controls.barHeight:SetValue(28)
controls.groupScale:SetValue(125); controls.fontSize:SetValue(14)
assert(bar.width == 437.5 and bar.height == 35 and bar.edge.height == 35)
local clip, gate = bar.parent, bar.parent.parent
assert(gate.width == bar.width and gate.height == bar.height)
local shield = Find("AuraContainer").slots.shield.button
assert(shield.durationBar.width == 437.5 and shield.durationBar.height == 3.75)
assert(shield.durationBar.points[1][5] == -64.5)
assert(shield.durationText.points[1][5] == -74.5)
assert(bar.amountText.fontSize == 17.5)
assert(PriestShieldTrackerDB.groupOptions.weakenedSoul.scale == 1 and sample.ws.fontSize == 16)
''')
case("native combat entry closes editor without protected writes or reopening", "EnableNativeEditMode()", r'''
Command("edit"); ClickGroup("weakenedSoul"); PriestShieldTrackerEditSettings.controls.fontSize:SetValue(19)
combat = true; absorb = secret; Fire("PLAYER_REGEN_DISABLED")
assert(PriestShieldTrackerDB.locked and not sample:IsVisible() and not PriestShieldTrackerEditSettings:IsVisible())
HideUIPanel(EditModeManagerFrame)
for i = 1, 200 do Tick(0.1) end
assert(rawequal(bar.value, secret))
combat = false; absorb = 0; Fire("PLAYER_REGEN_ENABLED")
assert(not sample:IsVisible() and not PriestShieldTrackerEditSettings:IsVisible() and not hud.mouse)
assert(PriestShieldTrackerDB.groupOptions.weakenedSoul.fontSize == 19)
''')
case("saved group settings restore locked with scaled fonts and icon preference", '''
PriestShieldTrackerDB = { width = 350, barHeight = 28, groupOptions = {
    weakenedSoul = { scale = 1.5, fontSize = 20, iconSize = 28, showIcon = false },
    shield = { scale = 1.25, fontSize = 14 } } }
EnableNativeEditMode()
''', r'''
assert(PriestShieldTrackerDB.locked and not sample:IsVisible() and PriestShieldTrackerEditSettings == nil)
assert(sample.ws.fontSize == 30 and not sample.readyIcon.shown)
assert(bar.width == 437.5 and bar.height == 35 and bar.amountText.fontSize == 17.5)
Command("edit"); assert(not sample.readyIcon.shown and not sample.readyCross.shown)
''')
case("reset group restores only its layout and appearance", "EnableNativeEditMode()", r'''
Command("edit")
ClickGroup("weakenedSoul")
PriestShieldTrackerEditSettings.controls.fontSize:SetValue(22)
PriestShieldTrackerDB.groups.weakenedSoul.x = 25
local handle
for _, f in ipairs(frames) do if f.groupKey == "shield" then handle = f end end
handle.scripts.OnMouseUp(handle, "LeftButton")
PriestShieldTrackerEditSettings.controls.width:SetValue(400)
PriestShieldTrackerEditSettings.controls.groupScale:SetValue(150)
PriestShieldTrackerEditSettings.resetButton.scripts.OnClick()
assert(PriestShieldTrackerDB.width == 260 and PriestShieldTrackerDB.barHeight == 19 and PriestShieldTrackerDB.groupOptions.shield.scale == 1)
assert(PriestShieldTrackerDB.groupOptions.weakenedSoul.fontSize == 22 and PriestShieldTrackerDB.groups.weakenedSoul.x == 25)
''')
case("settings appear only for focused group and dismiss on outside clicks", "EnableNativeEditMode()", r'''
assert(MouseIsOver == nil) -- Forever exposes the frame method, not this old global.
Command("edit")
assert(PriestShieldTrackerEditSettings == nil)
ClickGroup("weakenedSoul")
local panel = PriestShieldTrackerEditSettings
local ready, shield
for _, frame in ipairs(frames) do
    if frame.groupKey == "weakenedSoul" then ready = frame end
    if frame.groupKey == "shield" then shield = frame end
end
assert(panel:IsShown())
panel.mouseOver = true; Fire("GLOBAL_MOUSE_DOWN", "LeftButton")
assert(panel:IsShown()) -- Controls and title-bar drags keep the selection.
panel.mouseOver = false; ready.mouseOver = true
Fire("GLOBAL_MOUSE_DOWN", "LeftButton"); assert(panel:IsShown())
ready.scripts.OnDragStart(ready)
cursorX, cursorY = 30, 20; ready.scripts.OnUpdate()
ready.scripts.OnDragStop(ready)
assert(PriestShieldTrackerDB.groups.weakenedSoul.x == 30 and panel:IsShown())
ready.mouseOver = false; shield.mouseOver = true
Fire("GLOBAL_MOUSE_DOWN", "LeftButton"); ClickGroup("shield")
assert(panel:IsShown() and panel.subtitle.text == "Absorb display")
shield.mouseOver = false; Fire("GLOBAL_MOUSE_DOWN", "LeftButton")
assert(not panel:IsShown() and not PriestShieldTrackerDB.locked and EditModeManagerFrame:IsShown())
ClickGroup("weakenedSoul"); assert(panel:IsShown())
Fire("GLOBAL_MOUSE_DOWN", "RightButton"); assert(not panel:IsShown())
''')
case("liquid animates with opaque combat values without inspecting fill geometry", "", r'''
absorb = 1100; Fire("UNIT_ABSORB_AMOUNT_CHANGED")
bar.texture.GetWidth = function() error("Cannot measure secret fill") end
bar.texture.GetHeight = function() error("Cannot measure secret fill") end
combat = true; absorb = secret; Fire("PLAYER_REGEN_DISABLED")
local fx = bar.liquid
local before = fx.clock
for i = 1, 40 do Tick(0.04) end
assert(fx.clock > before and rawequal(bar.value, secret))
assert(bar.barColor[4] == 0 and fx.clip.shown)
assert(fx.mover.points[1][2] == bar.texture)
absorb = secretZero; Fire("UNIT_ABSORB_AMOUNT_CHANGED"); Tick(0.04)
assert(not fx.clip:IsRendered())
assert(PriestShieldTrackerDB.reference == 1100)
''')
case("styles switch native smoothing and remove liquid while preserving live amount", "", r'''
Command("settings")
local panel = PriestShieldTrackerOptions
panel.style:Choose("Smooth")
Command("lock"); absorb = 600; Fire("UNIT_ABSORB_AMOUNT_CHANGED")
assert(bar.value == 600 and bar.interpolation == 1 and not bar.liquid.clip.shown and bar.barColor[4] == 1)
Command("settings")
panel.style:Choose("Classic")
Command("lock"); Fire("UNIT_ABSORB_AMOUNT_CHANGED")
assert(bar.value == 600 and bar.interpolation == nil and not bar.liquid.clip.shown)
''')
case("palette colors reach preview live bars and native aura-owned text", "", r'''
Command("settings")
PriestShieldTrackerOptions.palette:Choose("Holy")
assert(PriestShieldTrackerDB.appearance.preset == "Holy")
assert(bar.liquid.rows[1].body.vertexColor[1] == 0.95)
assert(sample.absorb.liquid.rows[1].body.vertexColor[1] == 0.95)
local shield = Find("AuraContainer").slots.shield.button
assert(shield.durationBar.barColor[1] == 1 and shield.durationBar.barColor[2] == 0.84)
assert(FindText(shield, "Shield expires in").textColor[3] == 0.77)
assert(sample.ws.textColor[2] == 0.88)
''')
case("color picker edits all text while layout is locked and restores on cancel", "", r'''
ColorPickerFrame = CreateFrame("Frame", "ColorPickerFrame", UIParent)
function ColorPickerFrame:SetupColorPickerAndShow(info) self.info = info; self:Show() end
function ColorPickerFrame:GetColorRGB() return 0.2, 0.3, 0.4 end
Command("settings")
PriestShieldTrackerOptions.textColor.scripts.OnClick()
ColorPickerFrame.info.swatchFunc()
assert(bar.amountText.textColor[1] == 0.2 and sample.time.textColor[2] == 0.3)
assert(PriestShieldTrackerDB.appearance.preset == "Custom")
ColorPickerFrame.mouseOver = true; Fire("GLOBAL_MOUSE_DOWN", "LeftButton")
assert(PriestShieldTrackerOptions:IsVisible() and PriestShieldTrackerDB.locked)
ColorPickerFrame.info.cancelFunc()
assert(bar.amountText.textColor[1] == 1 and PriestShieldTrackerDB.appearance.preset == "Soul")
PriestShieldTrackerOptions:Hide()
assert(not ColorPickerFrame.shown and not PriestShieldTrackerOptions.shown)
''')
case("combat disables options and closes picker ignoring late callbacks", "", r'''
ColorPickerFrame = CreateFrame("Frame", "ColorPickerFrame", UIParent)
function ColorPickerFrame:SetupColorPickerAndShow(info) self.info = info; self:Show() end
function ColorPickerFrame:GetColorRGB() return 0, 0, 0 end
Command("settings")
PriestShieldTrackerOptions.textColor.scripts.OnClick()
combat = true; absorb = secret; Fire("PLAYER_REGEN_DISABLED")
ColorPickerFrame.info.swatchFunc(); ColorPickerFrame.info.cancelFunc()
assert(not PriestShieldTrackerOptions.style.enabled and not ColorPickerFrame.shown)
assert(PriestShieldTrackerDB.appearance.colors.ready[1] == 0.94)
for i = 1, 30 do Tick(0.05) end
''')
case("invalid saved appearance repairs channels and preserves layout", '''
PriestShieldTrackerDB = { width = 320, appearance = { style = "broken", preset = false,
    colors = { absorb = { 2, 0, 0 }, duration = { 0/0, 0, 0 }, numbers = { 0.1, 0.2, 0.3 } } } }
''', r'''
assert(PriestShieldTrackerDB.appearance.style == "liquid" and PriestShieldTrackerDB.appearance.preset == "Soul")
assert(bar.width == 320 and bar.amountText.textColor[3] == 0.3)
assert(PriestShieldTrackerDB.appearance.colors.absorb[1] == 0.55)
assert(PriestShieldTrackerDB.appearance.colors.duration[1] == 0.63)
''')
case("liquid resizes without reallocating texture pools during animation", "", r'''
Command("edit"); ClickGroup("shield")
PriestShieldTrackerEditSettings.controls.width:SetValue(400)
PriestShieldTrackerEditSettings.controls.barHeight:SetValue(40)
PriestShieldTrackerEditSettings.controls.groupScale:SetValue(150)
assert(bar.liquid.width == 600 and sample.absorb.liquid.height == 60)
local count = #frames
for i = 1, 1000 do Tick(0.04) end
assert(#frames == count)
''')
case("saved custom palette and style restore without starting preview", '''
PriestShieldTrackerDB = { appearance = { style = "smooth", preset = "Custom", colors = {
    ready = { 0.1, 0.2, 0.3 }, cross = { 0.6, 0.5, 0.4 } } } }
''', r'''
assert(PriestShieldTrackerDB.locked and not sample:IsVisible() and not bar.liquid.clip.shown)
assert(sample.ws.textColor[1] == 0.1 and sample.readyCross.textColor[3] == 0.4)
assert(bar.interpolation == 1)
''')
case("login during combat initializes selected colors without protected restyling", '''
combat = true; absorb = secret
PriestShieldTrackerDB = { appearance = { style = "classic", colors = { absorb = { 0.1, 0.7, 0.2 } } } }
''', r'''
assert(not bar.liquid.clip.shown and bar.barColor[2] == 0.7 and bar.barColor[4] == 1)
assert(rawequal(bar.value, secret))
combat = false; absorb = 0; Fire("PLAYER_REGEN_ENABLED")
assert(not bar.liquid.clip.shown)
''')
case("clients without native interpolation retain working fill and preview", "Enum.StatusBarInterpolation = nil", r'''
absorb = secret; Fire("UNIT_ABSORB_AMOUNT_CHANGED"); Tick(0.04)
assert(rawequal(bar.value, secret) and bar.interpolation == nil)
Command("test"); Tick(0.04)
assert(sample:IsVisible() and sample.absorb.interpolation == nil)
''')
case("minimap left click opens registered AddOns category and exits layout editing", "EnableNativeEditMode()", r'''
assert(#Settings.categories == 1 and Settings.categories[1].name == "PriestShieldTracker")
assert(not SettingsPanel:IsVisible() and not PriestShieldTrackerOptions:IsVisible())
Command("edit"); ClickGroup("shield")
PriestShieldTrackerMinimapButton.scripts.OnClick(PriestShieldTrackerMinimapButton, "LeftButton")
assert(Settings.opened == Settings.categories[1]:GetID() and PriestShieldTrackerOptions:IsVisible())
assert(PriestShieldTrackerDB.locked and not EditModeManagerFrame:IsVisible() and not sample:IsVisible())
assert(PriestShieldTrackerAppearance == nil and PriestShieldTrackerEditSettings.appearanceButton == nil)
''')
case("minimap right click opens Edit Mode focused on Shield Ready", "EnableNativeEditMode()", r'''
Command("settings")
PriestShieldTrackerMinimapButton.scripts.OnClick(PriestShieldTrackerMinimapButton, "RightButton")
assert(EditModeManagerFrame:IsShown() and not SettingsPanel:IsShown())
assert(not PriestShieldTrackerDB.locked and PriestShieldTrackerEditSettings:IsVisible())
assert(PriestShieldTrackerEditSettings.subtitle.text == "Shield Ready")
assert(PriestShieldTrackerEditSettings.controls.fontSize:IsVisible() and PriestShieldTrackerEditSettings.controls.iconSize:IsVisible())
assert(not PriestShieldTrackerEditSettings.controls.width:IsVisible())
assert(PriestShieldTrackerEditSettings.controls.showIcon == nil and PriestShieldTrackerEditSettings.appearanceButton == nil)
for _, f in ipairs(frames) do
    if f.groupKey == "weakenedSoul" then assert(f.selection.color[4] == 0.36) end
end
''')
case("minimap launcher and stale dropdown actions cannot edit in combat", "EnableNativeEditMode()", r'''
Command("settings")
PriestShieldTrackerOptions.style:GenerateMenu()
local action = PriestShieldTrackerOptions.style.choices[1].action
combat = true; absorb = secret; Fire("PLAYER_REGEN_DISABLED")
action()
assert(PriestShieldTrackerDB.appearance.style == "liquid" and not PriestShieldTrackerOptions.style.enabled)
SettingsPanel:Hide()
PriestShieldTrackerMinimapButton.scripts.OnClick(PriestShieldTrackerMinimapButton, "LeftButton")
PriestShieldTrackerMinimapButton.scripts.OnClick(PriestShieldTrackerMinimapButton, "RightButton")
assert(not SettingsPanel:IsVisible() and not EditModeManagerFrame:IsShown() and PriestShieldTrackerDB.locked)
combat = false; absorb = 0; Fire("PLAYER_REGEN_ENABLED")
assert(PriestShieldTrackerOptions.style.enabled and PriestShieldTrackerOptions.textColor.enabled)
''')
case("minimap dragging saves angle without opening a menu", "", r'''
local button = PriestShieldTrackerMinimapButton
local before = PriestShieldTrackerDB.minimapAngle
cursorX, cursorY = 1240, 760
button.scripts.OnDragStart(); button.scripts.OnUpdate(); button.scripts.OnDragStop()
assert(PriestShieldTrackerDB.minimapAngle ~= before and not button.scripts.OnUpdate)
button.scripts.OnClick(button, "LeftButton")
assert(PriestShieldTrackerDB.locked and PriestShieldTrackerEditSettings == nil)
button.scripts.OnMouseDown(); button.scripts.OnClick(button, "RightButton")
assert(not PriestShieldTrackerDB.locked and PriestShieldTrackerEditSettings.subtitle.text == "Shield Ready")
''')
case("minimap restores saved position and repairs invalid angles", "PriestShieldTrackerDB = { minimapAngle = 30 }", r'''
assert(PriestShieldTrackerDB.minimapAngle == 30)
assert(math.abs(PriestShieldTrackerMinimapButton.points[1][5] - 39) < 0.001)
''')
case("icon visibility lives in Options and layout reset preserves it", "EnableNativeEditMode()", r'''
Command("settings")
local check = PriestShieldTrackerOptions.showIcon
check:SetChecked(false); check.scripts.OnClick(check)
assert(not PriestShieldTrackerDB.groupOptions.weakenedSoul.showIcon)
PriestShieldTrackerOptions.editButton.scripts.OnClick()
assert(not sample.readyIcon.shown and not sample.readyCross.shown)
PriestShieldTrackerEditSettings.resetButton.scripts.OnClick()
assert(not PriestShieldTrackerDB.groupOptions.weakenedSoul.showIcon and not sample.readyIcon.shown)
Command("settings"); check:SetChecked(true); check.scripts.OnClick(check)
PriestShieldTrackerOptions.editButton.scripts.OnClick()
assert(sample.readyIcon.shown and sample.readyCross.shown)
''')
case("simplified bar color edits both bars and Cancel restores their distinct colors", "", r'''
ColorPickerFrame = CreateFrame("Frame", "ColorPickerFrame", UIParent)
function ColorPickerFrame:SetupColorPickerAndShow(info) self.info = info; self:Show() end
function ColorPickerFrame:GetColorRGB() return 0.2, 0.7, 0.4 end
Command("settings"); PriestShieldTrackerOptions.barColor.scripts.OnClick()
ColorPickerFrame.info.swatchFunc()
local colors = PriestShieldTrackerDB.appearance.colors
assert(colors.absorb[2] == 0.7 and colors.duration[2] == 0.7)
assert(colors.labels[1] == 0.9 and colors.background[1] == 0.035)
ColorPickerFrame.info.cancelFunc()
assert(colors.absorb[1] == 0.55 and colors.duration[1] == 0.63 and PriestShieldTrackerDB.appearance.preset == "Soul")
PriestShieldTrackerOptions.barColor.scripts.OnClick()
local stale = ColorPickerFrame.info.swatchFunc
PriestShieldTrackerOptions:Hide(); stale()
assert(colors.absorb[1] == 0.55)
''')
case("appearance reset preserves sizes positions and reference", "", r'''
absorb = 1100; Fire("UNIT_ABSORB_AMOUNT_CHANGED")
Command("width 390"); Command("settings")
PriestShieldTrackerDB.groups.shield.x = 75
PriestShieldTrackerDB.groupOptions.weakenedSoul.fontSize = 22
PriestShieldTrackerOptions.style:Choose("Classic"); PriestShieldTrackerOptions.palette:Choose("Holy")
PriestShieldTrackerOptions.resetButton.scripts.OnClick()
assert(PriestShieldTrackerDB.width == 390 and PriestShieldTrackerDB.groups.shield.x == 75)
assert(PriestShieldTrackerDB.groupOptions.weakenedSoul.fontSize == 22 and PriestShieldTrackerDB.reference == 1100)
assert(PriestShieldTrackerDB.appearance.style == "liquid" and PriestShieldTrackerDB.appearance.preset == "Soul")
''')
case("settings preview uses sample values without modifying live shield reference", "", r'''
absorb = 1100; Fire("UNIT_ABSORB_AMOUNT_CHANGED")
absorb = 600; Fire("UNIT_ABSORB_AMOUNT_CHANGED")
Command("settings")
assert(PriestShieldTrackerOptions.previewAbsorb ~= bar and not PriestShieldTrackerOptions.previewAbsorb.nativeOwned)
for i = 1, 100 do Tick(0.1) end
assert(bar.value == 600 and bar.maximum == 1100 and PriestShieldTrackerDB.reference == 1100)
assert(PriestShieldTrackerOptions.previewAbsorb.value >= 500 and PriestShieldTrackerOptions.previewAbsorb.value <= 1400)
''')
case("missing Settings or Minimap APIs leave the tracker and slash editor working", "Settings = nil; Minimap = nil", r'''
assert(hud and PriestShieldTrackerOptions == nil and PriestShieldTrackerMinimapButton == nil)
Command("edit"); assert(sample:IsVisible())
Command("lock"); Command("settings")
assert(PriestShieldTrackerDB.locked and #messages == 1)
''')
case("right click toggles native Edit Mode closed and can open it again", "EnableNativeEditMode()", r'''
local button = PriestShieldTrackerMinimapButton
button.scripts.OnClick(button, "RightButton")
assert(not PriestShieldTrackerDB.locked and PriestShieldTrackerEditSettings.subtitle.text == "Shield Ready")
ClickGroup("shield")
button.scripts.OnClick(button, "RightButton")
assert(PriestShieldTrackerDB.locked and not EditModeManagerFrame:IsVisible())
assert(not PriestShieldTrackerEditSettings:IsVisible() and not sample:IsVisible())
button.scripts.OnClick(button, "RightButton")
assert(not PriestShieldTrackerDB.locked and EditModeManagerFrame:IsVisible())
assert(PriestShieldTrackerEditSettings.subtitle.text == "Shield Ready")
''')
case("right click toggles fallback and externally opened Edit Mode", "", r'''
local button = PriestShieldTrackerMinimapButton
Command("edit"); ClickGroup("shield")
button.scripts.OnClick(button, "RightButton")
assert(PriestShieldTrackerDB.locked and not sample:IsVisible() and not PriestShieldTrackerEditSettings:IsVisible())
button.scripts.OnClick(button, "RightButton")
assert(not PriestShieldTrackerDB.locked and PriestShieldTrackerEditSettings.subtitle.text == "Shield Ready")
button.scripts.OnClick(button, "RightButton")
assert(PriestShieldTrackerDB.locked)
''')
case("palette dropdown contains six working presets without a Custom option", "", r'''
Command("settings"); PriestShieldTrackerOptions.palette:GenerateMenu()
assert(#PriestShieldTrackerOptions.palette.choices == 6)
for _, choice in ipairs(PriestShieldTrackerOptions.palette.choices) do assert(choice.text ~= "Custom") end
PriestShieldTrackerOptions.palette:Choose("Holy")
assert(PriestShieldTrackerDB.appearance.preset == "Holy")
PriestShieldTrackerOptions.palette:Choose("Emerald")
assert(PriestShieldTrackerDB.appearance.preset == "Emerald")
''')
case("previous character settings migrate with layout colors and calibration intact", '''
SoulShieldDB = { width = 350, x = 85, reference = 1100, minimapAngle = 30,
    appearance = { style = "smooth", preset = "Frost", colors = { absorb = { 0.1, 0.6, 0.9 } } },
    groups = { shield = { x = 40, y = -10 } } }
absorb = 600
''', r'''
assert(PriestShieldTrackerDB == SoulShieldDB)
assert(PriestShieldTrackerDB.width == 350 and PriestShieldTrackerDB.x == 85)
assert(PriestShieldTrackerDB.groups.shield.x == 40 and PriestShieldTrackerDB.appearance.preset == "Frost")
assert(bar.maximum == 1100 and bar.value == 600 and PriestShieldTrackerDB.minimapAngle == 30)
assert(PriestShieldTrackerDB.locked and not sample:IsVisible())
''')
case("new settings take precedence over previous settings on later logins", '''
SoulShieldDB = { width = 350, x = 85 }
PriestShieldTrackerDB = { width = 300, x = -25 }
''', r'''
assert(PriestShieldTrackerDB.width == 300 and PriestShieldTrackerDB.x == -25)
assert(PriestShieldTrackerDB ~= SoulShieldDB and SoulShieldDB.width == 350)
''')
case("renamed public identity and commands are registered", "", r'''
assert(SLASH_PRIESTSHIELDTRACKER1 == "/priestshieldtracker")
assert(SLASH_PRIESTSHIELDTRACKER2 == "/pst" and SLASH_PRIESTSHIELDTRACKER3 == "/ss")
assert(Settings.categories[1].name == "PriestShieldTracker")
assert(PriestShieldTrackerHUD and PriestShieldTrackerMinimapButton and SoulShieldHUD == nil)
''')
print("60 logic checks passed; live client validation remains required.")
