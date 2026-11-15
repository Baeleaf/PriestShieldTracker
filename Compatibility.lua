-- Import the previous addon's character settings without changing its saved file.
local _, ns = ...
function ns.ImportPreviousSettings()
    local previous = _G["SoulShieldDB"]
    if type(previous) == "table" then return previous end
end
