-- Shadow Word: Death kill estimate. Health is sent only to the native renderer;
-- addon code never compares, formats, or reads back a protected health value.
local _, ns = ...
local L = ns.L
local Execute = {}
ns.Execute = Execute
local db, state, events
local initialized = false
local dirty, elapsed, retryElapsed = true, 0, 0
local refreshing = false
local cooldownAlpha, previewing = 1, false
local cooldownEventSpell, cooldownEventReady, realCooldownDuration
local awaitingOwnCooldown = false

local function Readable(value)
    return not (issecretvalue and issecretvalue(value))
end

-- A description contains only the spell body, without mana, range, or rank
-- headers. Accept an unambiguous integer damage range before any percentage.
-- Unknown/formula-only descriptions fail closed instead of guessing a damage.
local function MinimumDamage(description)
    if not Readable(description) or type(description) ~= "string" then return end
    local text = description:gsub("|c%x%x%x%x%x%x%x%x", ""):gsub("|r", "")
        :gsub("|T.-|t", ""):gsub("|A.-|a", "")
    if text:find("$", 1, true) or text:find("|", 1, true) then return end
    -- Spell damage at these ranks is below 10,000. Grouped thousands are
    -- supported, but decimal and other unfamiliar number formats are rejected.
    text = text:gsub("(%d)[,%.](%d%d%d)", "%1%2")
        :gsub("(%d)\194\160(%d%d%d)", "%1%2")
        :gsub("(%d)\226\128\175(%d%d%d)", "%1%2")
        :gsub("(%d) (%d%d%d)", "%1%2")
    local first, last, minimum, separator, maximum = text:find("(%d+)([^%d]+)(%d+)")
    if not first or text:sub(1, first - 1):find("%%") or separator:find("%%")
        or separator:find("[.,]") or #separator > 24
        or text:sub(last + 1):match("^%s*%%") then return end
    minimum, maximum = tonumber(minimum), tonumber(maximum)
    if minimum < 1 or maximum < minimum or maximum > minimum * 2 then return end
    return minimum
end
Execute.MinimumDamage = MinimumDamage

local function ScanSpell()
    state = { reason = "Shadow Word: Death is not learned." }
    if not C_SpellBook or not C_Spell or not C_Spell.GetSpellInfo
        or not C_Spell.GetSpellDescription or not C_SpellBook.GetNumSpellBookSkillLines
        or not C_SpellBook.GetSpellBookSkillLineInfo or not C_SpellBook.GetSpellBookItemInfo
        or not C_SpellBook.IsSpellKnown or not Enum.SpellBookSpellBank then
        state.reason = "Execute tracking is unavailable on this client."
        return
    end
    local names = { [L["Shadow Word: Death"]] = true }
    -- IDs only identify the localized spell name. Learned rank IDs and damage
    -- are discovered from this client's spellbook, never assumed from Retail.
    for _, id in ipairs({ 32379, 401955 }) do
        local info = C_Spell.GetSpellInfo(id)
        if info and Readable(info.name) and type(info.name) == "string" then names[info.name] = true end
    end
    local bank = Enum.SpellBookSpellBank.Player
    local bestLevel, bestRank = -1, -1
    for line = 1, C_SpellBook.GetNumSpellBookSkillLines() do
        local skill = C_SpellBook.GetSpellBookSkillLineInfo(line)
        if skill then
            for slot = skill.itemIndexOffset + 1, skill.itemIndexOffset + skill.numSpellBookItems do
                local info = C_SpellBook.GetSpellBookItemInfo(slot, bank)
                if info and names[info.name] and not info.isPassive and not info.isOffSpec then
                    local id = info.spellID or info.actionID
                    local known = id and C_SpellBook.IsSpellKnown(id, bank)
                    if Readable(known) and known == true then
                        local level = C_SpellBook.GetSpellBookItemLevelLearned
                            and C_SpellBook.GetSpellBookItemLevelLearned(slot, bank) or 0
                        local rank = tonumber((info.subName or ""):match("%d+")) or 0
                        if level > bestLevel or (level == bestLevel and rank > bestRank) then
                            bestLevel, bestRank = level, rank
                            state = { id = id, name = info.name, rank = info.subName or "" }
                        end
                    end
                end
            end
        end
    end
    if state.id then
        state.minimum = MinimumDamage(C_Spell.GetSpellDescription(state.id))
        state.reason = state.minimum and "Execute tracking active; damage is an estimate."
            or "Waiting for a readable spell damage range."
    end
end

local function True(value) return Readable(value) and value == true end
local function False(value) return Readable(value) and value == false end

local function ResetCooldownTracking()
    cooldownEventSpell, cooldownEventReady, realCooldownDuration = state and state.id, nil, nil
    awaitingOwnCooldown = false
end

local function SnapshotCooldown()
    realCooldownDuration = nil
    if C_Spell.GetSpellCooldownDuration then
        local duration = C_Spell.GetSpellCooldownDuration(state.id, true)
        if duration and duration.Copy then
            -- The API's live object can be reused/reconfigured by the client.
            -- Keep our own native clock snapshot, never a live GCD reference.
            realCooldownDuration = duration:Copy()
        end
    end
    ns.ActionGlow.Trace("cooldown snapshot", realCooldownDuration and "copied SWD timer" or "no copy available")
end

local function CaptureOwnCast(spellID)
    if not state or not state.id then return end
    if not Readable(spellID) then
        ResetCooldownTracking()
        ns.ActionGlow.Trace("cast", "protected identity; bootstrap cooldown check")
        return
    end
    local isDeath = spellID == state.id
    if not isDeath and type(spellID) == "number" then
        local info = C_Spell.GetSpellInfo(spellID)
        isDeath = info and Readable(info.name) and info.name == state.name
    end
    if not isDeath then return end
    cooldownEventSpell, cooldownEventReady, realCooldownDuration = state.id, false, nil
    awaitingOwnCooldown = true
    ns.ActionGlow.Trace("cast", "SWD succeeded; waiting for its cooldown")
end

local function CaptureCooldownEvent()
    if not state or not state.id or not C_Spell.GetSpellCooldown then return end
    if cooldownEventSpell ~= state.id then ResetCooldownTracking() end
    local info = C_Spell.GetSpellCooldown(state.id)
    local value = ns.ActionGlow.DebugValue
    if info then
        ns.ActionGlow.Trace("cooldown event", "enabled=" .. value(info.isEnabled) .. " active=" .. value(info.isActive) .. " GCD=" .. value(info.isOnGCD))
    else ns.ActionGlow.Trace("cooldown event", "no info") end
    if not info or not Readable(info.isActive) or type(info.isActive) ~= "boolean" then return end
    if not info.isActive then
        cooldownEventReady, realCooldownDuration, awaitingOwnCooldown = true, nil, false
    elseif awaitingOwnCooldown then
        if False(info.isOnGCD) then
            SnapshotCooldown()
            cooldownEventReady, awaitingOwnCooldown = false, false
        end
    elseif cooldownEventReady == nil and Readable(info.isOnGCD) and type(info.isOnGCD) == "boolean" then
        -- Bootstrap after login/rank changes. Once ready is established, only
        -- the player's SWD cast may arm another cooldown mask. Other spells'
        -- GCD events must never turn a ready SWD into a new "real" cooldown.
        cooldownEventReady = info.isOnGCD
        if not info.isOnGCD then SnapshotCooldown() end
    end
end

local function ApplyCooldownBoolean(ready)
    if Readable(ready) then
        if ready ~= true then return false end
        cooldownAlpha = 1
    elseif C_CurveUtil and C_CurveUtil.EvaluateColorValueFromBoolean then
        cooldownAlpha = C_CurveUtil.EvaluateColorValueFromBoolean(ready, 1, 0)
    else return false end
    return true
end

local function Blocked(reason)
    ns.ActionGlow.Trace("readiness", "off: " .. reason)
    return false
end

local function Available()
    if not state or not state.minimum then return Blocked("no learned damage estimate") end
    if not db.executeEnabled then return Blocked("disabled") end
    if not UnitExists or not UnitCanAttack or not UnitIsDeadOrGhost or not UnitHealth
        or not C_Spell.GetSpellCooldown or not C_Spell.IsSpellUsable or not C_Spell.IsSpellInRange then return Blocked("missing API") end
    if not True(UnitExists("target")) or not True(UnitCanAttack("player", "target"))
        or not False(UnitIsDeadOrGhost("target")) or not False(UnitIsDeadOrGhost("player")) then return Blocked("target/player invalid or inaccessible") end
    local cooldown = C_Spell.GetSpellCooldown(state.id)
    -- These two fields are explicitly NeverSecret in Forever. Do not read the
    -- cooldown start/duration or infer readiness from secret timer arithmetic.
    local value, path = ns.ActionGlow.DebugValue, "inactive"
    if not cooldown then return Blocked("no cooldown info") end
    if not True(cooldown.isEnabled) or not Readable(cooldown.isActive) or type(cooldown.isActive) ~= "boolean" then
        return Blocked("cooldown enabled=" .. value(cooldown.isEnabled) .. " active=" .. value(cooldown.isActive))
    end
    if cooldownEventSpell ~= state.id then ResetCooldownTracking() end
    if awaitingOwnCooldown then return Blocked("waiting for SWD cooldown update") end
    if not cooldown.isActive then
        cooldownEventReady, realCooldownDuration = true, nil
        cooldownAlpha = 1
    elseif cooldownEventReady == true then
        cooldownAlpha = 1
        path = "SWD ready; ignoring unrelated GCD updates"
    elseif realCooldownDuration and realCooldownDuration.HasExpired then
        path = "SWD cooldown snapshot"
        if not ApplyCooldownBoolean(realCooldownDuration:HasExpired()) then return Blocked("SWD cooldown not expired") end
    elseif cooldownEventReady == false then
        return Blocked("SWD cooldown active; snapshot unavailable")
    elseif C_Spell.GetSpellCooldownDuration and C_CurveUtil and C_CurveUtil.EvaluateColorValueFromBoolean then
        local duration = C_Spell.GetSpellCooldownDuration(state.id, true)
        if not duration or not duration.IsZero then return Blocked("no bootstrap cooldown duration") end
        path = "bootstrap duration IsZero"
        if not ApplyCooldownBoolean(duration:IsZero()) then return Blocked("bootstrap duration IsZero=false") end
    else
        return Blocked("active cooldown; no bootstrap duration API")
    end
    local usable, insufficientPower = C_Spell.IsSpellUsable(state.id)
    if not True(usable) then return Blocked("usable=" .. value(usable) .. " insufficientPower=" .. value(insufficientPower)) end
    local inRange = C_Spell.IsSpellInRange(state.id, "target")
    if not True(inRange) then return Blocked("range=" .. value(inRange)) end
    ns.ActionGlow.Trace("readiness", "ready; " .. path .. " alpha=" .. value(cooldownAlpha))
    return true
end

function Execute.Update()
    if not initialized then return end
    if dirty then dirty = false; ScanSpell() end
    local available = Available()
    local health
    if available then health = UnitHealth("target", false) end
    ns.ActionGlow.Update(state and state.id, state and state.minimum, health, cooldownAlpha,
        available and not previewing)
end

function Execute.SetPreview(value)
    previewing = value
    if initialized then Execute.Update() end
end

function Execute.TestGlow()
    if state then ns.ActionGlow.Test(state.id, state.minimum); Execute.Update() end
end

local function Refresh()
    if refreshing then return end
    refreshing = true
    local ok, failure = pcall(Execute.Update)
    refreshing = false
    if not ok then
        ns.ActionGlow.Hide()
        state = state or {}; state.failure = ns.ActionGlow.DebugValue(failure)
        ns.ActionGlow.Trace("error", state.failure)
    elseif state then state.failure = nil end
end

Execute.Refresh = Refresh

function Execute.DebugLines() return ns.ActionGlow.DebugLines() end

function Execute.Status()
    if not state then return L["Execute tracking is unavailable on this client."] end
    if state.failure then return state.failure end
    if not state.minimum then return L[state.reason] end
    return string.format("%s %s (ID %d): %s. %s %s; %s", state.name, state.rank, state.id,
        string.format(L["Below %d HP (estimate)"], state.minimum), L[state.reason],
        string.format(L["Matching action buttons: %d"], ns.ActionGlow.Count(state.id)),
        string.format(L["Matching cooldown icons: %d"], ns.ActionGlow.Count(state.id, "cooldown")))
end

function Execute.Initialize(saved)
    db = saved
    -- Preserve the old Enabled checkbox, then discard all removed text-layout data.
    if type(db.executeEnabled) ~= "boolean" then
        local old = type(db.groupOptions) == "table" and db.groupOptions.execute
        db.executeEnabled = not (type(old) == "table" and old.enabled == false)
    end
    db.executeDisplay = nil
    if type(db.groupOptions) == "table" then db.groupOptions.execute = nil end
    if type(db.groups) == "table" then db.groups.execute = nil end
    ns.ActionGlow.Initialize()
    events = CreateFrame("Frame")
    local rescan = { SPELLS_CHANGED = true, LEARNED_SPELL_IN_SKILL_LINE = true, SPELL_TEXT_UPDATE = true,
        PLAYER_EQUIPMENT_CHANGED = true, PLAYER_LEVEL_UP = true, PLAYER_ENTERING_WORLD = true }
    for event in pairs(rescan) do events:RegisterEvent(event) end
    for _, event in ipairs({ "PLAYER_TARGET_CHANGED", "SPELL_UPDATE_COOLDOWN", "SPELL_UPDATE_USABLE" }) do events:RegisterEvent(event) end
    events:RegisterUnitEvent("UNIT_HEALTH", "target")
    events:RegisterUnitEvent("UNIT_POWER_UPDATE", "player")
    events:RegisterUnitEvent("UNIT_SPELLCAST_SUCCEEDED", "player")
    events:SetScript("OnEvent", function(_, event, unit, castGUID, spellID)
        if event == "UNIT_HEALTH" and unit ~= "target" then return end
        if event == "UNIT_POWER_UPDATE" and unit ~= "player" then return end
        if rescan[event] then dirty = true end
        if event == "UNIT_SPELLCAST_SUCCEEDED" and Readable(unit) and unit == "player" then CaptureOwnCast(spellID) end
        if event == "SPELL_UPDATE_COOLDOWN" then CaptureCooldownEvent() end
        -- Refresh synchronously; routine spell-text notifications must not
        -- hide a valid alert for one polling interval.
        Refresh()
    end)
    events:SetScript("OnUpdate", function(_, delta)
        elapsed, retryElapsed = elapsed + delta, retryElapsed + delta
        if elapsed < 0.05 then return end
        elapsed = 0
        if retryElapsed >= 2 then
            retryElapsed = 0
            if not state or not state.minimum then dirty = true end
        end
        Refresh()
    end)
    initialized = true
    Refresh()
end
