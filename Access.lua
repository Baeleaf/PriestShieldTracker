local _, ns = ...

-- Aura objects can remain inaccessible between pulls in an instance. Combat
-- lockdown alone does not describe access to Blizzard's adopted aura subtree.
local function Readable(value)
    return not (issecretvalue and issecretvalue(value))
end

function ns.CanAccessRegion(region)
    if not region then return false end
    if region.CanBeAccessedInContext then
        local ok, allowed = pcall(region.CanBeAccessedInContext, region)
        if not ok or not Readable(allowed) or not allowed then return false end
    elseif region.IsForbidden then
        local ok, forbidden = pcall(region.IsForbidden, region)
        if not ok or not Readable(forbidden) or forbidden then return false end
    end
    return true
end
