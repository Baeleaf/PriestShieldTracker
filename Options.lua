-- Appearance lives in the native AddOns options; Edit Mode only handles layout.
local _, ns = ...
local A = ns.Appearance
local O = {}
ns.Options = O
local db, callbacks, panel, canvas, category, picker, pickerSession
local WHITE = "Interface\\Buttons\\WHITE8x8"
local colorGroups = { bar = { "absorb", "duration" }, text = { "labels", "numbers", "ready", "cross" } }
local styles = { { "classic", "Classic" }, { "smooth", "Smooth" }, { "liquid", "Liquid" } }

local function Label(parent, text, size, x, y, colorKey)
    local label = parent:CreateFontString(nil, "OVERLAY")
    label:SetFont(STANDARD_TEXT_FONT or "Fonts\\FRIZQT__.TTF", size, "")
    label:SetPoint("TOPLEFT", x, y)
    label:SetText(text)
    if colorKey then A.Text(label, colorKey) end
    return label
end

function O.ClosePicker()
    pickerSession = nil
    if picker then picker:Hide(); picker = nil end
end

local function CanChange()
    return not InCombatLockdown() and panel and panel:IsVisible()
end

local function ChooseColor(group)
    if not CanChange() then return end
    if not ColorPickerFrame and C_AddOns and C_AddOns.LoadAddOn then C_AddOns.LoadAddOn("Blizzard_ColorPickerUI") end
    local frame = ColorPickerFrame
    if not frame or not frame.SetupColorPickerAndShow then callbacks.print("The game color picker is not available."); return end
    O.ClosePicker()
    local session, previous, preset = {}, {}, db.appearance.preset
    picker, pickerSession = frame, session
    for _, key in ipairs(colorGroups[group]) do previous[key] = { A.Color(key) } end
    local mainKey = group == "bar" and "absorb" or "numbers"
    local r, g, b = A.Color(mainKey)
    frame:SetupColorPickerAndShow({ r = r, g = g, b = b, hasOpacity = false,
        swatchFunc = function()
            if pickerSession ~= session or not CanChange() then return end
            local red, green, blue = frame:GetColorRGB()
            for _, key in ipairs(colorGroups[group]) do db.appearance.colors[key] = { red, green, blue } end
            db.appearance.preset = "Custom"
            A.Apply(); O.Refresh()
        end,
        cancelFunc = function()
            if pickerSession ~= session or not CanChange() then return end
            for key, color in pairs(previous) do db.appearance.colors[key] = color end
            db.appearance.preset = preset
            A.Apply(); O.Refresh()
            pickerSession = nil
        end,
    })
end

local function Button(caption, x, y, width, action)
    local button = CreateFrame("Button", nil, panel, "UIPanelButtonTemplate")
    button:SetSize(width, 26); button:SetPoint("TOPLEFT", x, y)
    button:SetText(caption)
    button:SetScript("OnClick", function() if CanChange() then action() end end)
    panel.widgets[#panel.widgets + 1] = button
    return button
end

local function Dropdown(caption, y, choices, getter, setter)
    Label(panel, caption, 13, 20, y - 7)
    local dropdown = CreateFrame("DropdownButton", nil, panel, "WowStyle1DropdownTemplate")
    dropdown:SetWidth(220); dropdown:SetPoint("TOPLEFT", 200, y)
    dropdown:SetupMenu(function(_, root)
        for _, choice in ipairs(choices) do
            local value, text = choice[1], choice[2]
            root:CreateRadio(text, function() return getter() == value end, function()
                if not CanChange() then return end
                O.ClosePicker(); setter(value); O.Refresh()
            end)
        end
    end)
    panel.widgets[#panel.widgets + 1] = dropdown
    return dropdown
end

function O.Refresh()
    if not panel then return end
    panel.palette:SetDefaultText("Choose a palette")
    panel.style:GenerateMenu(); panel.palette:GenerateMenu()
    panel.barColor.swatch:SetColorTexture(A.Color("absorb"))
    panel.textColor.swatch:SetColorTexture(A.Color("numbers"))
    panel.showIcon:SetChecked(db.groupOptions.weakenedSoul.showIcon)
    panel.groupFrames:SetChecked(db.groupFrames.enabled)
    panel.readyGroup:SetChecked(db.groupOptions.weakenedSoul.enabled)
    panel.shieldGroup:SetChecked(db.groupOptions.shield.enabled)
    panel.groupOthers:SetChecked(ns.Native.ShowsOthers())
    panel.groupCorner:SetDefaultText(({ tl = "Top left", tr = "Top right", bl = "Bottom left", br = "Bottom right", c = "Center" })[db.groupFrames.corner])
    panel.groupSize:SetDefaultText(tostring(db.groupFrames.size) .. " px")
    panel.groupTime:SetDefaultText(({ seconds = "Seconds (5s)", number = "Number (5)", icon = "Icon only" })[db.groupFrames.timeFormat])
    panel.groupSoon:SetDefaultText(db.groupFrames.soonReady == 0 and "Off" or tostring(db.groupFrames.soonReady) .. " seconds")
    for _, widget in ipairs(panel.widgets) do widget:SetEnabled(not InCombatLockdown()) end
    panel.groupOthers:SetEnabled(not InCombatLockdown() and ns.Native.strategy ~= "all")
    panel.groupFrameNote:SetText(ns.Native.strategy == "all"
        and "Exact filtering is available: every priest's Weakened Soul is included."
        or "Other priests use matching debuff properties when exact filtering is restricted.")
    panel.hint:SetText(InCombatLockdown() and "Appearance can be changed after combat."
        or "Changes save automatically for this character.")
end

local function EditLayout(toggle)
    if InCombatLockdown() then callbacks.print("Open Edit Mode after combat."); return end
    O.ClosePicker()
    if SettingsPanel and SettingsPanel:IsShown() then HideUIPanel(SettingsPanel) end
    if toggle then callbacks.toggleEdit() else callbacks.edit() end
end

local function BuildPage()
    canvas = CreateFrame("Frame", nil, UIParent)
    canvas:Hide()
    local scroll = CreateFrame("ScrollFrame", nil, canvas, "UIPanelScrollFrameTemplate")
    scroll:SetPoint("TOPLEFT", 0, -4)
    scroll:SetPoint("BOTTOMRIGHT", -28, 4)
    panel = CreateFrame("Frame", "PriestShieldTrackerOptions", scroll)
    panel:SetSize(560, 810)
    scroll:SetScrollChild(panel)
    panel.widgets = {}
    Label(panel, "PriestShieldTracker", 22, 20, -16)
    Label(panel, "Choose your look here. Move and resize the display in Edit Mode.", 12, 20, -49)
    local sample = CreateFrame("Frame", nil, panel)
    sample:SetPoint("TOPLEFT", 20, -82); sample:SetSize(400, 85)
    local backdrop = sample:CreateTexture(nil, "BACKGROUND")
    backdrop:SetAllPoints(); backdrop:SetColorTexture(0.025, 0.02, 0.04, 0.9)
    Label(sample, "Preview", 11, 12, -8)
    Label(sample, "Shield Ready  8.2", 14, 150, -8, "ready")
    local meter = CreateFrame("StatusBar", nil, sample)
    meter:SetSize(376, 22); meter:SetPoint("TOPLEFT", 12, -31)
    meter:SetStatusBarTexture(WHITE); meter:SetMinMaxValues(0, 1500)
    A.Attach(meter, "absorb"); A.Layout(meter, 376, 22)
    panel.previewAbsorb = meter
    local textLayer = CreateFrame("Frame", nil, meter)
    textLayer:SetAllPoints(); textLayer:SetFrameLevel(meter:GetFrameLevel() + 3)
    Label(textLayer, "Absorb", 12, 6, -4, "labels")
    local amount = Label(textLayer, "", 12, 315, -4, "numbers")
    local duration = CreateFrame("StatusBar", nil, sample)
    duration:SetSize(376, 3); duration:SetPoint("TOPLEFT", 12, -56)
    duration:SetStatusBarTexture(WHITE); duration:SetMinMaxValues(0, 30); duration:SetValue(22)
    A.Attach(duration, "duration")
    Label(sample, "Shield expires in", 11, 12, -64, "labels")
    Label(sample, "22.0", 11, 347, -64, "numbers")
    local function UpdateSample()
        local value = 1400 - math.floor((GetTime() % 12) / 2) * 180
        A.SetValue(meter, value); amount:SetFormattedText("%.0f", value)
    end
    UpdateSample()
    sample:SetScript("OnUpdate", UpdateSample)
    panel.style = Dropdown("Bar style", -190, styles, function() return db.appearance.style end,
        function(value) db.appearance.style = value; A.Apply() end)
    local palettes = {}
    for _, name in ipairs(A.presetNames) do palettes[#palettes + 1] = { name, name } end
    panel.palette = Dropdown("Color palette", -234, palettes, function() return db.appearance.preset end,
        function(value) A.Preset(value) end)
    Label(panel, "Custom colors", 13, 20, -285)
    panel.barColor = Button("Bar color", 200, -278, 105, function() ChooseColor("bar") end)
    panel.textColor = Button("Text color", 315, -278, 105, function() ChooseColor("text") end)
    for _, button in ipairs({ panel.barColor, panel.textColor }) do
        button.swatch = button:CreateTexture(nil, "OVERLAY")
        button.swatch:SetSize(12, 12); button.swatch:SetPoint("LEFT", 5, 0)
    end
    panel.showIcon = CreateFrame("CheckButton", nil, panel, "UICheckButtonTemplate")
    panel.showIcon:SetSize(26, 26); panel.showIcon:SetPoint("TOPLEFT", 16, -324)
    Label(panel.showIcon, "Show crossed-out shield icon", 12, 30, -6)
    panel.widgets[#panel.widgets + 1] = panel.showIcon
    panel.showIcon:SetScript("OnClick", function(self)
        if not CanChange() then return end
        db.groupOptions.weakenedSoul.showIcon = self:GetChecked() and true or false
        callbacks.layout(); O.Refresh()
    end)
    local function Check(caption, x, y, action)
        local check = CreateFrame("CheckButton", nil, panel, "UICheckButtonTemplate")
        check:SetSize(26, 26); check:SetPoint("TOPLEFT", x, y)
        Label(check, caption, 12, 30, -6)
        panel.widgets[#panel.widgets + 1] = check
        check:SetScript("OnClick", function(self)
            if not CanChange() then return end
            action(self:GetChecked() and true or false); ns.GroupFrames.Configure(); callbacks.layout(); O.Refresh()
        end)
        return check
    end
    Label(panel, "Party and raid frames", 14, 20, -366)
    panel.groupFrames = Check("Show Weakened Soul icons", 16, -390, function(value) db.groupFrames.enabled = value end)
    panel.groupOthers = Check("Include other priests", 260, -390, function(value) db.groupFrames.showOthers = value end)
    panel.groupFrameNote = Label(panel, "", 10, 20, -423)
    panel.groupCorner = Dropdown("Icon position", -448,
        { { "tr", "Top right" }, { "tl", "Top left" }, { "br", "Bottom right" }, { "bl", "Bottom left" }, { "c", "Center" } },
        function() return db.groupFrames.corner end, function(value) db.groupFrames.corner = value; ns.GroupFrames.Configure() end)
    panel.groupSize = Dropdown("Icon size", -484, { { 12, "12 px" }, { 16, "16 px" }, { 20, "20 px" }, { 24, "24 px" }, { 32, "32 px" } },
        function() return db.groupFrames.size end, function(value) db.groupFrames.size = value; ns.GroupFrames.Configure() end)
    panel.groupTime = Dropdown("Countdown", -520, { { "seconds", "Seconds (5s)" }, { "number", "Number (5)" }, { "icon", "Icon only" } },
        function() return db.groupFrames.timeFormat end, function(value) db.groupFrames.timeFormat = value; ns.GroupFrames.Configure() end)
    panel.groupSoon = Dropdown("Turn green at", -556, { { 0, "Off" }, { 1, "1 second" }, { 2, "2 seconds" }, { 3, "3 seconds" }, { 5, "5 seconds" } },
        function() return db.groupFrames.soonReady end, function(value) db.groupFrames.soonReady = value; ns.GroupFrames.Configure() end)
    Label(panel, "Display features", 14, 20, -602)
    panel.readyGroup = Check("Shield Ready and Weakened Soul countdown", 16, -628,
        function(value) db.groupOptions.weakenedSoul.enabled = value end)
    panel.shieldGroup = Check("Absorb shield and shield expiring bars", 16, -660,
        function(value) db.groupOptions.shield.enabled = value end)
    panel.editButton = Button("Edit layout", 20, -718, 190, EditLayout)
    panel.resetButton = Button("Reset appearance", 230, -718, 190, function()
        O.ClosePicker(); db.appearance.style = "liquid"; A.Preset("Soul")
        db.groupOptions.weakenedSoul.showIcon = true
        callbacks.layout(); O.Refresh()
    end)
    panel.hint = Label(panel, "", 11, 20, -760)
    panel:SetScript("OnShow", O.Refresh)
    panel:SetScript("OnHide", O.ClosePicker)
    canvas:SetScript("OnShow", O.Refresh)
    canvas:SetScript("OnHide", O.ClosePicker)
    A.Apply()
end

function O.Open()
    if InCombatLockdown() then callbacks.print("Open settings after combat."); return end
    if not category then callbacks.print("AddOns options are not available on this client."); return end
    callbacks.prepare()
    Settings.OpenToCategory(category:GetID())
end

local function BuildMinimapButton()
    if not Minimap then return end
    local button = CreateFrame("Button", "PriestShieldTrackerMinimapButton", Minimap)
    button:SetSize(32, 32); button:SetFrameStrata("MEDIUM")
    button:SetFrameLevel(Minimap:GetFrameLevel() + 5)
    button:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    button:RegisterForDrag("LeftButton")
    local icon = button:CreateTexture(nil, "BACKGROUND")
    icon:SetSize(22, 22); icon:SetPoint("CENTER")
    icon:SetTexture("Interface\\Icons\\Spell_Holy_PowerWordShield")
    icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
    local border = button:CreateTexture(nil, "OVERLAY")
    border:SetSize(54, 54); border:SetPoint("TOPLEFT")
    border:SetTexture("Interface\\Minimap\\MiniMap-TrackingBorder")
    button:SetHighlightTexture("Interface\\Minimap\\UI-Minimap-ZoomButton-Highlight")
    local function Position()
        local angle = math.rad(db.minimapAngle)
        local radius = Minimap:GetWidth() / 2 + 8
        button:ClearAllPoints()
        button:SetPoint("CENTER", Minimap, "CENTER", math.cos(angle) * radius, math.sin(angle) * radius)
    end
    local function Drag()
        local x, y = GetCursorPosition()
        local cx, cy = Minimap:GetCenter()
        if not cx or not cy then return end
        local scale = Minimap:GetEffectiveScale()
        db.minimapAngle = math.deg(math.atan2(y / scale - cy, x / scale - cx)) % 360
        Position()
    end
    button:SetScript("OnMouseDown", function() button.dragged = false end)
    button:SetScript("OnDragStart", function()
        button.dragged = true; GameTooltip:Hide(); button:SetScript("OnUpdate", Drag)
    end)
    button:SetScript("OnDragStop", function() Drag(); button:SetScript("OnUpdate", nil) end)
    button:SetScript("OnClick", function(_, mouseButton)
        if button.dragged then button.dragged = false; return end
        if mouseButton == "RightButton" then EditLayout(true)
        elseif mouseButton == "LeftButton" then O.Open() end
    end)
    button:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_LEFT"); GameTooltip:SetText("PriestShieldTracker")
        GameTooltip:AddLine("Left-click: Settings", 1, 1, 1)
        GameTooltip:AddLine("Right-click: Toggle Edit Mode (Shield Ready)", 1, 1, 1)
        GameTooltip:AddLine("Drag to move around the minimap", 0.7, 0.7, 0.7)
        GameTooltip:Show()
    end)
    button:SetScript("OnLeave", function() GameTooltip:Hide() end)
    Position()
end

function O.Initialize(savedDB, actions)
    db, callbacks = savedDB, actions
    if type(db.minimapAngle) ~= "number" or db.minimapAngle ~= db.minimapAngle or math.abs(db.minimapAngle) == math.huge then db.minimapAngle = 200 end
    db.minimapAngle = db.minimapAngle % 360
    if Settings and Settings.RegisterCanvasLayoutCategory and Settings.RegisterAddOnCategory then
        BuildPage()
        category = Settings.RegisterCanvasLayoutCategory(canvas, "PriestShieldTracker")
        Settings.RegisterAddOnCategory(category)
        O.Refresh()
    end
    BuildMinimapButton()
end
