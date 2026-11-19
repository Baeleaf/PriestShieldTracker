"""Run real Lua 5.1 against a small, strict WoW UI boundary model.

This verifies addon logic, not the game's rendering or secret execution engine.
Run with Python and lupa installed: python tests/check.py
"""
from pathlib import Path
import json
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
LOCALIZATION = (ROOT / "Localization.lua").read_text(encoding="utf-8")
SOURCE = (ROOT / "PriestShieldTracker.lua").read_text(encoding="utf-8")
COMPATIBILITY = (ROOT / "Compatibility.lua").read_text(encoding="utf-8")
APPEARANCE = (ROOT / "Appearance.lua").read_text(encoding="utf-8")
OPTIONS = (ROOT / "Options.lua").read_text(encoding="utf-8")
ACCESS = (ROOT / "Access.lua").read_text(encoding="utf-8")
GROUP_NATIVE = (ROOT / "GroupAuraNative.lua").read_text(encoding="utf-8")
GROUP_FRAMES = (ROOT / "GroupFrames.lua").read_text(encoding="utf-8")
EXECUTE = (ROOT / "Execute.lua").read_text(encoding="utf-8")
ACTION_GLOW = (ROOT / "ActionGlow.lua").read_text(encoding="utf-8")
STUBS = r'''
frames = {}
messages = {}
combat = false
auraRestricted = false
clock = 100
absorb = 0
healthMaximum = 2400
cursorX, cursorY = 0, 0
class = "PRIEST"
neverSecret = false
nativeAvailable = true
SlashCmdList = {}
Enum = { SecrecyLevel = { NeverSecret = 0 }, StatusBarTimerDirection = { RemainingTime = 1 },
    StatusBarInterpolation = { Immediate = 0, ExponentialEaseOut = 1 },
    LuaCurveType = { Step = 1 }, NumericRuleFormatRounding = { Nearest = 1, Up = 2 },
    DurationTextBindingProperty = { RemainingDuration = 1 } }
CustomAuraContainerSlotDefaultOptions = {}
C_AuraContainerUtil = {}
GameTooltip = { SetOwner = function(self, owner) self.owner = owner end,
    SetText = function(self, text) self.title = text end,
    AddLine = function(self, text) self.description = text end,
    Show = function(self) self.shown = true end, Hide = function(self) self.shown = false end }
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
local blockedWrites = 0
local function RequireWritable(frame)
    local ancestor = frame
    while ancestor do
        if ancestor.secureAction and combat then
            blockedWrites = blockedWrites + 1
            error("Cannot modify a secure action button during combat")
        end
        if ancestor.kind == "Button" and ancestor.restricted and (combat or auraRestricted) then
            blockedWrites = blockedWrites + 1
            error("Attempt to access forbidden object from addon code")
        end
        ancestor = ancestor.parent
    end
end
function BlockedWrites() return blockedWrites end
function Frame:CanBeAccessedInContext()
    local ancestor = self
    while ancestor do
        if ancestor.accessResult then return ancestor.accessResult end
        if ancestor.forbidden or (ancestor.kind == "Button" and ancestor.restricted and (combat or auraRestricted)) then return false end
        ancestor = ancestor.parent
    end
    return true
end
function Frame:IsForbidden() return self.forbidden == true end
function Frame:GetName() return self.name end
function Frame:SetHeight(v) RequireWritable(self); self.height = v end
function Frame:SetWidth(v) RequireWritable(self); self.width = v end
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
function Frame:SetSize(w,h) RequireWritable(self); self.width = w; self.height = h end
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
function Frame:HookScript(event, fn)
    local previous = self.scripts[event]
    self.scripts[event] = function(...)
        if previous then previous(...) end
        fn(...)
    end
end
function Frame:SetHitRectInsets(...) self.hitRectInsets = {...} end
function Frame:GetScript(event) return self.scripts[event] end
function Frame:RegisterEvent(event)
    assert(event ~= "LEARNED_SPELL_IN_TAB", 'Attempt to register unknown event "LEARNED_SPELL_IN_TAB"')
    self.events[event] = true
end
function Frame:RegisterUnitEvent(event, unit) self.events[event] = unit end
function Frame:SetAllPoints(v) self.allPoints = v end
function Frame:SetClipsChildren(value) self.clipsChildren = value end
function Frame:SetScrollChild(child) self.scrollChild = child end
function Frame:SetPoint(...)
    RequireWritable(self)
    table.insert(self.points, {...})
end
function Frame:ClearAllPoints() RequireWritable(self); self.points = {} end
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
function Frame:SetColorTexture(...) RequireWritable(self); self.color = {...} end
function Frame:SetVertexColor(...) self.vertexColor = {...} end
function Frame:SetBlendMode(value) self.blend = value end
function Frame:SetTexture(value) self.asset = value end
function Frame:SetTexCoord(...) self.texCoord = {...} end
function Frame:SetFont(font, size, flags) RequireWritable(self); self.fontSize = size; self.fontFlags = flags end
function Frame:SetTextColor(...) RequireWritable(self); self.textColor = {...} end
function Frame:SetShadowOffset(...) self.shadowOffset = {...} end
function Frame:SetJustifyH(value) self.justifyH = value end
function Frame:SetText(v) self.text = v end
function Frame:SetFormattedText(fmt, v)
    RequireWritable(self)
    self.formattedValue = v
    if not issecretvalue(v) then self.text = string.format(fmt, v) end
end
function Frame:SetShown(v)
    RequireWritable(self)
    assert(not (self.kind == "AuraContainer" and self.restricted), "Do not toggle a restricted container")
    local wasShown = self.shown
    self.shown = v
    if wasShown and not v and self.scripts.OnHide then self.scripts.OnHide(self) end
    if not wasShown and v and self.scripts.OnShow then self.scripts.OnShow(self) end
end
function NativeShown(frame, shown) frame.shown = shown end
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
    -- C-side rectangle intersection for a fixed clip following a fill edge.
    -- These coordinates/health values are never exposed back to addon code.
    if self.clipsChildren and #self.points == 1 then
        local anchor = self.points[1]
        local fill = anchor[2]
        if fill and fill.kind == "Texture" and fill.parent.kind == "StatusBar"
            and anchor[3] == "TOPRIGHT" and self.width then
            local meter = fill.parent
            local value = meter.value
            local nativeValue = issecretvalue(value) and (rawget(value, "nativeValue") or 1) or value
            local proportion = math.max(0, math.min(1, (nativeValue - meter.minimum) / (meter.maximum - meter.minimum)))
            local left = proportion * meter.width
            if anchor[1] == "TOPRIGHT" then left = left - self.width end
            clipVisible = left < meter.width and left + self.width > 0
        end
    end
    return alphaVisible and clipVisible and self.shown and (not self.parent or self.parent:IsRendered())
end
function Frame:StartMoving() self.moving = true end
function Frame:StopMovingOrSizing() self.moving = false end
function Frame:GetWidth() return self.width end
function Frame:GetHeight() return self.height end
function Frame:GetCenter() return 1200, 700 end
function Frame:GetEffectiveScale() return self.scale or 1 end
function Frame:GetEffectiveAlpha() if self.alpha == nil then return 1 else return self.alpha end end
function Frame:CreateTexture() return CreateFrame("Texture", nil, self) end
function Frame:CreateFontString() return CreateFrame("FontString", nil, self) end
function Frame:SetDurationBar(v, opts)
    assert(v.parent == self and opts.direction == Enum.StatusBarTimerDirection.RemainingTime)
    self.durationBar = v
end
function Frame:SetDurationText(v, options)
    RequireWritable(self)
    assert(v.parent == self)
    self.durationText = v; self.durationOptions = options
end
function Frame:SetSpellName(v) assert(v.parent == self); self.spellName = v end
function Frame:SetIcon(v) assert(v.parent == self); self.icon = v end
function Frame:SetDurationCooldown(v) assert(v.parent == self); self.cooldown = v end
function Frame:SetDrawEdge(v) self.drawEdge = v end
function Frame:SetCooldown(start, duration) self.cooldownStart = start; self.cooldownDuration = duration end
function Frame:SetHideCountdownNumbers(v) self.hideCountdownNumbers = v end
function Frame:SetAuraSlotEnabled(key, enabled) self.slots[key].enabled = enabled end
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
    if template == "ActionButtonSpellAlertTemplate" then
        frame.shown = false
        frame.ProcLoop = { plays = 0, Play = function(self) self.plays = self.plays + 1 end,
            Stop = function(self) self.stopped = true end }
    end
    return frame
end
function CreateColor(...) return {...} end
function C_CurveUtil.CreateColorCurve()
    return { points = {}, SetType = function(self, v) self.curveType = v end,
        AddPoint = function(self, x, color) table.insert(self.points, {x, color}) end }
end
function C_CurveUtil.EvaluateColorValueFromBoolean(value, yes, no)
    if issecretvalue(value) then
        return setmetatable({ secret = true, rendered = rawget(value, "nativeValue") == true }, getmetatable(secret))
    end
    return value and yes or no
end
local oldFormatter = C_StringUtil.CreateNumericRuleFormatter
function C_StringUtil.CreateNumericRuleFormatter()
    local formatter = oldFormatter()
    function formatter:AddBreakpoint(point) self.breakpoints = {point} end
    return formatter
end
function hooksecurefunc(target, method, callback)
    if type(target) == "string" then
        local name = target
        local original, hook = _G[name], method
        _G[name] = function(...) local result = original(...); hook(...); return result end
    else
        local original = target[method]
        target[method] = function(...) local result = original(...); callback(...); return result end
    end
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
function Fire(event, argument, ...)
    for _, f in ipairs(frames) do
        if f.events[event] and f.scripts.OnEvent then f.scripts.OnEvent(f, event, argument or "player", ...) end
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
    lua.execute(LOCALIZATION, "PriestShieldTracker", namespace)
    lua.globals().localeText = namespace.L
    lua.globals().localization = namespace.Localization
    lua.execute(ACCESS, "PriestShieldTracker", namespace)
    lua.execute(COMPATIBILITY, "PriestShieldTracker", namespace)
    lua.execute(APPEARANCE, "PriestShieldTracker", namespace)
    lua.execute(GROUP_NATIVE, "PriestShieldTracker", namespace)
    lua.execute(GROUP_FRAMES, "PriestShieldTracker", namespace)
    lua.execute(OPTIONS, "PriestShieldTracker", namespace)
    lua.execute(ACTION_GLOW, "PriestShieldTracker", namespace)
    lua.globals().actionGlowModule = namespace.ActionGlow
    lua.execute(EXECUTE, "PriestShieldTracker", namespace)
    lua.globals().executeModule = namespace.Execute
    lua.execute(SOURCE, "PriestShieldTracker", namespace)
    lua.execute('''Fire("PLAYER_LOGIN"); hud = PriestShieldTrackerHUD
for _, f in ipairs(frames) do
    if f.parts then sample = f end
    if f.kind == "StatusBar" and f.absorbLabel and not f.parent.parts then bar = f end
end
''')
    return lua


cases_run = 0


def case(name, setup, assertions):
    global cases_run
    lua = new(setup)
    lua.execute(assertions)
    cases_run += 1
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
NativeShown(shield, false); absorb = secretZero; Fire("UNIT_ABSORB_AMOUNT_CHANGED")
assert(not bar:IsRendered() and debuff:IsVisible())
combat = false; absorb = 0; Fire("PLAYER_REGEN_ENABLED")
assert(not bar:IsRendered())
Command("test"); assert(sample.absorb:IsVisible() and not bar.nativeOwned and not bar:IsRendered())
Command("test"); assert(not bar.nativeOwned and not bar:IsRendered())
''')
case("two draggable shield groups preserve spacing and native ownership", "", r'''
Command("scale 1.5"); Command("unlock")
local handle, debuffHandle, count = nil, nil, 0
for _, f in ipairs(frames) do
    if f.groupKey then
        count = count + 1
        if f.groupKey == "shield" then handle = f elseif f.groupKey == "weakenedSoul" then debuffHandle = f end
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
NativeShown(shield, false); absorb = secretZero; Fire("UNIT_ABSORB_AMOUNT_CHANGED")
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
assert(clip.clipsChildren and clip.allPoints == nil)
assert(clip.points[1][1] == "TOPRIGHT" and clip.points[1][2] == gate:GetStatusBarTexture())
assert(clip.width == gate.width and clip.height == gate.height)
assert(gate.minimum == 0 and gate.maximum == 1)
assert(gate.points[1][4] == bar.points[1][4] and gate.points[1][5] == bar.points[1][5])
for i = 1, 600 do Tick(0.1) end
assert(not bar:IsRendered() and rawequal(gate.value, secretZero))
absorb = secret; Tick(0.1)
assert(bar:IsRendered() and rawequal(bar.value, secret) and rawequal(gate.value, secret))
absorb = secretZero; Tick(0.1); assert(not bar:IsRendered())
Command("width 320")
assert(gate.width == 320 and bar.width == 320 and clip.width == 320)
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
assert(controls.showIcon:IsVisible() and PriestShieldTrackerEditSettings.appearanceButton == nil)
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
assert(PriestShieldTrackerEditSettings.controls.showIcon:IsVisible() and PriestShieldTrackerEditSettings.appearanceButton == nil)
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
case("icon visibility lives only in Shield Ready Edit Mode and reset preserves it", "EnableNativeEditMode()", r'''
Command("settings")
assert(PriestShieldTrackerOptions.showIcon == nil)
PriestShieldTrackerOptions.editButton.scripts.OnClick()
local check = PriestShieldTrackerEditSettings.controls.showIcon
assert(check:IsVisible() and check:GetChecked())
check:SetChecked(false); check.scripts.OnClick(check)
assert(not PriestShieldTrackerDB.groupOptions.weakenedSoul.showIcon)
assert(not sample.readyIcon.shown and not sample.readyCross.shown)
PriestShieldTrackerEditSettings.resetButton.scripts.OnClick()
assert(not PriestShieldTrackerDB.groupOptions.weakenedSoul.showIcon and not sample.readyIcon.shown)
ClickGroup("shield"); assert(not check:IsVisible())
check:SetChecked(true); check.scripts.OnClick(check)
assert(not PriestShieldTrackerDB.groupOptions.weakenedSoul.showIcon)
ClickGroup("weakenedSoul"); assert(not check:GetChecked())
check:SetChecked(true); check.scripts.OnClick(check)
assert(sample.readyIcon.shown and sample.readyCross.shown)
combat = true; Fire("PLAYER_REGEN_DISABLED")
check:SetChecked(false); check.scripts.OnClick(check)
assert(PriestShieldTrackerDB.groupOptions.weakenedSoul.showIcon)
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
case("palette dropdown contains six named palettes and Random without a Custom option", "", r'''
Command("settings"); PriestShieldTrackerOptions.palette:GenerateMenu()
assert(#PriestShieldTrackerOptions.palette.choices == 7)
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
case("instance aura restrictions survive combat end without forbidden writes", "", r'''
local ct = Find("AuraContainer")
local ws, shield = ct.slots.weakenedSoul.button, ct.slots.shield.button
local originalWidth = shield.durationBar.width
auraRestricted = true
combat = true; Fire("PLAYER_REGEN_DISABLED")
combat = false; Fire("PLAYER_REGEN_ENABLED")
Command("width 390"); Command("settings")
PriestShieldTrackerOptions.palette:Choose("Holy")
PriestShieldTrackerOptions.editButton.scripts.OnClick()
PriestShieldTrackerEditSettings.controls.showIcon:SetChecked(false)
PriestShieldTrackerEditSettings.controls.showIcon.scripts.OnClick(PriestShieldTrackerEditSettings.controls.showIcon)
Command("lock")
for i = 1, 30 do Tick(0.1) end
assert(BlockedWrites() == 0 and shield.durationBar.width == originalWidth)
absorb = secret; Fire("UNIT_ABSORB_AMOUNT_CHANGED")
assert(rawequal(bar.value, secret) and rawequal(bar.amountText.formattedValue, secret))
auraRestricted = false
Tick(1)
assert(shield.durationBar.width == 390 and shield.durationBar.barColor[1] == 1)
for _, f in ipairs(frames) do
    if f.parent == ws and f.asset then assert(not f.shown) end
end
assert(Find("AuraContainer") == ct and BlockedWrites() == 0)
''')
case("secret object access results defer layout instead of branching on secrets", "", r'''
local ct = Find("AuraContainer")
for _, slot in pairs(ct.slots) do slot.button.accessResult = secret end
local width = ct.slots.shield.button.durationBar.width
Command("width 410"); Fire("PLAYER_REGEN_ENABLED"); Tick(1)
assert(ct.slots.shield.button.durationBar.width == width and BlockedWrites() == 0)
for _, slot in pairs(ct.slots) do slot.button.accessResult = nil end
Fire("PLAYER_ENTERING_WORLD")
assert(ct.slots.shield.button.durationBar.width == 410 and BlockedWrites() == 0)
''')

GROUP_SETUP = r'''
function CompactUnitFrame_SetUnit(frame, unit) frame.unit = unit end
function CompactUnitFrame_UpdateAll(frame) end
CompactPartyFrameMember1 = CreateFrame("Frame", "CompactPartyFrameMember1", UIParent)
CompactPartyFrameMember1.unit = "player"
CompactPartyFrameMember2 = CreateFrame("Frame", "CompactPartyFrameMember2", UIParent)
CompactPartyFrameMember2.unit = "party1"
CompactRaidGroup2Member3 = CreateFrame("Frame", "CompactRaidGroup2Member3", UIParent)
CompactRaidGroup2Member3.unit = "raid8"
PartyFrame = { MemberFrame1 = CreateFrame("Frame", "ClassicPartyMember1", UIParent) }
PartyFrame.MemberFrame1.unit = "party2"
function GroupContainer(parent)
    for _, f in ipairs(frames) do
        if f.kind == "AuraContainer" and f.parent and f.parent.parent == parent then return f end
    end
end
'''
case("standalone group icons retain upstream filters borders swipe and green countdown", GROUP_SETUP, r'''
assert(WeakenedSoulTrackerDB == nil and SlashCmdList.WEAKENEDSOULTRACKER == nil)
assert(PriestShieldTrackerOptions.parent.scrollChild == PriestShieldTrackerOptions)
for _, frame in ipairs({CompactPartyFrameMember1, CompactPartyFrameMember2, CompactRaidGroup2Member3, PartyFrame.MemberFrame1}) do
    local ct = GroupContainer(frame)
    assert(ct and ct.enabled and ct.unit == frame.unit)
    local mine, others = ct.slots.mine, ct.slots.others
    assert(mine.filter == "HARMFUL|PLAYER" and others.filter == "HARMFUL")
    assert(mine.options.candidateFilters.maxDuration == 15.5)
    assert(others.options.candidateFilters.isFromPlayerOrPlayerPet == true and not others.enabled)
    local b = mine.button
    assert(b.width == 16 and b.height == 16 and b.mouse == false)
    assert(b.points[1][1] == "TOPRIGHT" and b.points[1][4] == -2)
    assert(b.icon and b.cooldown and b.cooldown.hideCountdownNumbers and b.cooldown.drawEdge == false)
    assert(b.durationText and b.durationOptions.textColor.curve.points[2][1] == 3)
    assert(b.level > others.button.level)
    local border
    for _, child in ipairs(frames) do if child.parent == b and child.color then border = child end end
    assert(border and border.color[1] == 0.9 and border.shown)
end
''')
case("group hooks reassign units reject unrelated frames and never duplicate icons", GROUP_SETUP, r'''
local frame = CompactPartyFrameMember2
local ct = GroupContainer(frame)
CompactUnitFrame_SetUnit(frame, "party3")
assert(ct.unit == "party3")
CompactUnitFrame_SetUnit(frame, "target")
assert(not ct.enabled)
CompactUnitFrame_SetUnit(frame, "party1")
assert(ct.enabled and ct.unit == "party1")
local count = #frames
for i = 1, 20 do CompactUnitFrame_UpdateAll(frame); Fire("GROUP_ROSTER_UPDATE") end
assert(#frames == count)
local enemy = CreateFrame("Frame", "NamePlate1", UIParent); enemy.unit = "party1"
CompactUnitFrame_UpdateAll(enemy)
assert(GroupContainer(enemy) == nil)
frame.unit = secret; Fire("GROUP_ROSTER_UPDATE")
assert(not ct.enabled and BlockedWrites() == 0)
''')
case("group indicator settings defer inside instance and recover when access returns", GROUP_SETUP, r'''
local ct = GroupContainer(CompactPartyFrameMember2)
Command("settings")
auraRestricted = true
PriestShieldTrackerOptions.groupSize:Choose("24 px")
PriestShieldTrackerOptions.groupCorner:Choose("Bottom left")
PriestShieldTrackerOptions.groupTime:Choose("Number (5)")
PriestShieldTrackerOptions.groupOthers:SetChecked(true)
PriestShieldTrackerOptions.groupOthers.scripts.OnClick(PriestShieldTrackerOptions.groupOthers)
Fire("PLAYER_REGEN_ENABLED"); Tick(1)
assert(ct.slots.mine.button.width == 16 and BlockedWrites() == 0)
assert(ct.slots.others.enabled and ct.slots.mine.button.mouse == false)
auraRestricted = false; Tick(1)
assert(ct.slots.mine.button.width == 24 and ct.slots.mine.button.points[1][1] == "BOTTOMLEFT")
assert(ct.slots.mine.button.durationOptions.textFormatter.breakpoints[1].format == "%d")
PriestShieldTrackerOptions.groupFrames:SetChecked(false)
PriestShieldTrackerOptions.groupFrames.scripts.OnClick(PriestShieldTrackerOptions.groupFrames)
assert(not ct.parent.shown and BlockedWrites() == 0)
PriestShieldTrackerOptions.groupFrames:SetChecked(true)
PriestShieldTrackerOptions.groupFrames.scripts.OnClick(PriestShieldTrackerOptions.groupFrames)
assert(ct.parent.shown)
''')
case("late group frames wait through combat then attach without external addons", GROUP_SETUP, r'''
combat = true; Fire("PLAYER_REGEN_DISABLED")
CompactRaidFrame7 = CreateFrame("Frame", "CompactRaidFrame7", UIParent)
CompactRaidFrame7.unit = "raid7"
Fire("GROUP_ROSTER_UPDATE")
assert(GroupContainer(CompactRaidFrame7) == nil)
combat = false; Fire("PLAYER_REGEN_ENABLED")
local ct = GroupContainer(CompactRaidFrame7)
assert(ct and ct.unit == "raid7" and ct.slots.mine.button.durationText and BlockedWrites() == 0)
''')
case("exact group aura filtering is retained when Weakened Soul is never secret", GROUP_SETUP + "\nneverSecret = true", r'''
local ct = GroupContainer(CompactPartyFrameMember2)
assert(ct.slots.mine.options.candidateFilters.includeSpellIDs[6788])
assert(ct.slots.others.options.candidateFilters.includeSpellIDs[6788] and ct.slots.others.enabled)
''')
case("non-priests never attach group indicators", GROUP_SETUP + '\nclass = "WARRIOR"', r'''
assert(GroupContainer(CompactPartyFrameMember1) == nil and PriestShieldTrackerDB == nil)
''')
case("settings preview retains live text contrast across every palette", "", r'''
Command("settings")
local panel = PriestShieldTrackerOptions
local label = FindText(panel.previewAbsorb.parent, "Absorb")
-- FindText checks direct children; bar text is deliberately in its own overlay.
for _, frame in ipairs(frames) do
    if frame.parent and frame.parent.parent == panel.previewAbsorb and frame.text == "Absorb" then label = frame end
end
assert(label and label.fontFlags == "OUTLINE" and label.shadowOffset[1] == 1 and label.shadowOffset[2] == -1)
assert(label.parent:GetFrameLevel() > panel.previewAbsorb.liquid.clip:GetFrameLevel())
for _, choice in ipairs(panel.palette.choices) do
    choice.action()
    assert(label.textColor[1] == bar.absorbLabel.textColor[1])
    assert(label.textColor[2] == bar.absorbLabel.textColor[2])
    assert(label.textColor[3] == bar.absorbLabel.textColor[3])
end
''')
case("sample raid icons follow settings and their own timer without real units", GROUP_SETUP, r'''
Command("settings")
local panel = PriestShieldTrackerOptions
local mine, others = panel.raidPreview.mine, panel.raidPreview.others
assert(mine.button:IsVisible() and not others.button:IsVisible())
assert(mine.button.mouse == false and mine.cooldown.mouse == false)
assert(mine.cooldown.cooldownDuration == 15 and mine.text.text == "15s")
panel.groupOthers:SetChecked(true); panel.groupOthers.scripts.OnClick(panel.groupOthers)
assert(others.button:IsVisible() and others.border.color[3] == 1)
panel.groupCorner:Choose("Bottom left"); panel.groupSize:Choose("24 px")
assert(mine.button.width == 24 and mine.button.points[1][1] == "BOTTOMLEFT")
panel.groupTime:Choose("Number (5)")
clock = clock + 13; Tick(0.2)
assert(mine.text.text == "2" and mine.text.textColor[2] == 1 and mine.text.textColor[1] == 0.25)
panel.groupSoon:Choose("Off")
assert(mine.text.textColor[1] == 1)
panel.groupTime:Choose("Icon only"); assert(mine.text.text == "")
panel.groupFrames:SetChecked(false); panel.groupFrames.scripts.OnClick(panel.groupFrames)
assert(not mine.button:IsVisible() and not others.button:IsVisible())
panel.groupFrames:SetChecked(true); panel.groupFrames.scripts.OnClick(panel.groupFrames)
assert(mine.button:IsVisible() and others.button:IsVisible())
assert(GroupContainer(CompactPartyFrameMember1).slots.mine.button.width == 24)
assert(mine.container.unit == nil and mine.button.kind == "Frame")
''')
case("Edit Mode enables groups independently and disabled groups stay reachable", "EnableNativeEditMode()", r'''
Command("settings")
assert(PriestShieldTrackerOptions.readyGroup == nil and PriestShieldTrackerOptions.shieldGroup == nil)
PriestShieldTrackerOptions.editButton.scripts.OnClick()
local panel = PriestShieldTrackerEditSettings
local check = panel.controls.enabled
assert(check:GetChecked())
check:SetChecked(false); check.scripts.OnClick(check)
assert(not PriestShieldTrackerDB.groupOptions.weakenedSoul.enabled and not sample.ws.shown)
assert(PriestShieldTrackerDB.groupOptions.shield.enabled and sample.absorb.shown)
local ready
for _, frame in ipairs(frames) do if frame.groupKey == "weakenedSoul" then ready = frame end end
assert(ready:IsVisible() and ready.disabledText:IsVisible())
ClickGroup("shield"); assert(check:GetChecked())
check:SetChecked(false); check.scripts.OnClick(check)
assert(not sample.absorb.shown and not bar.parent.parent.shown)
ClickGroup("weakenedSoul"); assert(not check:GetChecked())
check:SetChecked(true); check.scripts.OnClick(check)
assert(sample.ws.shown and not ready.disabledText.shown and not sample.absorb.shown)
panel.saveButton.scripts.OnClick()
assert(PriestShieldTrackerDB.locked and not ready:IsVisible())
assert(Find("AuraContainer").slots.weakenedSoul.enabled and not Find("AuraContainer").slots.shield.enabled)
Command("edit"); ClickGroup("shield"); assert(not check:GetChecked())
check:SetChecked(true); check.scripts.OnClick(check)
assert(sample.absorb.shown and bar.parent.parent.shown)
combat = true; Fire("PLAYER_REGEN_DISABLED")
check:SetChecked(false); check.scripts.OnClick(check)
assert(PriestShieldTrackerDB.groupOptions.shield.enabled and not panel:IsVisible())
''')
case("hover help explains controls and clears on leaving", "", r'''
Command("settings")
local panel = PriestShieldTrackerOptions
for _, widget in ipairs(panel.widgets) do
    assert(widget.scripts.OnEnter and widget.scripts.OnLeave)
    widget.scripts.OnEnter(widget)
    assert(GameTooltip.shown and GameTooltip.owner == widget and #GameTooltip.description > 15)
    widget.scripts.OnLeave(widget); assert(not GameTooltip.shown)
end
panel.editButton.scripts.OnClick()
for _, control in pairs(PriestShieldTrackerEditSettings.controls) do
    control.scripts.OnEnter(control)
    assert(GameTooltip.shown and #GameTooltip.description > 15)
    control.scripts.OnLeave(control)
end
''')
case("saved disabled groups remain configurable and preview safe under aura locks", GROUP_SETUP + r'''
PriestShieldTrackerDB = { groupOptions = { weakenedSoul = { enabled = false }, shield = { enabled = false } } }
''', r'''
Command("edit")
for _, frame in ipairs(frames) do
    if frame.groupKey then assert(frame:IsVisible() and frame.disabledText.shown) end
end
ClickGroup("shield"); assert(not PriestShieldTrackerEditSettings.controls.enabled:GetChecked())
Command("settings")
auraRestricted = true; Tick(0.2)
assert(BlockedWrites() == 0 and PriestShieldTrackerOptions.raidPreview.mine.button:IsVisible())
''')
case("minimap left click toggles only this settings page and closes its picker", "", r'''
local button = PriestShieldTrackerMinimapButton
button.scripts.OnClick(button, "LeftButton")
assert(SettingsPanel:IsVisible() and PriestShieldTrackerOptions:IsVisible())
ColorPickerFrame = CreateFrame("Frame", "ColorPickerFrame", UIParent)
function ColorPickerFrame:SetupColorPickerAndShow(info) self.info = info; self:Show() end
function ColorPickerFrame:GetColorRGB() return 0, 0, 0 end
PriestShieldTrackerOptions.textColor.scripts.OnClick()
local stale = ColorPickerFrame.info.swatchFunc
assert(ColorPickerFrame:IsVisible())
button.scripts.OnClick(button, "LeftButton")
assert(not SettingsPanel:IsVisible() and not ColorPickerFrame:IsVisible())
stale(); assert(PriestShieldTrackerDB.appearance.preset == "Soul")
button.scripts.OnClick(button, "LeftButton")
assert(SettingsPanel:IsVisible() and PriestShieldTrackerOptions:IsVisible())
-- A different settings category must switch to our page rather than close.
Settings.categories[1].panel:Hide()
button.scripts.OnClick(button, "LeftButton")
assert(SettingsPanel:IsVisible() and PriestShieldTrackerOptions:IsVisible())
combat = true; Fire("PLAYER_REGEN_DISABLED")
button.scripts.OnClick(button, "LeftButton")
assert(not SettingsPanel:IsVisible())
button.scripts.OnClick(button, "LeftButton")
assert(not SettingsPanel:IsVisible())
''')
RANDOM_SETUP = r'''
randomInterval = 900
math.random = function(low, high)
    if low == 900 and high == 1800 then return randomInterval end
    return low
end
'''
case("Random rotates at 15 and 30 minute boundaries and never repeats immediately", RANDOM_SETUP, r'''
Command("settings"); PriestShieldTrackerOptions.palette:Choose("Random")
local appearance = PriestShieldTrackerDB.appearance
local first = appearance.activePreset
assert(appearance.preset == "Random" and first ~= "Soul")
Tick(899); assert(appearance.activePreset == first)
randomInterval = 1800
Tick(1)
local second = appearance.activePreset
assert(second ~= first and appearance.preset == "Random")
Tick(1799); assert(appearance.activePreset == second)
Tick(1); assert(appearance.activePreset ~= second)
local selected = false
for _, choice in ipairs(PriestShieldTrackerOptions.palette.choices) do
    if choice.text == "Random" then selected = choice.selected() end
end
assert(selected)
''')
case("Random waits through combat then updates accessible displays while aura timers stay locked", RANDOM_SETUP, r'''
Command("settings"); PriestShieldTrackerOptions.palette:Choose("Random")
local appearance = PriestShieldTrackerDB.appearance
local first = appearance.activePreset
combat = true; Fire("PLAYER_REGEN_DISABLED")
clock = clock + 2000; Tick(1)
assert(appearance.activePreset == first)
local shield = Find("AuraContainer").slots.shield.button
local oldTimerRed = shield.durationBar.barColor[1]
auraRestricted = true; combat = false; Fire("PLAYER_REGEN_ENABLED"); Tick(1)
assert(appearance.activePreset ~= first and BlockedWrites() == 0)
assert(bar.liquid.rows[1].body.vertexColor[1] == appearance.colors.absorb[1])
assert(sample.ws.textColor[2] == appearance.colors.ready[2])
assert(shield.durationBar.barColor[1] == oldTimerRed)
local current = appearance.activePreset
clock = clock + 899; Tick(1)
assert(appearance.activePreset ~= current and BlockedWrites() == 0)
assert(bar.liquid.rows[1].body.vertexColor[1] == appearance.colors.absorb[1])
current = appearance.activePreset
auraRestricted = false; Tick(1)
assert(appearance.activePreset == current and BlockedWrites() == 0)
assert(shield.durationBar.barColor[1] == appearance.colors.duration[1])
Tick(1); assert(appearance.activePreset == current)
''')
case("Random waits during Edit Mode and color picking and respects manual choices", RANDOM_SETUP, r'''
Command("settings"); PriestShieldTrackerOptions.palette:Choose("Random")
local appearance = PriestShieldTrackerDB.appearance
local first = appearance.activePreset
Command("edit"); clock = clock + 900; Tick(1)
assert(appearance.activePreset == first)
Command("lock"); Tick(1)
assert(appearance.activePreset ~= first)
Command("settings")
ColorPickerFrame = CreateFrame("Frame", "ColorPickerFrame", UIParent)
function ColorPickerFrame:SetupColorPickerAndShow(info) self.info = info; self:Show() end
function ColorPickerFrame:GetColorRGB() return 0.2, 0.3, 0.4 end
PriestShieldTrackerOptions.textColor.scripts.OnClick()
first = appearance.activePreset; clock = clock + 900; Tick(1)
assert(appearance.activePreset == first)
ColorPickerFrame.info.cancelFunc(); Tick(1)
assert(appearance.activePreset ~= first and appearance.preset == "Random")
PriestShieldTrackerOptions.palette:Choose("Emerald")
clock = clock + 4000; Tick(1)
assert(appearance.preset == "Emerald" and appearance.activePreset == "Emerald")
PriestShieldTrackerOptions.palette:Choose("Random")
PriestShieldTrackerOptions.textColor.scripts.OnClick()
ColorPickerFrame.info.swatchFunc()
clock = clock + 4000; Tick(1)
assert(appearance.preset == "Custom" and appearance.colors.numbers[1] == 0.2)
ColorPickerFrame.info.cancelFunc(); ColorPickerFrame:Hide(); Tick(1)
assert(appearance.preset == "Random" and appearance.colors.numbers[1] == 1)
''')
case("Random chooses another palette on reload and preserves unrelated settings", RANDOM_SETUP + r'''
PriestShieldTrackerDB = { width = 350, appearance = { preset = "Random", activePreset = "Holy", style = "smooth" },
    groupOptions = { weakenedSoul = { enabled = false, showIcon = false } }, groups = { shield = { x = 42, y = 8 } } }
''', r'''
local appearance = PriestShieldTrackerDB.appearance
assert(appearance.preset == "Random" and appearance.activePreset ~= "Holy")
assert(appearance.style == "smooth" and bar.width == 350)
assert(not PriestShieldTrackerDB.groupOptions.weakenedSoul.enabled and not PriestShieldTrackerDB.groupOptions.weakenedSoul.showIcon)
assert(PriestShieldTrackerDB.groups.shield.x == 42 and PriestShieldTrackerDB.locked)
Command("settings"); assert(PriestShieldTrackerOptions.palette.choices[7].selected())
''')
case("Random reload in combat builds widgets with the new palette safely", RANDOM_SETUP + r'''
combat = true; absorb = secret
PriestShieldTrackerDB = { appearance = { preset = "Random", activePreset = "Holy" } }
''', r'''
assert(PriestShieldTrackerDB.appearance.activePreset ~= "Holy" and BlockedWrites() == 0)
assert(rawequal(bar.value, secret) and not sample:IsVisible())
''')


def saved_lua(value):
    if value is None:
        return "nil"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, (int, float)):
        return repr(value)
    return "{" + ",".join(f"[{saved_lua(k)}]={saved_lua(v)}" for k, v in value.items()) + "}"


reload_client = new(RANDOM_SETUP)
reload_client.execute('Command("settings"); PriestShieldTrackerOptions.palette:Choose("Random")')
for _ in range(6):
    previous_palette = reload_client.globals().PriestShieldTrackerDB.appearance.activePreset
    previous_color = tuple(reload_client.globals().PriestShieldTrackerDB.appearance.colors.absorb.values())
    saved_settings = saved_lua(reload_client.globals().PriestShieldTrackerDB)
    reload_client = new(RANDOM_SETUP + "PriestShieldTrackerDB = " + saved_settings)
    assert reload_client.globals().PriestShieldTrackerDB.appearance.activePreset != previous_palette
    assert tuple(reload_client.globals().PriestShieldTrackerDB.appearance.colors.absorb.values()) != previous_color
    reload_client.execute(r'''
local appearance = PriestShieldTrackerDB.appearance
for i = 1, 3 do
    assert(bar.liquid.rows[1].body.vertexColor[i] == appearance.colors.absorb[i])
    assert(sample.absorb.liquid.rows[1].body.vertexColor[i] == appearance.colors.absorb[i])
    assert(sample.ws.textColor[i] == appearance.colors.ready[i])
    assert(Find("AuraContainer").slots.shield.button.durationBar.barColor[i] == appearance.colors.duration[i])
end
Command("settings"); assert(PriestShieldTrackerOptions.palette.choices[7].selected())
local beforeTimer = appearance.activePreset
Tick(900); assert(appearance.activePreset ~= beforeTimer)
assert(bar.liquid.rows[1].body.vertexColor[1] == appearance.colors.absorb[1])
''')
cases_run += 1
print("PASS Random reloads restore saved settings and change actual live preview and timer colors")

for client_locale in ('enUS', 'enGB', 'deDE', 'frFR', 'esES', 'esMX', 'ptBR', 'itIT', 'ruRU', 'koKR', 'zhCN', 'zhTW', 'unsupported'):
    case(f"localized UI and saved setting keys remain functional for {client_locale}",
         f'function GetLocale() return "{client_locale}" end', r'''
Command("settings")
local panel = PriestShieldTrackerOptions
if localization.dictionaries[localization.sourceLocale] then
    assert(panel.translationNote:IsVisible())
    assert(panel.translationNote.text == localeText["Wording mistakes? Report them via a GitHub issue or CurseForge comment."])
    assert(panel.translationNote.text ~= "Wording mistakes? Report them via a GitHub issue or CurseForge comment.")
    assert(panel.translationNote.parent == panel.version.parent and panel.translationNote.points[1][5] > panel.version.points[1][5])
else
    assert(panel.translationNote == nil)
end
assert(bar.absorbLabel.text == localeText["Absorb"])
assert(sample.ws.text == localeText["Shield Ready"])
assert(panel.groupCorner.defaultText == localeText["Top right"])
panel.palette:Choose(localeText["Holy"])
panel.style:Choose(localeText["Smooth"])
assert(PriestShieldTrackerDB.appearance.preset == "Holy" and PriestShieldTrackerDB.appearance.style == "smooth")
panel.groupTime:Choose(localeText["Number (5)"])
panel.groupSoon:Choose(localeText["1 second"])
assert(PriestShieldTrackerDB.groupFrames.timeFormat == "number" and PriestShieldTrackerDB.groupFrames.soonReady == 1)
assert(panel.groupSoon.defaultText == string.format(localeText["%d second"], 1))
panel.groupTime:Choose(localeText["Seconds (5s)"])
assert(panel.raidPreview.mine.text.text == string.format(localeText["%ds"], 15))
for _, widget in ipairs(panel.widgets) do
    widget.scripts.OnEnter(widget)
    assert(GameTooltip.shown and #GameTooltip.description > 0)
    widget.scripts.OnLeave(widget)
end
panel.editButton.scripts.OnClick()
assert(PriestShieldTrackerEditSettings.subtitle.text == localeText["Shield Ready"])
ClickGroup("shield")
assert(PriestShieldTrackerEditSettings.subtitle.text == localeText["Absorb display"])
local shield = Find("AuraContainer").slots.shield.button
assert(FindText(shield, localeText["Shield expires in"]))
Command("lock"); Command("width nope")
assert(messages[#messages]:find(string.format(localeText["%s must be between %s and %s."], "width", 180, 500), 1, true))
assert(localeText["A future untranslated string"] == "A future untranslated string")
''')

case("translations cover matching keys and preserve format arguments and UTF-8", 'function GetLocale() return "frFR" end', r'''
local base = localization.dictionaries.frFR
local function Tokens(text)
    local result = {}
    for token in text:gmatch("%%[ds]") do result[#result + 1] = token end
    return table.concat(result, ",")
end
local count = 0
for locale, dictionary in pairs(localization.dictionaries) do
    count = count + 1
    local keys = 0
    for key, value in pairs(dictionary) do
        keys = keys + 1
        assert(base[key] and type(value) == "string" and #value > 0)
        assert(Tokens(key) == Tokens(value), locale .. ": " .. key)
        if value:find("??", 1, true) then error("Possible text encoding damage in translation: " .. locale .. ": " .. key) end
    end
    assert(keys == 122)
end
assert(count == 9)
assert(localization.dictionaries.zhCN["Save"] ~= "Save")
assert(localization.dictionaries.zhTW["Save"] ~= localization.dictionaries.zhCN["Save"])
assert(localeText["Top right"] ~= "Top right")
''')
EXECUTE_SETUP = r'''
Enum.SpellBookSpellBank = { Player = 0 }
known = { [90001] = true }
spellName = "Shadow Word: Death"
damageText = {
    [90001] = "A word of dark binding that inflicts 346 to 402 Shadow damage. If the target survives, take 50% damage.",
    [90002] = "Inflicts 500 to 580 Shadow damage. If the target survives, take 50% damage.",
    [90003] = "Inflicts 700 to 810 Shadow damage. If the target survives, take 50% damage.",
}
-- Deliberately unordered, including future ranks, to catch last-slot selection.
book = {
    { spellID = 90003, subName = "Rank 3", level = 48 },
    { spellID = 90001, subName = "Rank 1", level = 32 },
    { spellID = 90002, subName = "Rank 2", level = 40 },
}
C_SpellBook = {
    GetNumSpellBookSkillLines = function() return 1 end,
    GetSpellBookSkillLineInfo = function() return { itemIndexOffset = 0, numSpellBookItems = #book } end,
    GetSpellBookItemInfo = function(slot) book[slot].name = spellName; return book[slot] end,
    GetSpellBookItemLevelLearned = function(slot) return book[slot].level end,
    IsSpellKnown = function(id) return known[id] == true end,
}
cooldown = { isEnabled = true, isActive = false, startTime = secret, duration = secret }
ownCooldown = false
secretCooldownZero = nil
usable, inRange, targetExists, hostile, targetDead, playerDead = true, true, true, true, false, false
targetHealth = 345
lastCooldownID = nil
C_Spell = {
    GetSpellInfo = function(id)
        if id == 32379 or id == 401955 or damageText[id] then return { name = spellName } end
        return { name = "Other spell" }
    end,
    GetSpellDescription = function(id) return damageText[id] end,
    GetSpellTexture = function() return 1234 end,
    GetSpellCooldown = function(id) lastCooldownID = id; return cooldown end,
    GetSpellCooldownDuration = function(id, ignoreGCD)
        assert(ignoreGCD == true)
        local function ready() if secretCooldownZero ~= nil then return secretCooldownZero end; return not ownCooldown end
        return { IsZero = ready, HasExpired = ready, Copy = function() return { HasExpired = ready } end }
    end,
    IsSpellUsable = function() return usable end,
    IsSpellInRange = function() return inRange end,
}
function UnitExists() return targetExists end
function UnitCanAttack() return hostile end
function UnitIsDeadOrGhost(unit) if unit == "player" then return playerDead else return targetDead end end
function UnitHealth(unit, predicted)
    assert(unit == "target" and predicted == false)
    return targetHealth
end
function Health(value) return setmetatable({ secret = true, nativeValue = value }, getmetatable(secret)) end
function StartDeathCooldown()
    ownCooldown = true; cooldown.isActive = true; cooldown.isOnGCD = false
    Fire("UNIT_SPELLCAST_SUCCEEDED", "player", nil, 90001)
    Fire("SPELL_UPDATE_COOLDOWN")
end
PriestShieldTrackerDB = {}
'''

GLOW_SETUP = EXECUTE_SETUP + r'''
PriestShieldTrackerDB = {}
ActionButtonSpellAlertMixin = {}
slots = { [1] = 90001, [2] = 90002 }
macroSpell = 90001
C_ActionBar = { GetSpell = function(slot) return slots[slot] end }
function GetActionInfo(slot)
    if slot == 13 then return "macro", 5 end
    return "spell", slots[slot]
end
function GetMacroSpell() return macroSpell end
ActionButton1 = CreateFrame("CheckButton", "ActionButton1", UIParent)
ActionButton1.action = 1; ActionButton1:SetSize(36, 36); ActionButton1.secureAction = true
ActionButton2 = CreateFrame("CheckButton", "ActionButton2", UIParent)
ActionButton2.action = 2; ActionButton2:SetSize(36, 36); ActionButton2.secureAction = true
MultiBarBottomLeftButton1 = CreateFrame("CheckButton", "MultiBarBottomLeftButton1", UIParent)
MultiBarBottomLeftButton1.action = 13; MultiBarBottomLeftButton1:SetSize(40, 40); MultiBarBottomLeftButton1.secureAction = true
function ButtonGlow(button)
    for _, f in ipairs(frames) do
        if f.kind == "StatusBar" and f.parent and f.parent.points[1] and f.parent.points[1][2] == button then
            local gate, root = f, f.parent
            for _, child in ipairs(frames) do
                if child.kind == "Frame" and child.parent and child.parent.parent and child.parent.parent.parent == gate then
                    return child, gate, root
                end
            end
        end
    end
end
'''

EXECUTE_SETUP = GLOW_SETUP + r'''
function ExecuteGlow() return ButtonGlow(ActionButton1) end
'''

case("execute learns only the highest known rank and checks that rank's cooldown", EXECUTE_SETUP, r'''
assert(lastCooldownID == 90001 and select(2, ExecuteGlow()).minimum == 345)
Command("execute"); assert(messages[#messages]:find("Rank 1", 1, true) and messages[#messages]:find("346", 1, true))
known[90002], known[90003] = true, true
slots[1] = 90003
Fire("SPELLS_CHANGED"); Tick(0.05)
assert(lastCooldownID == 90003 and select(2, ExecuteGlow()).minimum == 699)
Command("execute"); assert(messages[#messages]:find("Rank 3", 1, true))
known = {}; Fire("SPELLS_CHANGED"); Tick(0.05)
assert(not ExecuteGlow():IsRendered())
''')

case("Forever spell-learn event updates execute rank while core startup and Random remain functional", EXECUTE_SETUP + r'''
PriestShieldTrackerDB = { appearance = { preset = "Random", activePreset = "Ember" } }
''', r'''
local registered = false
for _, frame in ipairs(frames) do
    assert(not frame.events.LEARNED_SPELL_IN_TAB)
    if frame.events.LEARNED_SPELL_IN_SKILL_LINE then registered = true end
end
assert(registered and PriestShieldTrackerOptions and Find("AuraContainer"))
known[90002] = true
Fire("LEARNED_SPELL_IN_SKILL_LINE", 90002); Tick(0.05)
assert(lastCooldownID == 90002)
local old = PriestShieldTrackerDB.appearance.activePreset
Tick(1801); assert(PriestShieldTrackerDB.appearance.activePreset ~= old)
''')

case("execute native threshold is strict below 346 and accepts opaque combat health", EXECUTE_SETUP, r'''
local label, gate = ExecuteGlow(), select(2, ExecuteGlow())
assert(label:IsRendered())
for _, hp in ipairs({ 347, 346, 345, 1 }) do
    targetHealth = Health(hp); combat = true; auraRestricted = true; Tick(0.05)
    assert(rawequal(gate.value, targetHealth))
    assert(label:IsRendered() == (hp < 346))
end
assert(BlockedWrites() == 0)
''')

case("execute stays visible as a range cue during GCD but hides during its own cooldown and unusable states", EXECUTE_SETUP, r'''
local label = ExecuteGlow()
assert(label:IsRendered())
StartDeathCooldown(); Tick(0.05); assert(not label:IsRendered())
ownCooldown = false; Tick(0.05); assert(label:IsRendered())
cooldown.isActive = false; Tick(0.05); assert(label:IsRendered())
cooldown.isActive = false; cooldown.isEnabled = false; Tick(0.05); assert(not label:IsRendered())
cooldown.isEnabled = true; usable = false; Tick(0.05); assert(not label:IsRendered())
usable = true; inRange = false; Tick(0.05); assert(not label:IsRendered())
inRange = nil; Tick(0.05); assert(not label:IsRendered())
inRange = true; Tick(0.05); assert(label:IsRendered())
cooldown.isActive = secret; Tick(0.05); assert(not label:IsRendered())
cooldown.isActive = false; usable = secret; Tick(0.05); assert(not label:IsRendered())
''')

case("execute rejects friendly missing dead and unreadable targets", EXECUTE_SETUP, r'''
local label = ExecuteGlow()
hostile = false; Tick(0.05); assert(not label:IsRendered())
hostile = true; targetExists = false; Tick(0.05); assert(not label:IsRendered())
targetExists = true; targetDead = true; Tick(0.05); assert(not label:IsRendered())
targetDead = false; playerDead = true; Tick(0.05); assert(not label:IsRendered())
playerDead = false; hostile = secret; Tick(0.05); assert(not label:IsRendered())
hostile = true; Tick(0.05); assert(label:IsRendered())
''')

case("execute damage parsing fails closed for unknown formulas percentages and decimals", EXECUTE_SETUP, r'''
local parse = executeModule.MinimumDamage
assert(parse("Inflige 1.234 a 1.450 de daño. Devuelve un 50%.") == 1234)
assert(parse("Inflige 1\226\128\175234 à 1\226\128\175450 dégâts.") == 1234)
assert(parse("Inflige |cffffffff346|r à |cffffffff402|r dégâts.") == 346)
assert(not parse(secret) and not parse(nil) and not parse(""))
assert(not parse("Deals $s1 to $s2 damage."))
assert(not parse("Deals 346 damage, with 50% backlash."))
assert(not parse("Uses 12% mana and deals 346 to 402 damage."))
assert(not parse("Deals 346.5 to 402.5 damage."))
damageText[90001] = nil; Fire("SPELL_TEXT_UPDATE"); Tick(0.05)
assert(not ExecuteGlow():IsRendered())
damageText[90001] = "Deals 400 to 450 damage."; Tick(2)
assert(select(2, ExecuteGlow()).minimum == 399 and ExecuteGlow():IsRendered())
''')



case("execute uses localized spell names and rank descriptions", EXECUTE_SETUP + r'''
function GetLocale() return "frFR" end
spellName = "Mot de l’ombre : Mort"
book[2].subName = "Rang 1"
damageText[90001] = "Inflige 346 à 402 points de dégâts d’Ombre. Renvoie 50% des dégâts."
''', r'''
assert(ExecuteGlow():IsRendered())
Command("execute"); assert(messages[#messages]:find("Rang 1", 1, true))
assert(localeText["Shadow Word: Death"] ~= "Shadow Word: Death")
''')

case("execute health cooldown mana and target events update immediately without text refresh flicker", EXECUTE_SETUP, r'''
local label, at = ExecuteGlow(), clock
targetHealth = 400; Fire("UNIT_HEALTH", "target"); assert(not label:IsRendered())
targetHealth = 345; Fire("UNIT_HEALTH", "target"); assert(label:IsRendered() and clock == at)
for i = 1, 20 do Fire("SPELL_TEXT_UPDATE"); assert(label:IsRendered() and clock == at) end
cooldown.isActive = true; Fire("SPELL_UPDATE_COOLDOWN")
assert(label:IsRendered())
cooldown.isActive = false; Fire("SPELL_UPDATE_COOLDOWN")
assert(label:IsRendered())
usable = false; Fire("UNIT_POWER_UPDATE", "player"); assert(not label:IsRendered())
usable = true; Fire("UNIT_POWER_UPDATE", "player"); assert(label:IsRendered())
targetExists = false; Fire("PLAYER_TARGET_CHANGED"); assert(not label:IsRendered())
targetExists = true; targetHealth = 400; Fire("PLAYER_TARGET_CHANGED"); assert(not label:IsRendered())
assert(clock == at)
''')

case("protected spell cooldown masks the GCD cue using native alpha without inspecting a secret", EXECUTE_SETUP, r'''
local label = ExecuteGlow()
combat = true; auraRestricted = true
cooldown.isActive = true
secretCooldownZero = setmetatable({secret = true, nativeValue = false}, getmetatable(secret))
StartDeathCooldown(); assert(not label:IsRendered())
assert(issecretvalue(select(2, ExecuteGlow()).alpha))
secretCooldownZero = setmetatable({secret = true, nativeValue = true}, getmetatable(secret))
Fire("SPELL_UPDATE_COOLDOWN"); assert(label:IsRendered())
assert(BlockedWrites() == 0)
''')

case("execute and absorb clipping stays nonzero and independent across repeated secret health thresholds", EXECUTE_SETUP, r'''
local label = ExecuteGlow()
local healthClip, healthGate = label.parent.parent, select(2, ExecuteGlow())
local absorbClip, absorbMeter = bar.parent, bar.parent.parent
assert(#healthClip.points == 1 and healthClip.width == healthGate.width and healthClip.height == healthGate.height)
assert(#absorbClip.points == 1 and absorbClip.width == absorbMeter.width and absorbClip.height == absorbMeter.height)
local ct = Find("AuraContainer")
NativeShown(ct.slots.shield.button, true); NativeShown(ct.slots.weakenedSoul.button, true)
combat = true; auraRestricted = true
for cycle = 1, 30 do
    for _, hp in ipairs({400, 346, 345, 1, 400}) do
        targetHealth = Health(hp); absorb = Health(300)
        Fire("UNIT_HEALTH", "target"); Tick(0.1)
        assert(label:IsRendered() == (hp < 346))
        assert(bar:IsRendered() and ct.slots.shield.button:IsVisible() and ct.slots.weakenedSoul.button:IsVisible())
        assert(healthClip.width > 0 and healthClip.height > 0 and absorbClip.width > 0 and absorbClip.height > 0)
        assert(healthGate.interpolation == Enum.StatusBarInterpolation.Immediate)
        assert(absorbMeter.interpolation == Enum.StatusBarInterpolation.Immediate)
    end
    targetHealth = Health(345); absorb = secretZero
    Tick(0.1); assert(label:IsRendered() and not bar:IsRendered())
    absorb = Health(200); Tick(0.1); assert(label:IsRendered() and bar:IsRendered())
end
assert(BlockedWrites() == 0)
''')

case("older cooldown APIs keep a successful SWD cast blocked until its cooldown clears", EXECUTE_SETUP, r'''
local glow = ExecuteGlow()
C_Spell.GetSpellCooldownDuration = nil
StartDeathCooldown(); assert(not glow:IsRendered())
cooldown.isActive = false; Fire("SPELL_UPDATE_COOLDOWN"); assert(glow:IsRendered())
''')

case("action glow is the default with native Retail proc art and no popup or secure button changes", GLOW_SETUP, r'''
local glow, gate, root = ButtonGlow(ActionButton1)
assert(PriestShieldTrackerDB.executeEnabled and PriestShieldTrackerDB.executeDisplay == nil)
assert(glow and glow.template == "ActionButtonSpellAlertTemplate" and glow.ProcLoop.plays > 0)
assert(glow:IsRendered() and root.parent == UIParent and not glow.nativeOwned)
assert(PriestShieldTrackerExecuteGate == nil)
assert(not ButtonGlow(ActionButton2):IsRendered())
assert(ButtonGlow(MultiBarBottomLeftButton1):IsRendered())
assert(not ActionButton1.SpellActivationAlert and ActionButton1.action == 1 and not ActionButton1.scripts.OnUpdate)
assert(actionGlowModule.Count(90001) == 2)
Command("edit")
for _, frame in ipairs(frames) do if frame.groupKey == "execute" then assert(not frame:IsShown()) end end
assert(not glow:IsRendered())
Command("lock"); assert(glow:IsRendered())
''')

case("action glow consumes protected health and cooldown and stays visible through only the GCD", GLOW_SETUP, r'''
local glow, gate = ButtonGlow(ActionButton1)
combat = true; auraRestricted = true
for _, hp in ipairs({400, 346, 345, 1, 400, 345}) do
    targetHealth = Health(hp); Fire("UNIT_HEALTH", "target")
    assert(glow:IsRendered() == (hp < 346) and rawequal(gate.value, targetHealth))
end
cooldown.isActive = true; Fire("SPELL_UPDATE_COOLDOWN"); assert(glow:IsRendered())
StartDeathCooldown(); assert(not glow:IsRendered())
ownCooldown = false; secretCooldownZero = setmetatable({secret = true, nativeValue = false}, getmetatable(secret))
Fire("SPELL_UPDATE_COOLDOWN"); assert(not glow:IsRendered() and issecretvalue(gate.alpha))
secretCooldownZero = setmetatable({secret = true, nativeValue = true}, getmetatable(secret))
Fire("SPELL_UPDATE_COOLDOWN"); assert(glow:IsRendered() and issecretvalue(gate.alpha))
usable = false; Fire("SPELL_UPDATE_USABLE"); assert(not glow:IsRendered())
usable = true; inRange = false; Tick(0.05); assert(not glow:IsRendered())
assert(BlockedWrites() == 0)
''')

case("action glow follows page changes rank upgrades macros bar visibility and fades", GLOW_SETUP, r'''
local first, _, root = ButtonGlow(ActionButton1)
local macro = ButtonGlow(MultiBarBottomLeftButton1)
combat = true
ActionButton1.action = 2; Fire("ACTIONBAR_PAGE_CHANGED"); Tick(0.05)
assert(not first:IsRendered() and macro:IsRendered())
ActionButton1.action = 1; Tick(0.05); assert(first:IsRendered())
ActionButton1.shown = false; Tick(0.05); assert(not first:IsRendered())
ActionButton1.shown = true; ActionButton1.alpha = 0; Tick(0.05); assert(not first:IsRendered())
ActionButton1.alpha = 1; Tick(0.05); assert(first:IsRendered())
known[90003] = true; Fire("LEARNED_SPELL_IN_SKILL_LINE", 90003)
assert(not first:IsRendered() and not macro:IsRendered())
slots[1] = 90003; macroSpell = 90003; Tick(0.05)
assert(first:IsRendered() and macro:IsRendered())
assert(not ActionButton1.SpellActivationAlert and BlockedWrites() == 0)
''')

case("settings checkbox controls only SWD glow with no text display controls", GLOW_SETUP, r'''
local glow = ButtonGlow(ActionButton1)
Command("settings")
local panel = PriestShieldTrackerOptions
local enabled = panel.executeEnabled
assert(panel.executeDisplay == nil and enabled:GetChecked())
enabled:SetChecked(false); enabled.scripts.OnClick(enabled)
assert(not glow:IsRendered() and not PriestShieldTrackerDB.executeEnabled)
assert(PriestShieldTrackerDB.groupOptions.shield.enabled and PriestShieldTrackerDB.groupOptions.weakenedSoul.enabled)
enabled:SetChecked(true); enabled.scripts.OnClick(enabled)
assert(glow:IsRendered() and PriestShieldTrackerDB.executeEnabled)
assert(PriestShieldTrackerExecuteGate == nil)
''')

case("glowtest previews the assigned SWD buttons for five seconds and cancels on combat", GLOW_SETUP, r'''
local glow = ButtonGlow(ActionButton1)
targetExists = false; Fire("PLAYER_TARGET_CHANGED"); assert(not glow:IsRendered())
Command("glowtest"); assert(glow:IsRendered())
Tick(4.9); assert(glow:IsRendered())
Tick(0.2); assert(not glow:IsRendered())
Command("glowtest"); assert(glow:IsRendered())
combat = true; Fire("PLAYER_REGEN_DISABLED"); Tick(0.05)
assert(not glow:IsRendered() and BlockedWrites() == 0)
''')

case("missing native glow template uses an independent pulsing border", GLOW_SETUP + 'ActionButtonSpellAlertMixin = nil', r'''
local glow = ButtonGlow(ActionButton1)
assert(glow:IsRendered() and not glow.ProcLoop and glow.scripts.OnUpdate)
targetHealth = 400; Fire("UNIT_HEALTH", "target"); assert(not glow:IsRendered())
targetHealth = 345; Fire("UNIT_HEALTH", "target"); assert(glow:IsRendered())
''')

case("late action buttons are discovered after combat and overlays resize with their buttons", GLOW_SETUP, r'''
combat = true
MultiBarRightButton1 = CreateFrame("CheckButton", "MultiBarRightButton1", UIParent)
MultiBarRightButton1.action = 1; MultiBarRightButton1.width = 50; MultiBarRightButton1.height = 50
Fire("ACTIONBAR_SLOT_CHANGED"); Tick(1); assert(not ButtonGlow(MultiBarRightButton1))
combat = false; Fire("PLAYER_REGEN_ENABLED"); Tick(0.05)
local glow, gate, root = ButtonGlow(MultiBarRightButton1)
assert(glow:IsRendered() and gate.width == 70 and root.width == 70)
MultiBarRightButton1:SetSize(60, 40); MultiBarRightButton1:SetScale(1.5)
Tick(1)
assert(gate.width == 84 and gate.height == 56 and root.scale == 1.5)
assert(BlockedWrites() == 0)
''')

CDM_SETUP = GLOW_SETUP + r'''
EssentialCooldownViewer = CreateFrame("Frame", "EssentialCooldownViewer", UIParent)
UtilityCooldownViewer = CreateFrame("Frame", "UtilityCooldownViewer", UIParent)
function CooldownIcon(parent, spell)
    local icon = CreateFrame("Frame", nil, parent)
    icon:SetSize(40, 40); icon.currentSpell = spell
    icon.GetSpellID = function(self) return self.currentSpell end
    return icon
end
essentialIcon = CooldownIcon(EssentialCooldownViewer, 90001)
utilityIcon = CooldownIcon(UtilityCooldownViewer, 90001)
otherIcon = CooldownIcon(EssentialCooldownViewer, 90002)
essentialActive = { [essentialIcon] = true, [otherIcon] = true }
utilityActive = { [utilityIcon] = true }
EssentialCooldownViewer.itemFramePool = { EnumerateActive = function() return pairs(essentialActive) end }
UtilityCooldownViewer.itemFramePool = { EnumerateActive = function() return pairs(utilityActive) end }
'''

case("cooldown manager SWD icons glow alongside action buttons and share the five second test", CDM_SETUP, r'''
local glow, gate, root = ButtonGlow(essentialIcon)
assert(glow:IsRendered() and ButtonGlow(utilityIcon):IsRendered())
assert(not ButtonGlow(otherIcon):IsRendered() and ButtonGlow(ActionButton1):IsRendered())
assert(root.parent == UIParent and gate.width == 56 and not essentialIcon.action)
assert(actionGlowModule.Count(90001) == 2 and actionGlowModule.Count(90001, "cooldown") == 2)
Command("execute"); assert(messages[#messages]:find("Matching cooldown icons: 2", 1, true))
Command("settings"); assert(PriestShieldTrackerOptions.executeEnabled:GetChecked() and PriestShieldTrackerOptions.executeDisplay == nil)
targetHealth = 400; Fire("UNIT_HEALTH", "target"); assert(not glow:IsRendered())
Command("glowtest"); assert(glow:IsRendered() and ButtonGlow(ActionButton1):IsRendered())
Tick(5.1); assert(not glow:IsRendered() and not ButtonGlow(ActionButton1):IsRendered())
''')

case("cooldown icons recheck pooled identity visibility and protected metadata without modifying the icon", CDM_SETUP, r'''
local glow = ButtonGlow(essentialIcon)
combat = true; auraRestricted = true
targetHealth = Health(345); Fire("UNIT_HEALTH", "target"); assert(glow:IsRendered())
essentialIcon.currentSpell = 90002; Tick(0.05); assert(not glow:IsRendered())
essentialIcon.currentSpell = secret; Tick(0.05); assert(not glow:IsRendered() and ButtonGlow(ActionButton1):IsRendered())
essentialIcon.currentSpell = 90001; Tick(0.05); assert(glow:IsRendered())
essentialIcon.forbidden = true; Tick(0.05); assert(not glow:IsRendered())
essentialIcon.forbidden = false; Tick(0.05); assert(glow:IsRendered())
NativeShown(EssentialCooldownViewer, false); Tick(0.05); assert(not glow:IsRendered())
NativeShown(EssentialCooldownViewer, true); Tick(0.05); assert(glow:IsRendered())
essentialIcon.alpha = 0; Tick(0.05); assert(not glow:IsRendered())
essentialIcon.alpha = 1; Tick(0.05); assert(glow:IsRendered())
StartDeathCooldown(); assert(not glow:IsRendered())
assert(BlockedWrites() == 0 and essentialIcon.currentSpell == 90001 and not essentialIcon.SpellActivationAlert)
''')

case("cooldown glow follows native pooled icons reparented by a layout addon without duplicate overlays", CDM_SETUP, r'''
local customBar = CreateFrame("Frame", "CustomCooldownBar", UIParent)
essentialIcon:SetParent(customBar); essentialIcon:SetSize(50, 30); essentialIcon:SetScale(1.25)
EssentialCooldownViewer.GetItemFrames = function() return {} end
Tick(1)
local glow, gate, root = ButtonGlow(essentialIcon)
assert(glow:IsRendered() and root.parent == UIParent and gate.width == 70 and gate.height == 42 and root.scale == 1.25)
local count = #frames
for i = 1, 10 do Tick(1) end
assert(#frames == count and actionGlowModule.Count(90001, "cooldown") == 2)
essentialActive[essentialIcon] = nil; essentialIcon:Hide(); Tick(0.05); assert(not glow:IsRendered())
essentialActive[essentialIcon] = true; essentialIcon:Show(); Tick(1); assert(glow:IsRendered() and #frames == count)
''')

case("cooldown discovery supports item-list and public cooldown-info fallbacks with exact overrides", CDM_SETUP + r'''
EssentialCooldownViewer.itemFramePool = nil
EssentialCooldownViewer.GetItemFrames = function() return { essentialIcon, otherIcon } end
essentialIcon.GetSpellID = nil
essentialIcon.cooldownInfo = { spellID = 80001, overrideSpellID = 90001 }
essentialIcon.GetCooldownInfo = function(self) return self.cooldownInfo end
utilityIcon.GetSpellID = nil; utilityIcon.cooldownID = 77
C_CooldownViewer = { GetCooldownViewerCooldownInfo = function() return { spellID = 90001 } end }
''', r'''
assert(ButtonGlow(essentialIcon):IsRendered() and ButtonGlow(utilityIcon):IsRendered())
essentialIcon.cooldownInfo.overrideSpellID = secret; Tick(0.05); assert(not ButtonGlow(essentialIcon):IsRendered())
essentialIcon.cooldownInfo.overrideSpellID = nil; essentialIcon.cooldownInfo.spellID = 80001
C_SpellBook.FindSpellOverrideByID = function(id) if id == 80001 then return 90001 else return id end end
Tick(0.05); assert(ButtonGlow(essentialIcon):IsRendered())
C_SpellBook.FindSpellOverrideByID = function() return secret end
Tick(0.05); assert(not ButtonGlow(essentialIcon):IsRendered() and ButtonGlow(utilityIcon):IsRendered())
''')

case("saved SWD disable controls both glow locations and cannot change through stale combat clicks", CDM_SETUP + r'''
PriestShieldTrackerDB = {executeDisplay = "action", groupOptions = {execute = {enabled = false}}}
''', r'''
local action, cooldown = ButtonGlow(ActionButton1), ButtonGlow(essentialIcon)
assert(not action:IsRendered() and not cooldown:IsRendered())
assert(PriestShieldTrackerDB.executeEnabled == false and PriestShieldTrackerDB.executeDisplay == nil)
assert(PriestShieldTrackerDB.groupOptions.execute == nil and PriestShieldTrackerDB.groups.execute == nil)
Command("settings")
local panel = PriestShieldTrackerOptions
assert(not panel.executeEnabled:GetChecked() and panel.executeDisplay == nil)
assert(panel.executeNote.text == "Ignores resistances, absorbs, and damage reduction.")
panel.executeEnabled:SetChecked(true); panel.executeEnabled.scripts.OnClick(panel.executeEnabled)
assert(action:IsRendered() and cooldown:IsRendered())
combat = true; Fire("PLAYER_REGEN_DISABLED")
assert(not panel.executeEnabled.enabled and panel.executeDisplay == nil)
panel.executeEnabled:SetChecked(false); panel.executeEnabled.scripts.OnClick(panel.executeEnabled)
assert(PriestShieldTrackerDB.executeEnabled and action:IsRendered() and cooldown:IsRendered())
combat = false; Fire("PLAYER_REGEN_ENABLED")
assert(panel.executeEnabled:GetChecked())
panel.executeEnabled:SetChecked(false); panel.executeEnabled.scripts.OnClick(panel.executeEnabled)
assert(not action:IsRendered() and not cooldown:IsRendered())
assert(PriestShieldTrackerDB.groupOptions.shield.enabled and PriestShieldTrackerDB.groupOptions.weakenedSoul.enabled)
''')

case("former text mode migrates to enabled icon glow without popup frames controls or Edit Mode group", GLOW_SETUP + r'''
PriestShieldTrackerDB = {executeDisplay = "text", groupOptions = {execute = {enabled = true, fontSize = 24}}, groups = {execute = {x = 45, y = -12}}}
''', r'''
assert(ButtonGlow(ActionButton1):IsRendered() and PriestShieldTrackerDB.executeEnabled)
assert(PriestShieldTrackerDB.executeDisplay == nil and PriestShieldTrackerDB.groupOptions.execute == nil and PriestShieldTrackerDB.groups.execute == nil)
assert(PriestShieldTrackerExecuteGate == nil)
Command("edit")
local count = 0
for _, frame in ipairs(frames) do
    if frame.groupKey then assert(frame.groupKey ~= "execute"); count = count + 1 end
    assert(frame.text ~= "Execute available" and frame.text ~= "Execute range")
end
assert(count == 2)
Command("settings")
local panel = PriestShieldTrackerOptions
assert(panel.executeDisplay == nil and panel.executeEnabled:GetChecked())
assert(panel.executeNote.text == "Ignores resistances, absorbs, and damage reduction.")
''')

case("execute update errors clear both glows without retaining removed popup UI", CDM_SETUP, r'''
local action, cooldown = ButtonGlow(ActionButton1), ButtonGlow(essentialIcon)
assert(action:IsRendered() and cooldown:IsRendered())
local readHealth = UnitHealth
UnitHealth = function() error("Health temporarily unavailable") end
Fire("UNIT_HEALTH", "target")
assert(not action:IsRendered() and not cooldown:IsRendered() and PriestShieldTrackerExecuteGate == nil)
UnitHealth = readHealth; Fire("UNIT_HEALTH", "target")
assert(action:IsRendered() and cooldown:IsRendered())
''')

case("GCD event keeps both glows stable when ignoreGCD returns nil and post-GCD flags wobble", CDM_SETUP, r'''
local action, icon = ButtonGlow(ActionButton1), ButtonGlow(essentialIcon)
C_Spell.GetSpellCooldownDuration = function() return nil end
assert(action:IsRendered() and icon:IsRendered())
cooldown.isActive = true; cooldown.isOnGCD = true
Fire("SPELL_UPDATE_COOLDOWN")
assert(action:IsRendered() and icon:IsRendered())
for i = 1, 30 do
    -- This field is unreliable between cooldown events. It must not hide a
    -- glow whose event-time classification was only a global cooldown.
    cooldown.isOnGCD = false
    Tick(0.05)
    assert(action:IsRendered() and icon:IsRendered())
end
cooldown.isActive = false; cooldown.isOnGCD = false; Fire("SPELL_UPDATE_COOLDOWN")
cooldown.isActive = true
for i = 1, 5 do Tick(0.05); assert(action:IsRendered() and icon:IsRendered()) end
-- Unrelated cooldown misclassification must not arm a new SWD mask.
cooldown.isOnGCD = false; Fire("SPELL_UPDATE_COOLDOWN")
assert(action:IsRendered() and icon:IsRendered())
StartDeathCooldown()
assert(not action:IsRendered() and not icon:IsRendered())
cooldown.isActive = false; Fire("SPELL_UPDATE_COOLDOWN")
assert(action:IsRendered() and icon:IsRendered())
''')

case("actual SWD cooldown remains hidden beneath GCD and returns as soon as its cached duration expires", CDM_SETUP, r'''
local action, icon = ButtonGlow(ActionButton1), ButtonGlow(essentialIcon)
local expired = false
local realDuration = { HasExpired = function() return expired end, IsZero = function() return false end }
realDuration.Copy = function() return { HasExpired = function() return expired end } end
C_Spell.GetSpellCooldownDuration = function() return realDuration end
StartDeathCooldown(); assert(not action:IsRendered() and not icon:IsRendered())
cooldown.isOnGCD = true
C_Spell.GetSpellCooldownDuration = function() return nil end
Fire("SPELL_UPDATE_COOLDOWN")
for i = 1, 10 do Tick(0.05); assert(not action:IsRendered() and not icon:IsRendered()) end
expired = setmetatable({secret = true, nativeValue = false}, getmetatable(secret))
Tick(0.05); assert(not action:IsRendered() and not icon:IsRendered())
expired = setmetatable({secret = true, nativeValue = true}, getmetatable(secret))
Tick(0.05); assert(action:IsRendered() and icon:IsRendered())
assert(issecretvalue(select(2, ButtonGlow(ActionButton1)).alpha))
assert(BlockedWrites() == 0)
''')

case("GCD readiness cache cannot make a newly learned SWD rank appear off cooldown", GLOW_SETUP, r'''
cooldown.isActive = true; cooldown.isOnGCD = true; Fire("SPELL_UPDATE_COOLDOWN")
assert(ButtonGlow(ActionButton1):IsRendered())
known[90003] = true; slots[1] = 90003; ownCooldown = true
Fire("SPELLS_CHANGED")
assert(not ButtonGlow(ActionButton1):IsRendered())
cooldown.isOnGCD = false; Fire("SPELL_UPDATE_COOLDOWN")
assert(not ButtonGlow(ActionButton1):IsRendered())
cooldown.isActive = false; Fire("SPELL_UPDATE_COOLDOWN")
assert(ButtonGlow(ActionButton1):IsRendered())
''')

case("glow diagnostics retain the public reason after a GCD usability failure clears", CDM_SETUP, r'''
cooldown.isActive = true; cooldown.isOnGCD = true; Fire("SPELL_UPDATE_COOLDOWN")
usable = false; Fire("SPELL_UPDATE_USABLE")
assert(not ButtonGlow(ActionButton1):IsRendered())
usable = true; Fire("SPELL_UPDATE_USABLE")
assert(ButtonGlow(ActionButton1):IsRendered())
for i = 1, 40 do Tick(0.05) end
local output = table.concat(actionGlowModule.DebugLines(), "\n")
assert(output:find("usable=false", 1, true) and output:find("GCD=true", 1, true))
assert(output:find("matched; cooldownAlpha=1", 1, true))
Command("glowdebug"); assert(messages[#messages]:find("loop=", 1, true))
''')

case("glow diagnostics distinguish protected icon identity and alpha without logging protected values", CDM_SETUP, r'''
essentialIcon.currentSpell = secret; Tick(0.05)
local output = table.concat(actionGlowModule.DebugLines(), "\n")
assert(output:find("spell identity protected", 1, true))
essentialIcon.currentSpell = 90001
ActionButton1.alpha = setmetatable({secret = true, rendered = true}, getmetatable(secret))
targetHealth = Health(345); Tick(0.05)
output = table.concat(actionGlowModule.DebugLines(), "\n")
assert(output:find("iconAlpha=protected", 1, true))
assert(not output:find("nativeValue", 1, true) and PriestShieldTrackerDB.glowDebug == nil)
for i = 1, 40 do usable = i % 2 == 0; Fire("SPELL_UPDATE_USABLE") end
assert(#actionGlowModule.DebugLines() <= 17)
''')

case("a reused live cooldown timer cannot rearm an expired SWD snapshot during later GCDs", CDM_SETUP, r'''
local action, icon = ButtonGlow(ActionButton1), ButtonGlow(essentialIcon)
local function nativeBool(value) return setmetatable({secret = true, nativeValue = value}, getmetatable(secret)) end
local live = { finish = clock + 12, copies = 0 }
function live:HasExpired() return nativeBool(clock >= self.finish) end
function live:IsZero() return nativeBool(false) end
function live:Copy()
    self.copies = self.copies + 1
    local capturedEnd = self.finish
    return {HasExpired = function() return nativeBool(clock >= capturedEnd) end}
end
C_Spell.GetSpellCooldownDuration = function() return live end
StartDeathCooldown()
assert(live.copies == 1 and not action:IsRendered() and not icon:IsRendered())
Tick(12.1)
assert(action:IsRendered() and icon:IsRendered())
local plays = action.ProcLoop.plays
for cycle = 1, 3 do
    -- Reconfigure the shared API object to the new GCD, then report another
    -- active/false-GCD update exactly like the trace's erroneous cache switch.
    live.finish = clock + 1.5
    cooldown.isOnGCD = true; Fire("SPELL_UPDATE_COOLDOWN")
    cooldown.isOnGCD = false; Fire("SPELL_UPDATE_COOLDOWN")
    for tick = 1, 30 do
        Tick(0.05)
        assert(action:IsRendered() and icon:IsRendered())
    end
end
assert(live.copies == 1 and action.ProcLoop.plays == plays)
live.finish = clock + 12; StartDeathCooldown()
assert(live.copies == 2 and not action:IsRendered() and not icon:IsRendered())
assert(BlockedWrites() == 0)
''')

case("unrelated cast and contradictory GCD updates never arm a real SWD mask once ready", CDM_SETUP, r'''
local action, icon = ButtonGlow(ActionButton1), ButtonGlow(essentialIcon)
local reads = 0
C_Spell.GetSpellCooldownDuration = function()
    reads = reads + 1
    return {IsZero = function() return false end, HasExpired = function() return false end,
        Copy = function() error("A GCD must not become a SWD snapshot") end}
end
cooldown.isActive = true; cooldown.isOnGCD = true; Fire("SPELL_UPDATE_COOLDOWN")
Fire("UNIT_SPELLCAST_SUCCEEDED", "player", secret, 12345)
Fire("UNIT_SPELLCAST_SUCCEEDED", "target", secret, 90001)
cooldown.isOnGCD = false; Fire("SPELL_UPDATE_COOLDOWN")
for i = 1, 30 do Tick(0.05); assert(action:IsRendered() and icon:IsRendered()) end
assert(reads == 0)
''')

case("reload with an existing SWD cooldown bootstraps a snapshot without exposing cast data", CDM_SETUP + r'''
cooldown.isActive = true; cooldown.isOnGCD = false; ownCooldown = true
''', r'''
local action, icon = ButtonGlow(ActionButton1), ButtonGlow(essentialIcon)
assert(not action:IsRendered() and not icon:IsRendered())
Fire("SPELL_UPDATE_COOLDOWN")
assert(not action:IsRendered() and not icon:IsRendered())
ownCooldown = false; cooldown.isOnGCD = true; Fire("SPELL_UPDATE_COOLDOWN")
assert(action:IsRendered() and icon:IsRendered())
Fire("UNIT_SPELLCAST_SUCCEEDED", "player", secret, secret)
assert(action:IsRendered() and icon:IsRendered() and BlockedWrites() == 0)
''')

print(f"{cases_run} logic checks passed; live client validation remains required.")
