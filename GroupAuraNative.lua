-- Adapted from Weakened Soul Tracker 2.6.0 by nocktambule (MIT).
-- License: licenses/WeakenedSoulTracker.txt.
-- PriestShieldTracker adds context checks and deferred configuration retries.
-- Weakened Soul Tracker: game-drawn display (Blizzard AuraContainer, 12.1+)
--
-- The addon never reads aura data (hidden from addons in combat). It hands
-- the game a filter and lets its own secure code find the debuff and draw the
-- icon and the real timer. Renewed Hope, Divine Grace and other priests'
-- shields are therefore reflected exactly, in combat too.
--
-- Blizzard rule (Blizzard_AuraContainerUtil.lua, CanApplyIdentityCandidateFilters):
-- matching a HARMFUL aura by spell ID on a friendly unit is only allowed when
-- the spell is flagged "never secret". Otherwise such auras are rejected.
-- So we pick a strategy at load time:
--   "all"   : Weakened Soul is never-secret -> exact spell-ID filter.
--   "props" : otherwise, Weakened Soul is recognised by its properties, which
--             Blizzard still lets addons filter on friendly units: a debuff
--             cast by a player, not dispellable, lasting 15 s at most. In a
--             group nothing else matches in practice. (Same approach as
--             ForeverAuras recommends for friendly debuffs.)
-- Both strategies show every priest's shields: a "mine" slot (red) drawn on
-- top of an "others" slot (purple) at the same spot.

local _, ns = ...

local Native = {
    available = false,  -- the AuraContainer API exists on this client
    strategy  = nil,    -- "all" or "mine"
    built     = 0,
    failed    = 0,
    lastError = nil,
    secrecy   = nil,    -- raw secrecy level of Weakened Soul (for /wst status)
}
ns.Native = Native

local handles = {}      -- [parent frame] = handle
local pending = false   -- layout/unit changes waiting for the end of combat
local spellID, db

-- Border colors come from the settings (db.borderMine / db.borderOthers,
-- db.showBorder): red for your shield, purple for another priest's by default.

local function Err(e)
    Native.failed = Native.failed + 1
    Native.lastError = tostring(e)
end

function Native.Init(database, wsSpellID)
    db, spellID = database, wsSpellID
    Native.available = (C_AuraContainerUtil ~= nil) and (CustomAuraContainerSlotDefaultOptions ~= nil)
    if not Native.available then return false end

    local neverSecret = false
    if C_Secrets and C_Secrets.GetSpellAuraSecrecy and Enum and Enum.SecrecyLevel then
        local ok, level = pcall(C_Secrets.GetSpellAuraSecrecy, spellID)
        if ok then
            Native.secrecy = level
            neverSecret = (level == Enum.SecrecyLevel.NeverSecret)
        end
    end
    Native.strategy = neverSecret and "all" or "props"
    return true
end

---------------------------------------------------------------------------
-- Slots
---------------------------------------------------------------------------
local MAX_WS_DURATION = 15.5  -- Weakened Soul lasts 15 s (less with talents)
local DISPELLABLE = { Magic = true, Curse = true, Disease = true, Poison = true }

-- Which shields are shown (db.showOthers), for the "props" strategy:
--   yours  : "HARMFUL|PLAYER" = debuffs YOU applied. A mob can never match,
--            so this is exact. Always on.
--   others : off by default. Other priests' Weakened Soul is matched by its
--            properties (cast by a player, not dispellable, 15 s max). Mobs
--            casting player spells (Rend, Hamstring...) carry the same
--            properties and may show up too; /wst scan helps find a better
--            criterion. ("canApplyAura" was tried: Weakened Soul fails it.)
local function PropsFilters(mine)
    local f = {
        excludeDispelTypes = DISPELLABLE, -- Weakened Soul can't be dispelled
        maxDuration = MAX_WS_DURATION,    -- also drops permanent auras
        isBossOrRoleAura = false,         -- never a boss mechanic
    }
    if not mine then f.isFromPlayerOrPlayerPet = true end
    return f
end

local function SlotFilters(key)
    local filterString = key == "mine" and "HARMFUL|PLAYER" or "HARMFUL"
    if Native.strategy == "all" then
        return filterString, { includeSpellIDs = { [spellID] = true } }
    end
    return filterString, PropsFilters(key == "mine")
end

local function ShowsOthers()
    return Native.strategy == "all" or (db and db.showOthers)
end
Native.ShowsOthers = ShowsOthers

-- Same test in plain Lua, used by /wst scan (out of combat, readable data
-- only): returns "mine", "others" or nil.
function Native.WouldMatch(aura, isMine)
    if Native.strategy == "all" then
        if aura.spellId ~= spellID then return nil end
        return isMine and "mine" or "others"
    end
    if aura.dispelName and DISPELLABLE[aura.dispelName] then return nil end
    if not aura.duration or aura.duration == 0 or aura.duration > MAX_WS_DURATION then return nil end
    if aura.isBossAura then return nil end
    if isMine then return "mine" end
    if ShowsOthers() and aura.isFromPlayerOrPlayerPet == true then return "others" end
    return nil
end

-- Position and size of one slot button (out of combat only)
local function PlaceButton(h, button)
    local c = ns.CORNERS[h.corner()] or ns.CORNERS.tr
    local size = h.size()
    button:ClearAllPoints()
    button:SetPoint(c[1], h.container, c[1], c[2], c[3])
    button:SetSize(size, size)
end

-- "Soon ready" signal: the remaining-time text is written by the game and
-- colored through a curve the game evaluates on the remaining duration:
-- white, then green during the last db.soonReady seconds (0 = off). Works in
-- combat, the addon never sees the time.
local SOON_COLOR, NORMAL_COLOR = { 0.25, 1, 0.25, 1 }, { 1, 1, 1, 1 }

-- Remaining-time format (db.timeFormat), applied by the game's own text:
--   "seconds": the game's default ("5s")
--   "number" : the number only ("5"), rounded up
--   "icon"   : no text, only the clock swipe on the icon
local formatters = {}
local function RuleFormatter(format)
    if formatters[format] == nil then
        local ok, f = pcall(function()
            local fmt = C_StringUtil.CreateNumericRuleFormatter()
            fmt:AddBreakpoint({ threshold = 0, step = 1, rounding = Enum.NumericRuleFormatRounding.Up, format = format })
            return fmt
        end)
        formatters[format] = ok and f or false
    end
    return formatters[format] or nil
end

local function DurationTextOptions()
    local opts = {}
    local format = db and db.timeFormat or "seconds"
    if format == "number" then
        opts.textFormatter = RuleFormatter("%d")
    elseif format == "icon" then
        opts.textFormatter = RuleFormatter("")
        return opts -- no text, so no "soon ready" color either
    end
    local seconds = db and db.soonReady or 0
    if seconds > 0 and C_CurveUtil and C_CurveUtil.CreateColorCurve and Enum.DurationTextBindingProperty then
        local curve = C_CurveUtil.CreateColorCurve()
        curve:SetType(Enum.LuaCurveType.Step)
        curve:AddPoint(0, CreateColor(unpack(SOON_COLOR)))
        curve:AddPoint(seconds, CreateColor(unpack(NORMAL_COLOR)))
        curve:AddPoint(3600, CreateColor(unpack(NORMAL_COLOR)))
        opts.textColor = { curve = curve, property = Enum.DurationTextBindingProperty.RemainingDuration }
    end
    return opts
end

local function BorderColor(key)
    local c = key == "mine" and db.borderMine or db.borderOthers
    return c.r, c.g, c.b, c.a
end

-- Ordinary sample frames use the same placement, colors and icon styling as
-- live indicators. They never attach to units or read any real aura data.
function Native.CreatePreview(parent, key)
    local h = { container = parent, key = key,
        corner = function() return db.corner end, size = function() return db.size end }
    local button = CreateFrame("Frame", nil, parent)
    button:SetFrameLevel(parent:GetFrameLevel() + 12)
    button:EnableMouse(false)
    h.button = button
    h.border = button:CreateTexture(nil, "BACKGROUND")
    h.border:SetPoint("TOPLEFT", -1, 1); h.border:SetPoint("BOTTOMRIGHT", 1, -1)
    local icon = button:CreateTexture(nil, "ARTWORK")
    icon:SetAllPoints(); icon:SetTexCoord(0.08, 0.92, 0.08, 0.92)
    icon:SetTexture(C_Spell and C_Spell.GetSpellTexture and C_Spell.GetSpellTexture(spellID)
        or "Interface\\Icons\\Spell_Holy_AshesToAshes")
    h.cooldown = CreateFrame("Cooldown", nil, button, "CooldownFrameTemplate")
    h.cooldown:SetAllPoints(); h.cooldown:SetDrawEdge(false); h.cooldown:SetHideCountdownNumbers(true)
    h.cooldown:EnableMouse(false)
    local textLayer = CreateFrame("Frame", nil, button)
    textLayer:SetAllPoints(); textLayer:SetFrameLevel(h.cooldown:GetFrameLevel() + 1)
    h.text = textLayer:CreateFontString(nil, "OVERLAY")
    h.text:SetPoint("CENTER"); h.text:SetShadowOffset(1, -1)
    return h
end

function Native.UpdatePreview(h, remaining)
    PlaceButton(h, h.button)
    h.button:SetShown(db.enabled and (h.key == "mine" or ShowsOthers()))
    h.border:SetColorTexture(BorderColor(h.key)); h.border:SetShown(db.showBorder)
    h.cooldown:SetCooldown(GetTime() - (15 - remaining), 15)
    h.text:SetFont(STANDARD_TEXT_FONT or "Fonts\\FRIZQT__.TTF", db.size >= 20 and 12 or 10, "OUTLINE")
    local format = db.timeFormat
    h.text:SetText(format == "icon" and "" or tostring(math.ceil(remaining)) .. (format == "seconds" and "s" or ""))
    local color = db.soonReady > 0 and remaining < db.soonReady and SOON_COLOR or NORMAL_COLOR
    h.text:SetTextColor(unpack(color))
end

local function MakeInitializer(h, key, withText)
    return function(button)
        -- the icon must never block clicks on the unit frame (targeting,
        -- click-casting)
        if button.EnableMouse then button:EnableMouse(false) end
        PlaceButton(h, button)
        -- your shield is drawn above another priest's at the same spot
        button:SetFrameLevel(h.container:GetFrameLevel() + (key == "mine" and 2 or 1))

        local border = button:CreateTexture(nil, "BACKGROUND")
        border:SetPoint("TOPLEFT", -1, 1)
        border:SetPoint("BOTTOMRIGHT", 1, -1)
        border:SetColorTexture(BorderColor(key))
        border:SetShown(db.showBorder)
        h.borders[key] = border

        local icon = button:CreateTexture(nil, "ARTWORK")
        icon:SetAllPoints()
        icon:SetTexCoord(0.08, 0.92, 0.08, 0.92)
        button:SetIcon(icon)

        local cd = CreateFrame("Cooldown", nil, button, "CooldownFrameTemplate")
        cd:SetAllPoints()
        cd:SetDrawEdge(false)
        cd:SetHideCountdownNumbers(true) -- the remaining time is a duration text (see below)
        button:SetDurationCooldown(cd)

        -- Investigation labels (/wst labels): the game itself writes the
        -- aura's spell name and its caster (class-colored), even in combat.
        -- Yours go under the icon, another priest's above it, so the two
        -- never overlap.
        if ns.DEBUG and db and db.labels and not withText then
            pcall(function()
                local spell = button:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmallOutline")
                local caster = button:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmallOutline")
                if key == "mine" then
                    spell:SetPoint("TOP", button, "BOTTOM", 0, -1)
                    caster:SetPoint("TOP", spell, "BOTTOM", 0, -1)
                else
                    caster:SetPoint("BOTTOM", button, "TOP", 0, 1)
                    spell:SetPoint("BOTTOM", caster, "TOP", 0, 1)
                end
                button:SetSpellName(spell)
                button:SetCasterName(caster, { useClassColors = true })
            end)
        end

        -- Remaining time, written by the game: next to the icon in the window
        -- rows, on the icon on group frames
        local fs
        if withText then
            fs = button:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
            fs:SetPoint("RIGHT", button, "LEFT", -4, 0)
        else
            fs = button:CreateFontString(nil, "OVERLAY",
                h.size() >= 20 and "GameFontHighlightOutline" or "GameFontHighlightSmallOutline")
            fs:SetPoint("CENTER", button, "CENTER", 0, 0)
        end
        local okText = pcall(button.SetDurationText, button, fs, DurationTextOptions())
        if not okText then button:SetDurationText(fs) end -- no color curve on this client
        h.texts[key] = fs
    end
end

local function AddSlot(h, key)
    local filterString, filters = SlotFilters(key)
    local button = h.container:AddAuraSlot(key, filterString, {
        candidateFilters = filters,
        initializeFrame  = MakeInitializer(h, key, h.withText),
    })
    h.buttons[key] = button
end

---------------------------------------------------------------------------
-- Handles: one container per display spot (Blizzard frame or window row)
---------------------------------------------------------------------------
-- opts = { corner = fn, size = fn, withText = bool, frameLevel = n }
function Native.Attach(parent, opts)
    if not Native.available or not ns.CanAccessRegion(parent) then pending = true; return nil end
    local h = handles[parent]
    if h then return h end
    if InCombatLockdown() then pending = true; return nil end
    if h == false then return nil end -- a previous attempt failed

    h = { parent = parent, buttons = {}, texts = {}, borders = {}, corner = opts.corner, size = opts.size, withText = opts.withText }
    local ok, e = pcall(function()
        local wrapper = CreateFrame("Frame", nil, parent)
        wrapper:SetAllPoints(parent)
        h.visibility = wrapper
        local ct = CreateFrame("AuraContainer", nil, wrapper, "CustomAuraContainerTemplate")
        h.container = ct
        ct:SetAllPoints(parent)
        ct:SetFrameLevel(parent:GetFrameLevel() + (opts.frameLevel or 12))
        -- both slots always exist; the "others" one is switched on and off
        -- live with the option (SetAuraSlotEnabled), no /reload needed
        AddSlot(h, "others")
        AddSlot(h, "mine")
        ct:SetAuraSlotEnabled("others", ShowsOthers())
        h.othersOn = ShowsOthers()
        ct:SetEnabled(true)
    end)
    if not ok then
        Err(e)
        handles[parent] = false
        return nil
    end
    Native.built = Native.built + 1
    handles[parent] = h
    return h
end

function Native.SetUnit(h, unit)
    if not h then return end
    if unit == h.unit and h.unitSet then return end
    if not ns.CanAccessRegion(h.container) then pending = true; return end
    local ok, e = pcall(function()
        if unit then
            h.container:SetUnit(unit)
            h.container:SetEnabled(true)
        else
            h.container:SetEnabled(false)
        end
    end)
    if ok then
        h.unit = unit
        h.unitSet = true
    else
        Err(e)
        pending = true -- retry when combat ends
    end
end

function Native.SetShown(h, shown)
    if not h then return end
    if InCombatLockdown() or not ns.CanAccessRegion(h.visibility) then pending = true; return end
    if pcall(h.visibility.SetShown, h.visibility, shown) then h.shown = shown
    else pending = true end
end

-- Re-apply corner and size to every button (blocked while auras are secret)
function Native.RelayoutAll()
    if InCombatLockdown() then pending = true; return end
    for _, h in pairs(handles) do
        if h then
            for _, b in pairs(h.buttons) do
                if ns.CanAccessRegion(b) then
                    local ok, e = pcall(PlaceButton, h, b)
                    if not ok then Err(e); pending = true end
                else pending = true end
            end
        end
    end
end

-- Re-apply format and "soon ready" color to every remaining-time text (out
-- of combat: Blizzard locks the buttons while auras are secret)
function Native.ApplyTextOptions()
    if InCombatLockdown() then pending = true; return end
    local opts = DurationTextOptions()
    for _, h in pairs(handles) do
        if h then
            for key, b in pairs(h.buttons) do
                local fs = h.texts[key]
                if fs and ns.CanAccessRegion(b) and ns.CanAccessRegion(fs) then
                    local ok, e = pcall(b.SetDurationText, b, fs, opts)
                    if not ok then Err(e); pending = true end
                elseif fs then pending = true end
            end
        end
    end
end

-- Re-apply border colors and visibility (our own textures, but on buttons
-- Blizzard locks while auras are secret: out of combat only)
function Native.ApplyBorders()
    if InCombatLockdown() then pending = true; return end
    for _, h in pairs(handles) do
        if h then
            for key, tex in pairs(h.borders) do
                if ns.CanAccessRegion(tex) then
                    local ok, e = pcall(function()
                        tex:SetColorTexture(BorderColor(key))
                        tex:SetShown(db.showBorder)
                    end)
                    if not ok then Err(e); pending = true end
                else pending = true end
            end
        end
    end
end

-- Switch the "others" slot of every container to match the option
function Native.ApplyOthers()
    local want = ShowsOthers()
    for _, h in pairs(handles) do
        if h and h.othersOn ~= want and ns.CanAccessRegion(h.container) then
            local ok, e = pcall(h.container.SetAuraSlotEnabled, h.container, "others", want)
            if ok then h.othersOn = want else Err(e); pending = true end
        elseif h and h.othersOn ~= want then pending = true end
    end
end

-- Diagnostic for /wst scan (test builds): containers following this unit
function Native.Diag(unit)
    local total, shown, others = 0, 0, 0
    for _, h in pairs(handles) do
        if h and h.unit == unit then
            total = total + 1
            local vis = h.container:IsVisible()
            if vis then shown = shown + 1 end
            if vis and h.othersOn then others = others + 1 end
        end
    end
    return total, shown, others
end

-- Called when combat ends: retry everything that was refused
function Native.Flush(getUnit)
    if not pending or InCombatLockdown() then return end
    pending = false
    Native.RelayoutAll()
    Native.ApplyOthers()
    Native.ApplyTextOptions()
    Native.ApplyBorders()
    for parent, h in pairs(handles) do
        if h then
            local u = getUnit(parent)
            Native.SetUnit(h, u)
            if h.shown ~= nil then Native.SetShown(h, h.shown) end
        end
    end
end

function Native.Status()
    local L = ns.L
    local lines = {}
    if not Native.available then
        lines[1] = L["|cffff6060The game-drawn aura display is not available on this client: nothing can be shown.|r"]
        return lines
    end
    local name = C_Spell and C_Spell.GetSpellName and C_Spell.GetSpellName(spellID)
    lines[#lines + 1] = string.format(L["Tracked spell: %s (ID %d)."], name or L["|cffff6060unknown|r"], spellID or 0)
    if Native.strategy == "all" then
        lines[#lines + 1] = L["Weakened Soul is never-secret: every priest's shields are shown (yours red, others purple)."]
    elseif db.showOthers then
        lines[#lines + 1] = L["Your shields (red) are exact. Other priests' shields (purple) are matched by their properties: some monster debuffs may show too."]
    else
        lines[#lines + 1] = L["Only your shields are shown (exact). Other priests' shields are off (option in /wst)."]
    end
    lines[#lines + 1] = string.format(L["Secrecy level %s, containers %d built / %d failed."],
        tostring(Native.secrecy), Native.built, Native.failed)
    if Native.lastError then
        lines[#lines + 1] = string.format(L["Last error: %s"], Native.lastError)
    end
    return lines
end

function Native.HasPending() return pending end
