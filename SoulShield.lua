local addonName = ...
local WHITE = "Interface\\Buttons\\WHITE8x8"
local FONT = STANDARD_TEXT_FONT or "Fonts\\FRIZQT__.TTF"
local SHIELD_IDS = {
    [17] = true, [592] = true, [600] = true, [3747] = true,
    [6065] = true, [6066] = true, [10898] = true,
    [10899] = true, [10900] = true, [10901] = true,
}
local defaults = { x = 0, y = -145, width = 260, barHeight = 19, scale = 1, locked = true }
local groupDefaults = {
    weakenedSoul = { scale = 1, fontSize = 16, iconSize = 20, showIcon = true },
    shield = { scale = 1, fontSize = 12 },
}
local db, hud, bar, amountText, container, preview, liveRoot, auraRoot
local maximum, previousAmount, hasReference, previewStarted
local initialized, pendingLayout = false, false
local nativeFailure
local shieldButton, absorbLabel
local nativeParts, handles = {}, {}
local StopPreview, StartPreview
local absorbGate, timerFormatter
local textRegions = {}
local nativeReadyCross, settingsPanel, selectedGroup = nil, nil, "weakenedSoul"
local focusedGroup
local ShowSettings, BeginEditing, EndEditing, OpenEditMode, CloseEditMode, SetupEditMode
local editModeActive, updatingControls = false, false
-- Group positions are offsets in HUD pixels. Text remains owned by its native aura
-- button even when its anchor is moved, so Blizzard still controls visibility.
local parts = {
    absorb = { title = "Absorb bar", point = "TOPLEFT", x = 0, y = -27, height = 19 },
    absorbLabel = { title = "Absorb label", point = "LEFT", relative = "absorb", relativePoint = "LEFT", x = 6, y = 0, width = 70, height = 18 },
    absorbAmount = { title = "Absorb number", point = "RIGHT", relative = "absorb", relativePoint = "RIGHT", x = -6, y = 0, width = 65, height = 18 },
    weakenedLabel = { title = "Shield Ready", point = "RIGHT", relativePoint = "TOPRIGHT", x = -26, y = -13, width = 112, height = 24 },
    weakenedTime = { title = "Debuff timer", point = "LEFT", relativePoint = "TOPRIGHT", x = -188, y = -13, width = 42, height = 24 },
    weakenedIcon = { title = "Shield unavailable", point = "LEFT", relative = "weakenedLabel", relativePoint = "RIGHT", x = 6, y = 0, width = 20, height = 20 },
    duration = { title = "Duration bar", point = "TOPLEFT", x = 0, y = -48, height = 3 },
    shieldLabel = { title = "Shield label", point = "TOPLEFT", x = 0, y = -56, width = 145, height = 18 },
    shieldTime = { title = "Shield timer", point = "TOPRIGHT", x = 0, y = -56, width = 70, height = 18 },
}

local function ReadyWidth()
    local options = db.groupOptions.weakenedSoul
    return 154 * options.fontSize / 16 + 8 + (options.showIcon and options.iconSize + 6 or 0)
end

local function FontSize(size, group, role)
    local options = db.groupOptions[group]
    if role == "cross" then return options.iconSize * 1.1 * options.scale end
    return size * options.fontSize / groupDefaults[group].fontSize * options.scale
end
local groups = {
    weakenedSoul = { title = "Shield Ready and countdown", y = 0, height = 26, width = 188 },
    shield = { title = "Shield bars, text and countdown", y = -27, height = 47 },
}

local function PlacePart(region, key, relativeBar, relativeLabel)
    if not region then return end
    local spec = parts[key]
    local group = (key == "weakenedLabel" or key == "weakenedTime" or key == "weakenedIcon") and "weakenedSoul" or "shield"
    local offset = db.groups[group]
    local options, baseY = db.groupOptions[group], groups[group].y
    -- The absorb label and amount inherit movement through their bar anchor.
    local x, y = spec.relative and 0 or offset.x, spec.relative and 0 or offset.y
    local relative = spec.relative and (relativeBar or bar) or hud
    if spec.relative == "weakenedLabel" then relative = relativeLabel or nativeParts.weakenedLabel end
    region:ClearAllPoints()
    local partX, partY = spec.x, spec.y
    if key == "weakenedLabel" then partX = -(options.showIcon and options.iconSize + 6 or 0) end
    if key == "weakenedTime" then partX = -ReadyWidth() end
    if key == "duration" then partY = -27 - db.barHeight - 2 end
    if key == "shieldLabel" or key == "shieldTime" then partY = -27 - db.barHeight - 10 end
    partX = partX * options.scale
    partY = spec.relative and partY * options.scale or baseY + (partY - baseY) * options.scale
    region:SetPoint(spec.point, relative, spec.relativePoint or spec.point, partX + x, partY + y)
    if spec.height and not spec.width then
        region:SetSize(db.width * options.scale, (key == "absorb" and db.barHeight or spec.height) * options.scale)
    end
    if key == "weakenedLabel" then region:SetWidth(spec.width * options.fontSize / 16 * options.scale) end
    if key == "weakenedIcon" then region:SetSize(options.iconSize * options.scale, options.iconSize * options.scale) end
end

local function LayoutParts()
    PlacePart(absorbGate, "absorb")
    PlacePart(bar, "absorb")
    PlacePart(absorbLabel, "absorbLabel")
    PlacePart(amountText, "absorbAmount")
    if not InCombatLockdown() then
        for key, region in pairs(nativeParts) do PlacePart(region, key) end
        for _, entry in ipairs(textRegions) do
            local size = FontSize(entry.size, entry.group, entry.role)
            if entry.applied ~= size then
                entry.region:SetFont(FONT, size, "OUTLINE")
                entry.applied = size
            end
        end
        local showIcon = db.groupOptions.weakenedSoul.showIcon
        if nativeParts.weakenedIcon then nativeParts.weakenedIcon:SetShown(showIcon) end
        if nativeReadyCross then nativeReadyCross:SetShown(showIcon) end
    end
    if preview then
        for key in pairs(parts) do PlacePart(preview.parts[key], key, preview.absorb, preview.ws) end
    end
    local shieldScale = db.groupOptions.shield.scale
    if bar.edge then bar.edge:SetSize(2 * shieldScale, db.barHeight * shieldScale) end
    if preview and preview.absorb.edge then preview.absorb.edge:SetSize(2 * shieldScale, db.barHeight * shieldScale) end
    for key, handle in pairs(handles) do
        local spec, offset = groups[key], db.groups[key]
        handle:ClearAllPoints()
        local point = spec.width and "TOPRIGHT" or "TOPLEFT"
        handle:SetPoint(point, hud, point, offset.x, spec.y + offset.y)
        local options = db.groupOptions[key]
        local width = key == "weakenedSoul" and ReadyWidth() or db.width
        local height = key == "weakenedSoul" and math.max(26 * options.fontSize / 16, options.showIcon and options.iconSize + 6 or 0) or db.barHeight + 28
        handle:SetSize(width * options.scale, height * options.scale)
        handle:SetShown(not db.locked)
    end
end

local function Secret(value)
    return issecretvalue and issecretvalue(value) or false
end

local function Print(message)
    DEFAULT_CHAT_FRAME:AddMessage("|cffc8a0ffSoulShield:|r " .. message)
end

local function ClearGroupFocus()
    focusedGroup = nil
    for _, handle in pairs(handles) do
        if handle.selection then handle.selection:SetColorTexture(0.65, 0.45, 1, 0.18) end
    end
    if settingsPanel then settingsPanel:Hide() end
end

local function Text(parent, size, r, g, b, group, role)
    local text = parent:CreateFontString(nil, "OVERLAY")
    local applied = group and FontSize(size, group, role) or size
    text:SetFont(FONT, applied, "OUTLINE")
    if group then table.insert(textRegions, { region = text, size = size, group = group, role = role, applied = applied }) end
    text:SetTextColor(r or 1, g or 1, b or 1)
    text:SetShadowOffset(1, -1)
    return text
end

local function BuildReadyIcon(parent)
    local icon = parent:CreateTexture(nil, "ARTWORK")
    icon:SetTexture("Interface\\Icons\\Spell_Holy_PowerWordShield")
    icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
    local cross = Text(parent, 22, 1, 0.15, 0.15, "weakenedSoul", "cross")
    cross:SetPoint("CENTER", icon, "CENTER", 0, 0)
    cross:SetText("X")
    return icon, cross
end

local function NewBar(parent, height, r, g, b)
    local status = CreateFrame("StatusBar", nil, parent)
    status:SetHeight(height)
    status:SetStatusBarTexture(WHITE)
    status:SetStatusBarColor(r, g, b, 1)
    status:SetMinMaxValues(0, 1)
    status:SetValue(0)
    local background = status:CreateTexture(nil, "BACKGROUND")
    background:SetAllPoints()
    background:SetColorTexture(0.035, 0.025, 0.055, 0.85)
    return status
end

local function BuildAbsorb(parent)
    local status = NewBar(parent, 19, 0.55, 0.28, 0.85)
    local label = Text(status, 11, 0.95, 0.91, 1, "shield")
    label:SetText("Absorb")
    local amount = Text(status, 12, 1, 1, 1, "shield")
    -- Follow the native fill without inspecting its secret value or geometry.
    local edge = status:CreateTexture(nil, "OVERLAY")
    edge:SetColorTexture(1, 0.95, 1, 0.95)
    edge:SetSize(2, 19)
    edge:SetPoint("CENTER", status:GetStatusBarTexture(), "RIGHT", 0, 0)
    status.absorbLabel, status.amountText = label, amount
    status.edge = edge
    return status, label, amount
end

local function SetMaximum(value)
    maximum = value
    hasReference = true
    bar:SetMinMaxValues(0, value)
end

local function TimerOptions()
    if not timerFormatter then
        timerFormatter = C_StringUtil.CreateNumericRuleFormatter()
        timerFormatter:SetBreakpoints({
            { threshold = 0, format = "%.1f", step = 0.1, rounding = Enum.NumericRuleFormatRounding.Nearest },
        })
    end
    local binding = C_DurationUtil.CreateDurationTextBinding()
    binding:SetFormatter(timerFormatter)
    binding:SetUpdateInterval(0.05)
    return { binding = binding }
end

local function UpdateAbsorb()
    if not initialized then return end
    local amount = UnitGetTotalAbsorbs("player")
    if not Secret(amount) then
        if type(amount) ~= "number" then amount = 0 end
        -- Learn the total at application/increase, never lower the reference
        -- merely because damage depleted it. Secret values never enter the DB.
        if amount > 0 and ((previousAmount and amount > previousAmount)
            or (not previousAmount and (not hasReference or amount > maximum))) then
            SetMaximum(amount)
            db.reference = amount
        end
        previousAmount = amount
    else
        previousAmount = nil
    end
    if not hasReference then
        -- A first login in combat may have no readable full shield yet.
        -- Max health provides a native-safe fallback, without a zero maximum.
        bar:SetMinMaxValues(0, UnitHealthMax("player"))
    end
    bar:SetValue(amount)
    amountText:SetFormattedText("%.0f", amount)
    -- SetValue explicitly accepts secret inputs from tainted addon execution.
    -- A 0..1 native fill clips the display to nothing at zero, or full width
    -- for positive whole-point absorbs. Never evaluate or inspect that fill.
    absorbGate:SetValue(amount)
end

local function Layout()
    if InCombatLockdown() then pendingLayout = true; return end
    pendingLayout = false
    hud:SetSize(db.width, math.max(80, db.barHeight + 61))
    hud:SetScale(db.scale)
    hud:ClearAllPoints()
    hud:SetPoint("CENTER", UIParent, "CENTER", db.x, db.y)
    hud:EnableMouse(not db.locked)
    hud.moveHint:SetShown(not db.locked)
    hud.moveHandle:SetShown(not db.locked)
    LayoutParts()
end

local function NativeTimer(button, shield)
    -- All timer regions must belong to the aura button: Blizzard owns their
    -- visibility and countdown in combat. Never poll or hook its aura state.
    button:EnableMouse(false)
    button:SetSize(db.width, shield and 24 or 26)
    if shield then
        button:SetPoint("TOPLEFT", container, "TOPLEFT", 0, -48)
        button:SetPoint("TOPRIGHT", container, "TOPRIGHT", 0, -48)
        local duration = NewBar(button, 3, 0.63, 0.43, 0.94)
        duration:SetPoint("TOPLEFT")
        duration:SetPoint("TOPRIGHT")
        local label = Text(button, 11, 0.8, 0.77, 0.86, "shield")
        label:SetPoint("TOPLEFT", 0, -8)
        label:SetText("Shield expires in")
        local countdown = Text(button, 11, 0.9, 0.86, 1, "shield")
        countdown:SetPoint("TOPRIGHT", 0, -8)
        button:SetDurationBar(duration, { direction = Enum.StatusBarTimerDirection.RemainingTime })
        button:SetDurationText(countdown, TimerOptions())
        nativeParts.duration = duration
        nativeParts.shieldLabel = label
        nativeParts.shieldTime = countdown
        PlacePart(duration, "duration")
        PlacePart(label, "shieldLabel")
        PlacePart(countdown, "shieldTime")
        shieldButton = button
    else
        button:SetPoint("TOPLEFT", container, "TOPLEFT", 0, 0)
        button:SetPoint("TOPRIGHT", container, "TOPRIGHT", 0, 0)
        local name = Text(button, 16, 0.94, 0.88, 0.74, "weakenedSoul")
        name:SetJustifyH("RIGHT")
        name:SetText("Shield Ready")
        local countdown = Text(button, 18, 0.94, 0.88, 0.74, "weakenedSoul")
        countdown:SetJustifyH("LEFT")
        button:SetDurationText(countdown, TimerOptions())
        nativeParts.weakenedLabel = name
        nativeParts.weakenedTime = countdown
        -- Static artwork owned by the aura button, so its visibility follows
        -- the game-controlled row without reading any restricted aura state.
        nativeParts.weakenedIcon, nativeReadyCross = BuildReadyIcon(button)
        PlacePart(name, "weakenedLabel")
        PlacePart(countdown, "weakenedTime")
        PlacePart(nativeParts.weakenedIcon, "weakenedIcon")
        nativeParts.weakenedIcon:SetShown(db.groupOptions.weakenedSoul.showIcon)
        nativeReadyCross:SetShown(db.groupOptions.weakenedSoul.showIcon)
    end
end

local function SetupNativeTimers()
    if not C_AuraContainerUtil and C_AddOns and C_AddOns.LoadAddOn then
        C_AddOns.LoadAddOn("Blizzard_AuraContainer")
    end
    if not C_AuraContainerUtil or not CustomAuraContainerSlotDefaultOptions then
        error("This client does not expose the native aura display.")
    end
    container = CreateFrame("AuraContainer", nil, auraRoot, "CustomAuraContainerTemplate")
    container:SetAllPoints(hud)
    container:SetFrameLevel(bar:GetFrameLevel() + 2)
    local neverSecret = C_Secrets and C_Secrets.GetSpellAuraSecrecy
        and C_Secrets.GetSpellAuraSecrecy(6788) == Enum.SecrecyLevel.NeverSecret
    local filters
    if neverSecret then
        filters = { includeSpellIDs = { [6788] = true } }
    else
        -- Friendly harmful auras cannot generally be selected by identity.
        -- Restrict to our own short, non-dispellable debuffs; ideal for solo.
        filters = {
            excludeDispelTypes = { Magic = true, Curse = true, Poison = true, Disease = true },
            maxDuration = 15.5,
            isBossOrRoleAura = false,
        }
    end
    container:AddAuraSlot("weakenedSoul", neverSecret and "HARMFUL" or "HARMFUL|PLAYER", {
        candidateFilters = filters,
        initializeFrame = function(button) NativeTimer(button, false) end,
    })
    container:AddAuraSlot("shield", "HELPFUL", {
        candidateFilters = { includeSpellIDs = SHIELD_IDS },
        initializeFrame = function(button) NativeTimer(button, true) end,
    })
    container:SetUnit("player")
    container:SetEnabled(true)
    LayoutParts()
end

local function BuildPreview()
    preview = CreateFrame("Frame", nil, hud)
    preview:SetAllPoints()
    preview:SetFrameLevel(bar:GetFrameLevel() + 5)
    preview.absorb, preview.absorbLabel, preview.absorbAmount = BuildAbsorb(preview)
    preview.ws = Text(preview, 16, 0.94, 0.88, 0.74, "weakenedSoul")
    preview.ws:SetPoint("TOPLEFT", 0, -4)
    preview.ws:SetText("Shield Ready")
    preview.ws:SetJustifyH("RIGHT")
    preview.wsTime = Text(preview, 18, 0.94, 0.88, 0.74, "weakenedSoul")
    preview.wsTime:SetPoint("TOPRIGHT", 0, -3)
    preview.wsTime:SetJustifyH("LEFT")
    preview.readyIcon, preview.readyCross = BuildReadyIcon(preview)
    preview.readyIcon:SetShown(db.groupOptions.weakenedSoul.showIcon)
    preview.readyCross:SetShown(db.groupOptions.weakenedSoul.showIcon)
    preview.duration = NewBar(preview, 3, 0.63, 0.43, 0.94)
    preview.duration:SetPoint("TOPLEFT", 0, -48)
    preview.duration:SetPoint("TOPRIGHT", 0, -48)
    preview.duration:SetMinMaxValues(0, 30)
    preview.label = Text(preview, 11, 0.8, 0.77, 0.86, "shield")
    preview.label:SetPoint("TOPLEFT", 0, -56)
    preview.label:SetText("Shield expires in")
    preview.time = Text(preview, 11, 0.9, 0.86, 1, "shield")
    preview.time:SetPoint("TOPRIGHT", 0, -56)
    preview.parts = {
        absorb = preview.absorb, absorbLabel = preview.absorbLabel, absorbAmount = preview.absorbAmount,
        weakenedLabel = preview.ws, weakenedTime = preview.wsTime,
        weakenedIcon = preview.readyIcon,
        duration = preview.duration, shieldLabel = preview.label, shieldTime = preview.time,
    }
    preview:Hide()
end

local function BuildHandles()
    for key, spec in pairs(groups) do
        local groupKey = key
        local handle = CreateFrame("Frame", nil, hud)
        handles[groupKey] = handle
        handle:SetFrameStrata("DIALOG")
        handle.groupKey = groupKey
        handle:SetFrameLevel(preview:GetFrameLevel() + 5)
        handle:EnableMouse(true)
        handle:RegisterForDrag("LeftButton")
        local background = handle:CreateTexture(nil, "BACKGROUND")
        handle.selection = background
        background:SetAllPoints()
        background:SetColorTexture(0.65, 0.45, 1, 0.18)
        handle:SetScript("OnEnter", function(self)
            GameTooltip:SetOwner(self, "ANCHOR_TOP")
            GameTooltip:SetText(spec.title .. ": drag to move, click for settings")
            GameTooltip:Show()
        end)
        handle:SetScript("OnLeave", function() GameTooltip:Hide() end)
        handle:SetScript("OnMouseUp", function(_, button)
            if button == "LeftButton" and not db.locked and not InCombatLockdown() then ShowSettings(groupKey) end
        end)
        handle:SetScript("OnDragStart", function(self)
            if db.locked or InCombatLockdown() then return end
            GameTooltip:Hide()
            ShowSettings(groupKey)
            local startX, startY = GetCursorPosition()
            local initialX, initialY = db.groups[groupKey].x, db.groups[groupKey].y
            self:SetScript("OnUpdate", function()
                if InCombatLockdown() then self:SetScript("OnUpdate", nil); return end
                local x, y = GetCursorPosition()
                local scale = hud:GetEffectiveScale()
                db.groups[groupKey].x = initialX + (x - startX) / scale
                db.groups[groupKey].y = initialY + (y - startY) / scale
                LayoutParts()
            end)
        end)
        handle:SetScript("OnDragStop", function(self) self:SetScript("OnUpdate", nil) end)
    end
end

local function TickPreview()
    if not previewStarted then return end
    local elapsed = db.locked and (GetTime() - previewStarted) % 18 or 0
    local remaining = math.max(0, 15 - elapsed)
    preview.ws:SetShown(remaining > 0)
    preview.wsTime:SetShown(remaining > 0)
    preview.readyIcon:SetShown(remaining > 0 and db.groupOptions.weakenedSoul.showIcon)
    preview.readyCross:SetShown(remaining > 0 and db.groupOptions.weakenedSoul.showIcon)
    preview.wsTime:SetFormattedText("%.1f", remaining)
    preview.duration:SetValue(30 - elapsed)
    preview.time:SetFormattedText("%.1f", 30 - elapsed)
    local absorb = math.max(0, 1100 - math.floor(elapsed / 2) * 145)
    preview.duration:SetShown(absorb > 0)
    preview.label:SetShown(absorb > 0)
    preview.time:SetShown(absorb > 0)
    preview.absorb:SetMinMaxValues(0, 1100)
    preview.absorb:SetValue(absorb)
    preview.absorbAmount:SetFormattedText("%.0f", absorb)
end

StopPreview = function()
    previewStarted = nil
    hud:SetScript("OnUpdate", nil)
    preview:Hide()
    -- Only toggle our ordinary wrapper, including at combat entry. Never
    -- touch the restricted aura container/button to leave preview mode.
    liveRoot:Show()
    UpdateAbsorb()
end

StartPreview = function()
    previewStarted = GetTime()
    liveRoot:Hide()
    preview:Show()
    hud:SetScript("OnUpdate", TickPreview)
    TickPreview()
end

local function AddSettingsSlider(panel, key, caption, low, high, step, y, format, getter, setter)
    local slider = CreateFrame("Slider", nil, panel)
    panel.controls[key] = slider
    slider:SetSize(252, 16)
    slider:SetPoint("TOPLEFT", 24, y - 20)
    slider:SetOrientation("HORIZONTAL")
    slider:SetMinMaxValues(low, high)
    slider:SetValueStep(step)
    slider:SetObeyStepOnDrag(true)
    slider:SetThumbTexture("Interface\\Buttons\\UI-SliderBar-Button-Horizontal")
    local track = slider:CreateTexture(nil, "BACKGROUND")
    track:SetPoint("LEFT"); track:SetPoint("RIGHT"); track:SetHeight(4)
    track:SetColorTexture(0.25, 0.22, 0.34, 1)
    slider.caption = Text(slider, 12, 0.95, 0.92, 1)
    slider.caption:SetPoint("BOTTOMLEFT", slider, "TOPLEFT", 0, 3)
    slider.getter = getter
    slider.refresh = function()
        local value = getter()
        slider:SetValue(value)
        slider.caption:SetText(caption .. ": " .. string.format(format, value))
    end
    slider:SetScript("OnValueChanged", function(_, value)
        if updatingControls or InCombatLockdown() or db.locked then return end
        value = math.max(low, math.min(high, math.floor(value / step + 0.5) * step))
        setter(value)
        slider.caption:SetText(caption .. ": " .. string.format(format, value))
        Layout()
    end)
    return slider
end

local function BuildSettingsPanel()
    local panel = CreateFrame("Frame", "SoulShieldEditSettings", UIParent, "BackdropTemplate")
    settingsPanel = panel
    panel.controls = {}
    panel:SetSize(300, 380)
    local position = db.menuPosition
    if type(position) == "table" and type(position.x) == "number" and type(position.y) == "number"
        and position.x == position.x and position.y == position.y
        and math.abs(position.x) < 10000 and math.abs(position.y) < 10000 then
        panel:SetPoint("CENTER", UIParent, "CENTER", position.x, position.y)
    else
        panel:SetPoint("RIGHT", UIParent, "RIGHT", -34, 0)
    end
    panel:SetMovable(true)
    panel:SetClampedToScreen(true)
    panel:SetFrameStrata("DIALOG")
    panel:EnableMouse(true)
    panel:SetBackdrop({ bgFile = WHITE, edgeFile = WHITE, edgeSize = 1 })
    panel:SetBackdropColor(0.035, 0.03, 0.055, 0.97)
    panel:SetBackdropBorderColor(0.5, 0.4, 0.7, 1)
    local titleBar = CreateFrame("Frame", nil, panel)
    panel.titleBar = titleBar
    titleBar:SetPoint("TOPLEFT", 1, -1)
    titleBar:SetPoint("TOPRIGHT", -1, -1)
    titleBar:SetHeight(36)
    titleBar:EnableMouse(true)
    titleBar:RegisterForDrag("LeftButton")
    local dragging = false
    local function StopMenuDrag()
        if not dragging then return end
        dragging = false
        panel:StopMovingOrSizing()
        local x, y = panel:GetCenter()
        if not x or not y then return end
        local ratio = panel:GetEffectiveScale() / UIParent:GetEffectiveScale()
        db.menuPosition = { x = x - UIParent:GetWidth() / ratio / 2, y = y - UIParent:GetHeight() / ratio / 2 }
        panel:ClearAllPoints()
        panel:SetPoint("CENTER", UIParent, "CENTER", db.menuPosition.x, db.menuPosition.y)
    end
    titleBar:SetScript("OnDragStart", function()
        if InCombatLockdown() then return end
        dragging = true
        panel:StartMoving()
    end)
    titleBar:SetScript("OnDragStop", StopMenuDrag)
    panel:SetScript("OnHide", StopMenuDrag)
    local title = Text(titleBar, 17, 0.96, 0.9, 1)
    title:SetPoint("CENTER", 0, -4); title:SetText("SoulShield")
    panel.subtitle = Text(panel, 12, 0.8, 0.78, 0.86)
    panel.subtitle:SetPoint("TOP", 0, -44)
    AddSettingsSlider(panel, "groupScale", "Group size", 50, 200, 5, -74, "%d%%",
        function() return db.groupOptions[selectedGroup].scale * 100 end,
        function(value) db.groupOptions[selectedGroup].scale = value / 100 end)
    AddSettingsSlider(panel, "fontSize", "Text size", 9, 28, 1, -124, "%d",
        function() return db.groupOptions[selectedGroup].fontSize end,
        function(value) db.groupOptions[selectedGroup].fontSize = value end)
    AddSettingsSlider(panel, "width", "Bar width", 180, 500, 5, -174, "%d",
        function() return db.width end, function(value) db.width = value end)
    AddSettingsSlider(panel, "barHeight", "Bar height", 12, 40, 1, -224, "%d",
        function() return db.barHeight end, function(value) db.barHeight = value end)
    AddSettingsSlider(panel, "iconSize", "Icon size", 12, 40, 1, -174, "%d",
        function() return db.groupOptions.weakenedSoul.iconSize end,
        function(value) db.groupOptions.weakenedSoul.iconSize = value end)
    local check = CreateFrame("CheckButton", nil, panel, "UICheckButtonTemplate")
    panel.controls.showIcon = check
    check:SetSize(26, 26); check:SetPoint("TOPLEFT", 20, -224)
    local checkText = Text(check, 12, 0.95, 0.92, 1)
    checkText:SetPoint("LEFT", check, "RIGHT", 3, 0)
    checkText:SetText("Show crossed-out shield icon")
    check:SetScript("OnClick", function(self)
        if InCombatLockdown() or db.locked then return end
        db.groupOptions.weakenedSoul.showIcon = self:GetChecked() and true or false
        Layout(); TickPreview()
    end)
    local help = Text(panel, 11, 0.75, 0.73, 0.8)
    help:SetPoint("BOTTOM", 0, 65)
    help:SetText("Drag a group to move it.\nChanges save automatically for this character.")
    local reset = CreateFrame("Button", nil, panel, "UIPanelButtonTemplate")
    panel.resetButton = reset
    reset:SetSize(124, 26); reset:SetPoint("BOTTOMLEFT", 20, 20)
    reset:SetText("Reset group")
    reset:SetScript("OnClick", function()
        if InCombatLockdown() or db.locked then return end
        for key, value in pairs(groupDefaults[selectedGroup]) do db.groupOptions[selectedGroup][key] = value end
        db.groups[selectedGroup] = { x = 0, y = 0 }
        if selectedGroup == "shield" then db.width, db.barHeight = defaults.width, defaults.barHeight end
        Layout(); TickPreview(); ShowSettings(selectedGroup)
    end)
    local save = CreateFrame("Button", nil, panel, "UIPanelButtonTemplate")
    panel.saveButton = save
    save:SetSize(124, 26); save:SetPoint("BOTTOMRIGHT", -20, 20)
    save:SetText("Save")
    save:SetScript("OnClick", function() CloseEditMode() end)
    panel:Hide()
end

ShowSettings = function(group)
    if db.locked or InCombatLockdown() then return end
    selectedGroup = group or selectedGroup
    focusedGroup = selectedGroup
    for key, handle in pairs(handles) do
        handle.selection:SetColorTexture(0.65, 0.45, 1, key == focusedGroup and 0.36 or 0.18)
    end
    if not settingsPanel then BuildSettingsPanel() end
    updatingControls = true
    local controls = settingsPanel.controls
    for key, control in pairs(controls) do if control.refresh then control.refresh() end end
    controls.width:SetShown(selectedGroup == "shield")
    controls.barHeight:SetShown(selectedGroup == "shield")
    controls.iconSize:SetShown(selectedGroup == "weakenedSoul")
    controls.showIcon:SetShown(selectedGroup == "weakenedSoul")
    controls.showIcon:SetChecked(db.groupOptions.weakenedSoul.showIcon)
    settingsPanel.subtitle:SetText(selectedGroup == "shield" and "Absorb display" or "Shield Ready")
    updatingControls = false
    settingsPanel:Show()
end

BeginEditing = function(fromEditMode)
    if not initialized or InCombatLockdown() then return end
    editModeActive = fromEditMode and true or false
    db.locked = false
    StartPreview(); Layout()
    ClearGroupFocus()
end

EndEditing = function()
    if not initialized then return end
    editModeActive = false
    db.locked = true
    for _, handle in pairs(handles) do handle:SetScript("OnUpdate", nil); handle:Hide() end
    hud:StopMovingOrSizing(); hud:EnableMouse(false)
    hud.moveHandle:Hide(); hud.moveHint:Hide()
    ClearGroupFocus()
    StopPreview(); Layout()
end

OpenEditMode = function()
    if InCombatLockdown() then Print("Open Edit Mode after combat."); return end
    if not EditModeManagerFrame and C_AddOns and C_AddOns.LoadAddOn then C_AddOns.LoadAddOn("Blizzard_EditMode") end
    if EditModeManagerFrame and EventRegistry and EventRegistry.RegisterCallback then
        ShowUIPanel(EditModeManagerFrame)
        BeginEditing(true)
    else
        BeginEditing(false)
    end
end

CloseEditMode = function()
    if EditModeManagerFrame and EditModeManagerFrame:IsShown() and not InCombatLockdown() then
        HideUIPanel(EditModeManagerFrame)
    end
    EndEditing()
end

SetupEditMode = function()
    if not EventRegistry or not EventRegistry.RegisterCallback then return end
    EventRegistry:RegisterCallback("EditMode.Enter", function() BeginEditing(true) end, hud)
    EventRegistry:RegisterCallback("EditMode.Exit", function() EndEditing() end, hud)
    if EditModeManagerFrame and EditModeManagerFrame:IsShown() then BeginEditing(true) end
end

local function Initialize()
    if initialized then return end
    if select(2, UnitClass("player")) ~= "PRIEST" then return end
    db = type(SoulShieldDB) == "table" and SoulShieldDB or {}
    SoulShieldDB = db
    for key, value in pairs(defaults) do
        if type(db[key]) ~= type(value) then db[key] = value end
    end
    -- Editing is a session action; never reopen a saved sample on login.
    db.locked = true
    db.width = math.max(180, math.min(500, db.width))
    db.barHeight = math.max(12, math.min(40, db.barHeight))
    db.scale = math.max(0.5, math.min(2, db.scale))
    if type(db.groupOptions) ~= "table" then db.groupOptions = {} end
    for group, options in pairs(groupDefaults) do
        if type(db.groupOptions[group]) ~= "table" then db.groupOptions[group] = {} end
        local saved = db.groupOptions[group]
        for key, value in pairs(options) do
            if type(saved[key]) ~= type(value) or (type(value) == "number" and (saved[key] ~= saved[key] or math.abs(saved[key]) > 10000)) then saved[key] = value end
        end
        saved.scale = math.max(0.5, math.min(2, saved.scale))
        saved.fontSize = math.max(9, math.min(28, saved.fontSize))
        if saved.iconSize then saved.iconSize = math.max(12, math.min(40, saved.iconSize)) end
    end
    if type(db.groups) ~= "table" then
        -- Keep each group's main element where it was placed, then restore
        -- consistent internal spacing instead of retaining separate text offsets.
        local previous = type(db.positions) == "table" and db.positions or {}
        db.groups = { weakenedSoul = previous.weakenedLabel, shield = previous.absorb }
    end
    db.positions = nil
    for key in pairs(groups) do
        local position = db.groups[key]
        if type(position) ~= "table" then position = {}; db.groups[key] = position end
        for _, axis in ipairs({ "x", "y" }) do
            local value = position[axis]
            if type(value) ~= "number" or value ~= value or math.abs(value) > 10000 then position[axis] = 0 end
        end
    end
    hud = CreateFrame("Frame", "SoulShieldHUD", UIParent)
    hud:SetFrameStrata("MEDIUM")
    hud:SetMovable(true)
    hud:SetClampedToScreen(true)
    hud:RegisterForDrag("LeftButton")
    hud:SetScript("OnDragStart", function(self)
        if not db.locked and not InCombatLockdown() then self:StartMoving() end
    end)
    hud:SetScript("OnDragStop", function(self)
        self:StopMovingOrSizing()
        local x, y = self:GetCenter()
        -- Frame centers are in their own effective scale coordinate systems.
        local ratio = self:GetEffectiveScale() / UIParent:GetEffectiveScale()
        db.x = x - UIParent:GetWidth() / ratio / 2
        db.y = y - UIParent:GetHeight() / ratio / 2
        Layout()
    end)
    liveRoot = CreateFrame("Frame", nil, hud)
    liveRoot:SetAllPoints(hud)
    auraRoot = CreateFrame("Frame", nil, liveRoot)
    auraRoot:SetAllPoints(hud)
    absorbGate = CreateFrame("StatusBar", nil, liveRoot)
    absorbGate:SetStatusBarTexture(WHITE)
    absorbGate:SetStatusBarColor(1, 1, 1, 0)
    absorbGate:SetMinMaxValues(0, 1)
    absorbGate:SetValue(0)
    local absorbClip = CreateFrame("Frame", nil, absorbGate)
    absorbClip:SetAllPoints(absorbGate:GetStatusBarTexture())
    absorbClip:SetClipsChildren(true)
    bar, absorbLabel, amountText = BuildAbsorb(absorbClip)
    hud.moveHandle = CreateFrame("Frame", nil, hud)
    hud.moveHandle:SetFrameStrata("DIALOG")
    hud.moveHandle:SetSize(280, 20)
    hud.moveHandle:SetPoint("BOTTOM", hud, "TOP", 0, 4)
    hud.moveHandle:EnableMouse(true)
    hud.moveHandle:RegisterForDrag("LeftButton")
    hud.moveHandle:SetScript("OnDragStart", function() hud:GetScript("OnDragStart")(hud) end)
    hud.moveHandle:SetScript("OnDragStop", function() hud:GetScript("OnDragStop")(hud) end)
    hud.moveHint = Text(hud.moveHandle, 10, 0.85, 0.8, 0.95)
    hud.moveHint:SetPoint("CENTER")
    hud.moveHint:SetText("Move entire display  |  Click a group for settings")
    Layout()
    if type(db.reference) == "number" and db.reference > 0 then SetMaximum(db.reference) end
    BuildPreview()
    local ok, failure = pcall(SetupNativeTimers)
    if not ok then
        nativeFailure = tostring(failure)
        auraRoot:Hide()
        shieldButton = nil
        nativeParts = {}
        Print("Absorb bar loaded; timers could not start. Use /soulshield status for details.")
    end
    BuildHandles()
    initialized = true
    Layout()
    UpdateAbsorb()
    SetupEditMode()
end

local events = CreateFrame("Frame")
events:RegisterEvent("PLAYER_LOGIN")
events:RegisterEvent("PLAYER_ENTERING_WORLD")
events:RegisterEvent("PLAYER_REGEN_DISABLED")
events:RegisterEvent("PLAYER_REGEN_ENABLED")
events:RegisterEvent("GLOBAL_MOUSE_DOWN")
events:RegisterUnitEvent("UNIT_ABSORB_AMOUNT_CHANGED", "player")
events:RegisterUnitEvent("UNIT_AURA", "player")
events:RegisterUnitEvent("UNIT_HEALTH", "player")
events:RegisterUnitEvent("UNIT_MAXHEALTH", "player")
-- Absorb events can be absent or arrive before the unit cache has settled.
-- Refresh from the unit API independently of previews and native aura state.
-- Restricted values still go directly to native widgets, never Lua arithmetic.
local refreshElapsed = 0
events:SetScript("OnUpdate", function(_, elapsed)
    if not initialized then return end
    refreshElapsed = refreshElapsed + elapsed
    if refreshElapsed < 0.1 then return end
    refreshElapsed = 0
    UpdateAbsorb()
end)
events:SetScript("OnEvent", function(_, event, argument)
    if event == "PLAYER_LOGIN" then Initialize(); return end
    if not initialized then return end
    if event == "GLOBAL_MOUSE_DOWN" then
        if not focusedGroup or not settingsPanel or not settingsPanel:IsShown() then return end
        -- Interacting with the selected group's controls retains selection.
        if settingsPanel:IsMouseOver() then return end
        -- Let a left-click on either element switch focus on mouse-up.
        if argument == "LeftButton" then
            for _, handle in pairs(handles) do
                if handle:IsShown() and handle:IsMouseOver() then return end
            end
        end
        ClearGroupFocus()
        return
    end
    if event == "PLAYER_REGEN_DISABLED" then
        if editModeActive then EndEditing() else StopPreview() end
        ClearGroupFocus()
        hud:StopMovingOrSizing()
        hud:EnableMouse(false)
        hud.moveHint:Hide()
        hud.moveHandle:Hide()
        for _, handle in pairs(handles) do handle:SetScript("OnUpdate", nil); handle:Hide() end
    elseif event == "PLAYER_REGEN_ENABLED" then
        Layout()
        if not db.locked then StartPreview() end
    end
    UpdateAbsorb()
end)

SLASH_SOULSHIELD1 = "/soulshield"
SLASH_SOULSHIELD2 = "/ss"
SlashCmdList.SOULSHIELD = function(message)
    if not initialized then Print("This tracker is for priest characters on WoW Forever."); return end
    local command, argument = (message or ""):lower():match("^%s*(%S*)%s*(.-)%s*$")
    if command == "status" then
        Print(nativeFailure or "Native timers active. Absorb values include all active shields.")
        return
    end
    if InCombatLockdown() then Print("Change the layout or preview after combat."); return end
    if command == "" or command == "edit" or command == "settings" or command == "unlock" then
        OpenEditMode()
    elseif command == "lock" then
        CloseEditMode()
    elseif command == "test" then
        if not db.locked then Print("Finish Edit Mode, then /ss test for the animated preview.")
        elseif previewStarted then StopPreview() else StartPreview() end
    elseif command == "scale" or command == "width" then
        local value = tonumber(argument)
        local low, high = command == "scale" and 0.5 or 180, command == "scale" and 2 or 500
        if not value or value ~= value or value < low or value > high then
            Print(command .. " must be between " .. low .. " and " .. high .. "."); return
        end
        db[command] = value
        Layout()
    elseif command == "calibrate" then
        StopPreview()
        local amount = UnitGetTotalAbsorbs("player")
        if not Secret(amount) and type(amount) == "number" and amount > 0 then
            SetMaximum(amount)
            db.reference = amount
            previousAmount = amount
            UpdateAbsorb()
            Print("Current absorb is now the full-bar reference.")
        else Print("Apply a fresh shield outside combat, then calibrate.") end
    elseif command == "reset" then
        StopPreview()
        local wasEditing = not db.locked
        for key, value in pairs(defaults) do db[key] = value end
        for key in pairs(groups) do db.groups[key] = { x = 0, y = 0 } end
        for group, options in pairs(groupDefaults) do
            for key, value in pairs(options) do db.groupOptions[group][key] = value end
        end
        Layout()
        if wasEditing then BeginEditing(editModeActive) end
    else
        Print("/ss edit | test | calibrate | reset | status")
    end
end
