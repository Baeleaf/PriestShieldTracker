-- Own overlays only: never change a secure button, its attributes, or Blizzard's
-- proc-alert manager. Protected health goes straight to a native fill/clip.
local addonName, ns = ...
local G = {}
ns.ActionGlow = G
local entries, seen = {}, {}
local discoverElapsed, testUntil, testID, testMinimum = 0, nil, nil, nil
local WHITE = "Interface\\Buttons\\WHITE8x8"
local IMMEDIATE = Enum.StatusBarInterpolation and Enum.StatusBarInterpolation.Immediate
local prefixes = { "ActionButton", "MultiBarBottomLeftButton", "MultiBarBottomRightButton",
    "MultiBarRightButton", "MultiBarLeftButton", "MultiBar5Button", "MultiBar6Button", "MultiBar7Button" }
local viewers = { "EssentialCooldownViewer", "UtilityCooldownViewer" }

local function Readable(value) return not (issecretvalue and issecretvalue(value)) end

-- Small in-memory diagnostic trace. Never stringify protected values, inspect
-- health/clip geometry, or write diagnostic data into character settings.
local trace, lastTrace, traceStarted = {}, {}, GetTime()
function G.DebugValue(value)
    if not Readable(value) then return "protected" end
    local kind = type(value)
    if kind == "nil" then return "nil" end
    if kind == "boolean" or kind == "number" or kind == "string" then return tostring(value) end
    return kind
end
function G.Trace(scope, detail)
    if scope ~= "error" and lastTrace[scope] == detail then return end
    lastTrace[scope] = detail
    trace[#trace + 1] = string.format("%.2f %s: %s", GetTime() - traceStarted, scope, detail)
    if #trace > 24 then table.remove(trace, 1) end
end
function G.DebugLines()
    local version = C_AddOns and C_AddOns.GetAddOnMetadata and C_AddOns.GetAddOnMetadata(addonName, "Version")
        or (GetAddOnMetadata and GetAddOnMetadata(addonName, "Version")) or "unknown version"
    local lines = { "Glow diagnostics " .. G.DebugValue(version) .. " (public flags only; no target health):" }
    for i = math.max(1, #trace - 15), #trace do lines[#lines + 1] = trace[i] end
    return lines
end

local function Slot(button)
    local slot = button.action
    if not Readable(slot) or type(slot) ~= "number" or slot <= 0 then return end
    return slot
end

local function CooldownSpell(button)
    -- Read current identity every time: viewer pools recycle frames, and CDM
    -- layout addons may move a pooled icon out of its original container.
    if button.GetSpellID then return button:GetSpellID() end
    local info
    if button.GetCooldownInfo then info = button:GetCooldownInfo()
    elseif C_CooldownViewer and C_CooldownViewer.GetCooldownViewerCooldownInfo then
        local cooldownID = button.cooldownID
        if Readable(cooldownID) and type(cooldownID) == "number" then
            info = C_CooldownViewer.GetCooldownViewerCooldownInfo(cooldownID)
        end
    end
    if not Readable(info) or type(info) ~= "table" then return end
    for _, key in ipairs({ "overrideTooltipSpellID", "overrideSpellID", "spellID" }) do
        local id = info[key]
        if not Readable(id) then return end
        if id ~= nil then return id end
    end
end

local function Matches(button, spellID, source)
    if not ns.CanAccessRegion(button) then return false, "icon inaccessible" end
    local visible = button:IsVisible()
    if not Readable(visible) then return false, "visibility protected" end
    if visible ~= true then return false, "icon hidden" end
    if source == "cooldown" then
        local id = CooldownSpell(button)
        if not Readable(id) then return false, "spell identity protected" end
        if type(id) ~= "number" or id <= 0 then return false, "spell identity missing" end
        if id == spellID then return true end
        -- Some viewer entries identify the base spell while the spellbook
        -- exposes a learned override. Only accept a readable exact resolution.
        if C_SpellBook and C_SpellBook.FindSpellOverrideByID then
            id = C_SpellBook.FindSpellOverrideByID(id)
            if not Readable(id) then return false, "override identity protected" end
            return id == spellID, "different spell"
        end
        return false, "different spell"
    end
    local slot = Slot(button)
    if not slot then return false, "action slot missing/protected" end
    local id
    if C_ActionBar and C_ActionBar.GetSpell then id = C_ActionBar.GetSpell(slot) end
    if not Readable(id) then return false, "action identity protected" end
    if id == spellID then return true end
    -- Also support ordinary macros when the client resolves their spell.
    if GetActionInfo then
        local kind, actionID = GetActionInfo(slot)
        if not Readable(kind) or not Readable(actionID) then return false, "action identity protected" end
        if kind == "spell" then return actionID == spellID end
        if kind == "macro" and GetMacroSpell then
            id = GetMacroSpell(actionID)
            if not Readable(id) then return false, "macro identity protected" end
            return id == spellID, "different macro spell"
        end
    end
    return false, "different spell"
end

local function Layout(entry)
    local button = entry.button
    if not ns.CanAccessRegion(button) then return end
    local w, h = button:GetWidth(), button:GetHeight()
    local scale = button:GetEffectiveScale()
    if not Readable(w) or not Readable(h) or not Readable(scale)
        or type(w) ~= "number" or type(h) ~= "number" or type(scale) ~= "number"
        or w <= 0 or h <= 0 or scale <= 0 then return end
    w, h = w * 1.4, h * 1.4
    local level = button:GetFrameLevel()
    if Readable(level) and type(level) == "number" then entry.root:SetFrameLevel(level + 10) end
    entry.root:SetScale(scale / UIParent:GetEffectiveScale())
    entry.root:ClearAllPoints(); entry.root:SetPoint("CENTER", button, "CENTER", 0, 0)
    entry.root:SetSize(w, h); entry.gate:SetSize(w, h); entry.clip:SetSize(w, h)
    entry.laidOut = true
end

local function Add(button, source)
    if not button or seen[button] or not ns.CanAccessRegion(button) then return end
    if not button.GetWidth or not button.IsVisible then return end
    if source == "cooldown" then
        if not button.GetSpellID and not button.GetCooldownInfo then
            local id = button.cooldownID
            if not Readable(id) or type(id) ~= "number" then return end
        end
    elseif not Slot(button) then return end
    seen[button] = true
    local root = CreateFrame("Frame", nil, UIParent)
    root:SetFrameStrata("HIGH"); root:EnableMouse(false); root:Hide()
    local gate = CreateFrame("StatusBar", nil, root)
    gate:SetAllPoints(root); gate:SetStatusBarTexture(WHITE); gate:SetStatusBarColor(1, 1, 1, 0)
    gate:SetMinMaxValues(0, 1); gate:SetValue(1, IMMEDIATE)
    local clip = CreateFrame("Frame", nil, gate)
    clip:SetPoint("TOPLEFT", gate:GetStatusBarTexture(), "TOPRIGHT", 0, 0)
    clip:SetClipsChildren(true)
    local bounds = CreateFrame("Frame", nil, clip)
    bounds:SetAllPoints(gate); bounds:SetClipsChildren(true)
    local alert
    if ActionButtonSpellAlertMixin then
        local ok, frame = pcall(CreateFrame, "Frame", nil, bounds, "ActionButtonSpellAlertTemplate")
        if ok and frame and frame.ProcLoop then alert = frame
        elseif ok and frame then frame:Hide() end
    end
    if not alert then
        alert = CreateFrame("Frame", nil, bounds)
        local border = alert:CreateTexture(nil, "OVERLAY")
        border:SetAllPoints(alert); border:SetTexture("Interface\\Buttons\\UI-ActionButton-Border")
        border:SetBlendMode("ADD"); border:SetVertexColor(1, 0.82, 0.2, 1)
        local clock = 0
        alert:SetScript("OnUpdate", function(_, delta)
            clock = (clock + delta) % 60
            border:SetAlpha(0.65 + 0.35 * math.sin(clock * 6)^2)
        end)
    end
    alert:SetAllPoints(bounds); alert:EnableMouse(false)
    -- A continuous Retail proc loop works without reading a secret visibility
    -- transition to trigger the initial burst. The native clip reveals it.
    alert.animationPlaying = true
    alert:Show()
    if alert.ProcLoop then
        root:SetScript("OnShow", function() alert.ProcLoop:Play() end)
        root:SetScript("OnHide", function() alert.ProcLoop:Stop() end)
        alert:HookScript("OnHide", function() alert.ProcLoop:Stop() end)
    end
    local entry = { button = button, source = source or "action", root = root, gate = gate, clip = clip, alert = alert,
        debugKey = (source or "action") .. "#" .. (#entries + 1) }
    entries[#entries + 1] = entry
    Layout(entry)
end

local function DiscoverViewer(viewer)
    if not viewer or not ns.CanAccessRegion(viewer) then return end
    local pool = viewer.itemFramePool
    if pool and pool.EnumerateActive then
        for icon in pool:EnumerateActive() do Add(icon, "cooldown") end
    elseif viewer.GetItemFrames then
        local icons = viewer:GetItemFrames()
        if Readable(icons) and type(icons) == "table" then
            for _, icon in pairs(icons) do Add(icon, "cooldown") end
        end
    end
end

function G.Discover()
    if InCombatLockdown() then return end
    for _, prefix in ipairs(prefixes) do for index = 1, 12 do Add(_G[prefix .. index]) end end
    for _, name in ipairs({ "ActionBarActionEventsFrame", "ActionBarButtonEventsFrame" }) do
        local registry = _G[name]
        if registry and type(registry.frames) == "table" then
            for _, button in pairs(registry.frames) do Add(button) end
        end
    end
    for _, name in ipairs(viewers) do pcall(DiscoverViewer, _G[name]) end
    for _, entry in ipairs(entries) do Layout(entry) end
end

function G.Update(spellID, minimum, health, alpha, enabled)
    if testUntil and GetTime() < testUntil and not InCombatLockdown() then
        spellID, minimum, health, alpha, enabled = testID, testMinimum, 1, 1, true
    else testUntil = nil end
    local matches = 0
    for _, entry in ipairs(entries) do
        local ok, match, why = false, false, "readiness off"
        if enabled and spellID and minimum then ok, match, why = pcall(Matches, entry.button, spellID, entry.source) end
        if enabled and spellID and minimum and entry.laidOut and ok and match then
            if entry.minimum ~= minimum then
                entry.gate:SetMinMaxValues(minimum - 1, minimum)
                entry.minimum = minimum
            end
            entry.gate:SetValue(health, IMMEDIATE)
            entry.gate:SetAlpha(alpha)
            -- Respect bar fades without branching on their potentially secret alpha.
            local sourceAlpha = 1
            if entry.button.GetEffectiveAlpha then sourceAlpha = entry.button:GetEffectiveAlpha(); entry.root:SetAlpha(sourceAlpha) end
            entry.root:Show()
            matches = matches + 1
            entry.debugSpell = spellID
            local animation = "fallback"
            if entry.alert.ProcLoop and entry.alert.ProcLoop.IsPlaying then
                local success, playing = pcall(entry.alert.ProcLoop.IsPlaying, entry.alert.ProcLoop)
                animation = success and G.DebugValue(playing) or "error"
            end
            G.Trace(entry.debugKey, "matched; cooldownAlpha=" .. G.DebugValue(alpha)
                .. " iconAlpha=" .. G.DebugValue(sourceAlpha) .. " loop=" .. animation)
        else
            entry.root:Hide()
            if entry.debugSpell and entry.debugSpell == spellID then
                G.Trace(entry.debugKey, "off: " .. (ok and (why or "not matched") or (why == "readiness off" and why or "match error: " .. G.DebugValue(match))))
            end
        end
    end
    G.matches = matches
end

function G.Hide()
    testUntil = nil
    for _, entry in ipairs(entries) do entry.root:Hide() end
    G.matches = 0
end

function G.Test(spellID, minimum)
    if InCombatLockdown() or not spellID or not minimum then return end
    G.Discover()
    testID, testMinimum, testUntil = spellID, minimum, GetTime() + 5
end

function G.Count(spellID, source)
    source = source or "action"
    local count = 0
    for _, entry in ipairs(entries) do
        local ok, match = false, false
        if entry.source == source then ok, match = pcall(Matches, entry.button, spellID, entry.source) end
        if ok and match then count = count + 1 end
    end
    return count
end

function G.Initialize()
    if not ActionButtonSpellAlertMixin and C_AddOns and C_AddOns.LoadAddOn then
        pcall(C_AddOns.LoadAddOn, "Blizzard_ActionBar")
    end
    G.Discover()
    local events = CreateFrame("Frame")
    for _, event in ipairs({ "PLAYER_REGEN_ENABLED", "PLAYER_ENTERING_WORLD", "ACTIONBAR_SLOT_CHANGED", "ACTIONBAR_PAGE_CHANGED" }) do events:RegisterEvent(event) end
    events:SetScript("OnEvent", G.Discover)
    events:SetScript("OnUpdate", function(_, delta)
        discoverElapsed = discoverElapsed + delta
        if discoverElapsed < 1 then return end
        discoverElapsed = 0
        G.Discover()
    end)
end
