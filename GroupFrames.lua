-- Frame discovery adapted from Weakened Soul Tracker 2.6.0, nocktambule (MIT).
-- See licenses/WeakenedSoulTracker.txt. Rendering lives in GroupAuraNative.lua.
local _, ns = ...
local G, Native = {}, ns.Native
ns.GroupFrames = G
ns.CORNERS = {
    tl = { "TOPLEFT", 2, -2 }, tr = { "TOPRIGHT", -2, -2 },
    bl = { "BOTTOMLEFT", 2, 2 }, br = { "BOTTOMRIGHT", -2, 2 }, c = { "CENTER", 0, 0 },
}
local defaults = {
    enabled = true, corner = "tr", size = 16, showOthers = false,
    soonReady = 3, timeFormat = "seconds", showBorder = true,
    borderMine = { r = 0.9, g = 0.1, b = 0.1, a = 0.9 },
    borderOthers = { r = 0.6, g = 0.3, b = 1.0, a = 0.9 },
}
local db, pending, initialized
local attached, hooked = {}, {}
local driver = CreateFrame("Frame")

local function Readable(value) return not (issecretvalue and issecretvalue(value)) end
local function FrameUnit(frame)
    if not ns.CanAccessRegion(frame) then return end
    local unit = frame.unit
    if Readable(unit) and type(unit) == "string" and
        (unit == "player" or unit:match("^party[1-4]$") or unit:match("^raid%d+$")) then return unit end
end
local function IsGroupFrame(frame)
    local name = frame.GetName and frame:GetName()
    if Readable(name) and type(name) == "string" and
        (name:match("^CompactPartyFrameMember%d+$") or name:match("^CompactRaidFrame%d+$")
        or name:match("^CompactRaidGroup%d+Member%d+$")) then return true end
    if PartyFrame then
        for i = 1, 4 do if frame == PartyFrame["MemberFrame" .. i] then return true end end
    end
    return false
end
local function Attach(frame)
    if not frame then return end
    if not ns.CanAccessRegion(frame) then pending = true; return end
    if not IsGroupFrame(frame) then return end
    local handle = attached[frame]
    if not handle then
        if InCombatLockdown() then pending = true; return end
        handle = Native.Attach(frame, {
            corner = function() return db.corner end, size = function() return db.size end,
        })
        if not handle then return end
        attached[frame] = handle
    end
    Native.SetUnit(handle, FrameUnit(frame))
    if handle.shown ~= db.enabled then Native.SetShown(handle, db.enabled) end
end
local function HookBlizzard()
    if not hooksecurefunc then return end
    for _, name in ipairs({ "CompactUnitFrame_SetUnit", "CompactUnitFrame_UpdateAll" }) do
        if type(_G[name]) == "function" and not hooked[name] then
            hooksecurefunc(name, Attach); hooked[name] = true
        end
    end
    if PartyFrame and PartyFrame.UpdatePartyFrames and not hooked[PartyFrame] then
        hooksecurefunc(PartyFrame, "UpdatePartyFrames", function() G.Refresh() end)
        hooked[PartyFrame] = true
    end
end
function G.Refresh()
    if not initialized or not Native.available then return end
    pending = false
    HookBlizzard()
    for i = 1, 5 do Attach(_G["CompactPartyFrameMember" .. i]) end
    for i = 1, 40 do Attach(_G["CompactRaidFrame" .. i]) end
    for group = 1, 8 do
        for member = 1, 5 do Attach(_G["CompactRaidGroup" .. group .. "Member" .. member]) end
    end
    if PartyFrame then
        for i = 1, 4 do Attach(PartyFrame["MemberFrame" .. i]) end
    end
    Native.Flush(FrameUnit)
end
function G.Configure()
    if not initialized then return end
    Native.RelayoutAll(); Native.ApplyOthers(); Native.ApplyTextOptions(); Native.ApplyBorders()
    G.Refresh()
end
function G.Initialize(database)
    if initialized then return end
    if type(database.groupFrames) ~= "table" then database.groupFrames = {} end
    db = database.groupFrames
    for key, value in pairs(defaults) do
        if type(value) == "table" then
            if type(db[key]) ~= "table" then db[key] = {} end
            for channel, number in pairs(value) do
                local saved = db[key][channel]
                if type(saved) ~= "number" or saved ~= saved or saved < 0 or saved > 1 then db[key][channel] = number end
            end
        elseif type(db[key]) ~= type(value) then db[key] = value end
    end
    if not ns.CORNERS[db.corner] then db.corner = defaults.corner end
    if db.size ~= db.size then db.size = defaults.size end
    db.size = math.max(10, math.min(40, db.size))
    if db.soonReady ~= db.soonReady then db.soonReady = defaults.soonReady end
    db.soonReady = math.max(0, math.min(10, db.soonReady))
    if db.timeFormat ~= "seconds" and db.timeFormat ~= "number" and db.timeFormat ~= "icon" then db.timeFormat = "seconds" end
    Native.Init(db, 6788)
    initialized = true
    for _, event in ipairs({ "ADDON_LOADED", "PLAYER_ENTERING_WORLD", "GROUP_ROSTER_UPDATE",
        "PLAYER_ROLES_ASSIGNED", "PLAYER_REGEN_ENABLED" }) do driver:RegisterEvent(event) end
    driver:SetScript("OnEvent", function() G.Refresh() end)
    local elapsed = 0
    driver:SetScript("OnUpdate", function(_, dt)
        elapsed = elapsed + dt
        if elapsed < 1 then return end
        elapsed = 0
        if not InCombatLockdown() and (pending or Native.HasPending()) then G.Refresh() end
    end)
    G.Refresh()
end
