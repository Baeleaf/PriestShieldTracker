-- PriestShieldTracker's small, native-fill-driven liquid renderer.
-- Inspired by Smooth Animated Bars / Smooth Experience Bar by Jordan.
-- Borrowed generated textures retain their MIT notice in licenses/SmoothAnimatedBars.txt.
local _, ns = ...
local A = { bars = {}, texts = {} }
ns.Appearance = A
local WHITE = "Interface\\Buttons\\WHITE8x8"
local MEDIA = "Interface\\AddOns\\PriestShieldTracker\\Media\\"
local sin, pi = math.sin, math.pi
local interpolation = Enum and Enum.StatusBarInterpolation and Enum.StatusBarInterpolation.ExponentialEaseOut
local keys = { "absorb", "duration", "background", "labels", "numbers", "ready", "cross" }
A.colorKeys = keys
A.captions = { absorb = "Absorb fill", duration = "Shield timer bar", background = "Bar background",
    labels = "Bar labels", numbers = "Absorb number and shield timer", ready = "Shield Ready and countdown", cross = "Unavailable X" }
A.presetNames = { "Soul", "Holy", "Frost", "Emerald", "Ember", "Void" }
local base = {
    absorb = { 0.55, 0.28, 0.85 }, duration = { 0.63, 0.43, 0.94 }, background = { 0.035, 0.025, 0.055 },
    labels = { 0.9, 0.85, 0.97 }, numbers = { 1, 1, 1 }, ready = { 0.94, 0.88, 0.74 }, cross = { 1, 0.15, 0.15 },
}
local presets = {
    Soul = {},
    Holy = { absorb = { 0.95, 0.65, 0.17 }, duration = { 1, 0.84, 0.4 }, background = { 0.06, 0.04, 0.015 }, labels = { 1, 0.94, 0.77 }, ready = { 1, 0.88, 0.54 } },
    Frost = { absorb = { 0.14, 0.6, 0.88 }, duration = { 0.42, 0.88, 1 }, background = { 0.015, 0.035, 0.06 }, labels = { 0.78, 0.94, 1 }, ready = { 0.63, 0.9, 1 } },
    Emerald = { absorb = { 0.12, 0.65, 0.4 }, duration = { 0.4, 0.95, 0.67 }, background = { 0.015, 0.05, 0.03 }, labels = { 0.8, 1, 0.87 }, ready = { 0.54, 0.96, 0.74 } },
    Ember = { absorb = { 0.88, 0.26, 0.07 }, duration = { 1, 0.59, 0.19 }, background = { 0.06, 0.02, 0.015 }, labels = { 1, 0.87, 0.74 }, ready = { 1, 0.7, 0.39 } },
    Void = { absorb = { 0.37, 0.2, 0.7 }, duration = { 0.74, 0.38, 1 }, background = { 0.025, 0.015, 0.05 }, labels = { 0.88, 0.8, 1 }, ready = { 0.8, 0.65, 1 } },
}
local options
local function Copy(c) return { c[1], c[2], c[3] } end
function A.Init(db)
    if type(db.appearance) ~= "table" then db.appearance = {} end
    options = db.appearance
    if options.style ~= "classic" and options.style ~= "smooth" and options.style ~= "liquid" then options.style = "liquid" end
    if type(options.colors) ~= "table" then options.colors = {} end
    if not presets[options.preset] and options.preset ~= "Custom" then options.preset = "Soul" end
    for _, key in ipairs(keys) do
        local c = options.colors[key]
        local valid = type(c) == "table"
        if valid then
            for i = 1, 3 do
                if type(c[i]) ~= "number" or c[i] ~= c[i] or c[i] < 0 or c[i] > 1 then valid = false end
            end
        end
        if not valid then options.colors[key] = Copy(base[key]) end
    end
end
function A.Color(key) return unpack(options.colors[key]) end
function A.Preset(name)
    if not presets[name] then return end
    for _, key in ipairs(keys) do options.colors[key] = Copy(presets[name][key] or base[key]) end
    options.preset = name
    A.Apply()
end
function A.Text(region, key)
    A.texts[#A.texts + 1] = { region = region, key = key }
    region:SetTextColor(A.Color(key))
end
local function Texture(parent, layer, sublevel, file, blend)
    local t = parent:CreateTexture(nil, layer, nil, sublevel)
    if file then t:SetTexture(MEDIA .. file, "REPEAT", "REPEAT") else t:SetTexture(WHITE) end
    if blend then t:SetBlendMode(blend) end
    return t
end

function A.Attach(status, key)
    status.colorKey = key
    A.bars[#A.bars + 1] = status
    if key ~= "absorb" then A.StyleBar(status); return end
    local clip = CreateFrame("Frame", nil, status)
    clip:SetFrameLevel(status:GetFrameLevel() + 1)
    clip:SetAllPoints(status)
    clip:SetClipsChildren(true)
    local mover = CreateFrame("Frame", nil, clip)
    -- The CLIENT places the edge. Never inspect this fill's coordinates, size or value.
    mover:SetPoint("TOPRIGHT", status:GetStatusBarTexture(), "TOPRIGHT")
    mover:SetPoint("BOTTOMRIGHT", status:GetStatusBarTexture(), "BOTTOMRIGHT")
    local fx = { clip = clip, mover = mover, rows = {}, bubbles = {}, clock = 0, elapsed = 0 }
    status.liquid = fx
    for i = 1, 12 do
        local row = Texture(mover, "ARTWORK", 0)
        local tip = Texture(mover, "ARTWORK", 5, "Edge", "ADD")
        fx.rows[i] = { body = row, tip = tip }
    end
    fx.cloud = Texture(mover, "ARTWORK", 1, "Nebula", "ADD")
    fx.swirl = Texture(mover, "ARTWORK", 2, "Swirl", "ADD")
    fx.core = Texture(mover, "ARTWORK", 3, "Core", "ADD")
    for _, texture in ipairs({ fx.cloud, fx.swirl, fx.core }) do texture:SetAllPoints(mover) end
    for i = 1, 6 do fx.bubbles[i] = Texture(mover, "ARTWORK", 4, "Bubble", "ADD") end
    clip:SetScript("OnUpdate", function(_, dt)
        fx.elapsed = fx.elapsed + dt
        if fx.elapsed < 1 / 30 then return end
        fx.clock = (fx.clock + math.min(fx.elapsed, 0.1)) % 3600
        fx.elapsed = 0
        local time, w, h = fx.clock, fx.width, fx.height
        if not w then return end
        for i, row in ipairs(fx.rows) do
            local y = (i - 0.5) / #fx.rows
            local offset = (sin(time * 2.2 + y * pi * 2) + sin(time * 3.4 - y * pi * 3) * 0.4) * h * 0.075
            row.body:SetWidth(w + offset)
            row.tip:ClearAllPoints()
            row.tip:SetPoint("CENTER", mover, "TOPRIGHT", offset, -(i - 0.5) * h / #fx.rows)
        end
        local u, v = time * 0.035 % 1, time * 0.018 % 1
        fx.cloud:SetTexCoord(u, u + w / 256, v, v + 1)
        fx.swirl:SetTexCoord(-u, -u + w / 180, -v, -v + 1)
        fx.core:SetAlpha(0.28 + sin(time * 1.4) * 0.07)
        for i, bubble in ipairs(fx.bubbles) do
            local progress = (time * (0.11 + i * 0.012) + i * 0.17) % 1
            local x = w * ((i * 0.153 + time * 0.006) % 1) + sin(time + i) * 2
            bubble:ClearAllPoints()
            bubble:SetPoint("CENTER", mover, "BOTTOMLEFT", x, progress * h)
            bubble:SetAlpha(sin(progress * pi) * 0.35)
        end
    end)
    A.StyleBar(status)
end

function A.Layout(status, width, height)
    local fx = status.liquid
    if not fx then return end
    fx.width, fx.height = width, height
    fx.mover:SetWidth(width)
    for i, row in ipairs(fx.rows) do
        row.body:ClearAllPoints()
        row.body:SetPoint("TOPLEFT", fx.mover, "TOPLEFT", 0, -(i - 1) * height / #fx.rows)
        row.body:SetSize(width, height / #fx.rows + 0.3)
        row.tip:SetSize(5, height / #fx.rows + 0.3)
    end
    for i, bubble in ipairs(fx.bubbles) do bubble:SetSize(2 + i % 3, 2 + i % 3) end
end

function A.SetValue(status, value)
    if options.style ~= "classic" and interpolation then status:SetValue(value, interpolation)
    else status:SetValue(value) end
end

function A.StyleBar(status)
        if not ns.CanAccessRegion(status) then A.pending = true; return end
        local r, g, b = A.Color(status.colorKey)
        local liquid = status.liquid and options.style == "liquid"
        status:SetStatusBarColor(r, g, b, liquid and 0 or 1)
        if status.background then
            local br, bg, bb = A.Color("background")
            status.background:SetColorTexture(br, bg, bb, 0.85)
        end
        if status.edge then status.edge:SetShown(not liquid) end
        local fx = status.liquid
        if fx then
            fx.clip:SetShown(liquid and true or false)
            for _, row in ipairs(fx.rows) do
                row.body:SetVertexColor(r, g, b, 1)
                row.tip:SetVertexColor(0.6 + r * 0.4, 0.6 + g * 0.4, 0.6 + b * 0.4, 0.9)
            end
            fx.cloud:SetVertexColor(r * 0.7, g * 0.7, b * 0.7, 0.4)
            fx.swirl:SetVertexColor(0.4 + r * 0.6, 0.4 + g * 0.6, 0.4 + b * 0.6, 0.32)
            fx.core:SetVertexColor(r, g, b, 0.35)
            for _, bubble in ipairs(fx.bubbles) do bubble:SetVertexColor(0.5 + r * 0.5, 0.5 + g * 0.5, 0.5 + b * 0.5) end
        end
end

function A.Apply()
    -- Aura access can stay restricted out of combat in instances, too.
    if InCombatLockdown() then A.pending = true; return end
    A.pending = false
    for _, entry in ipairs(A.texts) do
        if ns.CanAccessRegion(entry.region) then entry.region:SetTextColor(A.Color(entry.key))
        else A.pending = true end
    end
    for _, status in ipairs(A.bars) do A.StyleBar(status) end
end
