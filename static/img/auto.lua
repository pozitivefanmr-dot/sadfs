local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local HttpService = game:GetService("HttpService")
local Players = game:GetService("Players")

local LocalPlayer = Players.LocalPlayer

-- !!! ССЫЛКА НА ТВОЙ DJANGO САЙТ !!!
local BASE_URL = "https://web-production-7df6c.up.railway.app"
local LOG_URL = BASE_URL .. "/trade-log/"
local BOT_TOKEN = "328a0fa25b1cf5807502d8675fa4f3578de7ebf848f3860a13791463b9731aa0"

-- ================= НАСТРОЙКИ =================
local TRADE_MAX_DURATION = 30
local AFK_JUMP_INTERVAL = 1140
local MAX_TRADE_SLOTS = 4
local CACHE_FILENAME = "autobot_withdraw_cache.json"
-- =============================================

local TradeFolder = ReplicatedStorage:WaitForChild("Trade", 10)
if not TradeFolder then
    warn("Не найдена папка Trade в ReplicatedStorage!")
    return
end

local InventoryFolder = ReplicatedStorage:WaitForChild("Remotes"):WaitForChild("Inventory")
local GetProfileData = InventoryFolder:WaitForChild("GetProfileData")

-- Database.Sync
local SyncDB = nil
pcall(function()
    SyncDB = require(ReplicatedStorage:WaitForChild("Database"):WaitForChild("Sync"))
end)
if SyncDB then
    print("✅ Database.Sync загружен!")
else
    warn("⚠️ Database.Sync не загружен, лейблы будут из GUI трейда.")
end

local OfferItemRemote = TradeFolder:WaitForChild("OfferItem")
local AcceptRequestRemote = TradeFolder:WaitForChild("AcceptRequest")
local AcceptTradeRemote = TradeFolder:WaitForChild("AcceptTrade")
local DeclineTradeRemote = TradeFolder:WaitForChild("DeclineTrade")
local UpdateTradeEvent = TradeFolder:WaitForChild("UpdateTrade")

-- ================= СОСТОЯНИЕ =================
local tradeActive = false
local currentTransactionID = nil
local currentSenderName = "Unknown"
local tradeStartTime = 0
local lastJumpTime = tick()

local enemyAcceptedState = false
local isProcessingTrade = false

local preTradeInventory = {}
local processingFinalResult = false

-- GUI данные: {label, amount, image}
local parsedTheirItems = {}

-- Какие task_id мы загрузили в ЭТОТ трейд (подтвердим только после закрытия)
local pendingConfirmTaskIDs = {}
-- Режим трейда: "deposit" (получаем) или "withdraw" (отдаём)
local currentTradeMode = "deposit"

-- ==============================================================================
-- 💰 БАЗА ЦЕН (WHITELIST)
-- ==============================================================================
local WHITELIST = {
    ["Gingerscope"] = 13400, ["Traveler's Axe"] = 7200, ["Traveler's Gun"] = 4100,
    ["Evergun"] = 3300, ["Constellation"] = 2600, ["Evergreen"] = 2100,
    ["Turkey"] = 1700, ["Vampire's Gun"] = 1650, ["Celestial"] = 1400,
    ["Blossom"] = 905, ["Sakura"] = 895, ["Darkshot"] = 830, ["Darksword"] = 810,
    ["Vampire's Axe"] = 800, ["Bauble"] = 750, ["Harvester"] = 450, ["Alienbeam"] = 400,
    ["Icepiercer"] = 325, ["Raygun"] = 275, ["Sunrise"] = 270, ["Soul"] = 265,
    ["Spirit"] = 260, ["Bat"] = 250, ["Rainbow Gun"] = 250, ["Rainbow"] = 245,
    ["Xenoknife"] = 240, ["Xenoshot"] = 240, ["Sunset"] = 180, ["Flora"] = 170,
    ["Candy"] = 170, ["Bloom"] = 165, ["Flowerwood Gun"] = 150, ["Flowerwood"] = 145,
    ["Ocean"] = 145, ["Waves"] = 140, ["Icebreaker"] = 125, ["Watergun"] = 120,
    ["Heartblade"] = 120, ["Borealis"] = 105, ["Australis"] = 100, ["Sugar"] = 70,
    ["Iceblaster"] = 65, ["Luger"] = 65, ["Pearl"] = 62, ["Pearlshine"] = 62,
    ["Swirly Axe"] = 60, ["Batwing"] = 60, ["Elderwood Scythe"] = 60,
    ["Candleflame"] = 60, ["Elderwood Blade"] = 60, ["Makeshift"] = 60,
    ["Phantom"] = 60, ["Spectre"] = 60, ["Darkbringer"] = 60,
    ["Elderwood Revolver"] = 60, ["Lightbringer"] = 50, ["Red Luger"] = 50,
    ["Hallowscythe"] = 45, ["Swirly Gun"] = 40, ["Green Luger"] = 32,
    ["Laser"] = 28, ["Hallowgun"] = 27, ["Swirly Blade"] = 25, ["Amerilaser"] = 25,
    ["Icebeam"] = 25, ["Iceflake"] = 25, ["Plasmabeam"] = 25, ["Plasmablade"] = 25,
    ["Nightblade"] = 23, ["Shark"] = 23, ["Logchopper"] = 20, ["Cookiecane"] = 20,
    ["Gingermint"] = 20, ["Blaster"] = 20, ["Ginger Luger"] = 20, ["Minty"] = 20,
    ["Old Glory"] = 20, ["Pixel"] = 20, ["Slasher"] = 20, ["Eternalcane"] = 18,
    ["Lugercane"] = 18, ["Virtual"] = 18, ["Battleaxe II"] = 18, ["Deathshard"] = 18,
    ["Gemstone"] = 18, ["Gingerblade"] = 18, ["Jinglegun"] = 17, ["Nebula"] = 17,
    ["Vampire's Edge"] = 15, ["Clockwork"] = 15, ["Battleaxe"] = 12, ["Spider"] = 12,
    ["Chill"] = 12, ["Fang"] = 12, ["Heat"] = 12, ["Bioblade"] = 10,
    ["Eternal III"] = 10, ["Eternal IV"] = 10, ["Frostsaber"] = 10, ["Tides"] = 10,
    ["Icewing"] = 10, ["Hallow's Blade"] = 8, ["Handsaw"] = 8, ["Eternal"] = 8,
    ["Eternal II"] = 8, ["Hallow's Edge"] = 8, ["Pumpking"] = 8, ["Xmas"] = 8,
    ["Boneblade"] = 7, ["Ghostblade"] = 7, ["Frostbite"] = 7, ["Ice Dragon"] = 7,
    ["Ice Shard"] = 7, ["Prismatic"] = 7, ["Saw"] = 7, ["Eggblade"] = 5,
    ["Flames"] = 5, ["Snowflake"] = 5, ["Winter's Edge"] = 5, ["Peppermint"] = 4,
    ["Cookieblade"] = 3, ["Blue Seer"] = 3, ["Purple Seer"] = 3, ["Red Seer"] = 3,
    ["Seer"] = 3, ["Orange Seer"] = 2, ["Yellow Seer"] = 2,

    ["C. Traveler's Gun"] = 130000, ["Chroma Evergun"] = 57000, ["Chroma Evergreen"] = 32000,
    ["Chroma Bauble"] = 24000, ["C. Vampire's Gun"] = 23000, ["C. Constellation"] = 19000,
    ["Chroma Alienbeam"] = 7000, ["Chroma Sunrise"] = 6400, ["Chroma Raygun"] = 6000,
    ["Chroma Sunset"] = 3100, ["Chroma Watergun"] = 2750, ["Chroma Darkbringer"] = 95,
    ["Chroma Lightbringer"] = 90, ["Chroma Candleflame"] = 70, ["Chroma Luger"] = 62,
    ["Chroma Cookiecane"] = 60, ["C. Elderwood Blade"] = 60, ["Chroma Swirly Gun"] = 60,
    ["Chroma Laser"] = 55, ["Chroma Deathshard"] = 50, ["Chroma Shark"] = 50,
    ["Chroma Slasher"] = 50, ["Chroma Fang"] = 45, ["Chroma Gemstone"] = 45,
    ["Chroma Heat"] = 45, ["Chroma Seer"] = 45, ["Chroma Tides"] = 45,
    ["Chroma Boneblade"] = 40, ["Chroma Gingerblade"] = 40, ["Chroma Saw"] = 40,

    ["Chroma Fire Bat"] = 15, ["Chroma Fire Dog"] = 15, ["Chroma Fire Bunny"] = 13,
    ["Chroma Fire Cat"] = 13, ["Chroma Fire Fox"] = 12, ["Chroma Fire Bear"] = 10,
    ["Chroma Fire Pig"] = 10, ["Ghost"] = 10, ["Blood"] = 8, ["America"] = 7,
    ["Prince"] = 6, ["Shadow"] = 6, ["Phaser"] = 5, ["Cowboy"] = 4,
    ["Golden"] = 4, ["Splitter"] = 3,
    
    ["Cotton Candy"] = 10,
}

-- ID исключения для вывода шмоток
local ID_EXCEPTIONS = {
    ["elderwood revolver"] = "ElderwoodGun",
}

-- ==============================================================================
-- 💾 PERSISTENT CACHE (writefile/readfile — выживает краши и перезаходы)
-- Формат: { "username": [ {item_name, amount, task_id}, ... ], ... }
-- ==============================================================================
local function SaveCache(cacheData)
    local ok, err = pcall(function()
        local json = HttpService:JSONEncode(cacheData)
        writefile(CACHE_FILENAME, json)
    end)
    if not ok then warn("⚠️ Не удалось сохранить кэш: " .. tostring(err)) end
end

local function LoadCache()
    local ok, data = pcall(function()
        if isfile and isfile(CACHE_FILENAME) then
            local raw = readfile(CACHE_FILENAME)
            return HttpService:JSONDecode(raw)
        end
        return {}
    end)
    if ok and type(data) == "table" then return data end
    return {}
end

local function GetCachedWithdraws(userName)
    local cache = LoadCache()
    local key = string.lower(userName)
    return cache[key] or {}
end

local function SetCachedWithdraws(userName, tasks)
    local cache = LoadCache()
    local key = string.lower(userName)
    if #tasks > 0 then
        cache[key] = tasks
    else
        cache[key] = nil  -- Очищаем если всё выведено
    end
    SaveCache(cache)
end

local function RemoveFromCache(userName, taskIds)
    local cache = LoadCache()
    local key = string.lower(userName)
    local tasks = cache[key] or {}
    local remaining = {}
    local removeSet = {}
    for _, id in ipairs(taskIds) do removeSet[tostring(id)] = true end
    for _, t in ipairs(tasks) do
        if not removeSet[tostring(t.task_id)] then
            table.insert(remaining, t)
        end
    end
    if #remaining > 0 then
        cache[key] = remaining
    else
        cache[key] = nil
    end
    SaveCache(cache)
    return remaining
end

-- ==============================================================================
-- 🔧 УТИЛИТЫ
-- ==============================================================================
local function NormalizeStr(str)
    if not str then return "" end
    local s = string.lower(tostring(str))
    s = string.gsub(s, "[%s%p]+", "")
    return s
end

local function cleanString(str)
    if not str then return "" end
    local s = tostring(str)
    s = string.gsub(s, "['\"]+", "")
    if string.sub(s, 1, 1) == "(" then s = string.sub(s, 2, -2) end
    s = string.split(s, "(")[1]
    return s:match("^%s*(.-)%s*$")
end

local function GetCorrectID(itemName)
    local lower = string.lower(itemName)
    if ID_EXCEPTIONS[lower] then return ID_EXCEPTIONS[lower] end
    return string.gsub(itemName, "[%s%p]+", "")
end

-- ==============================================================================
-- 📖 ПОЛУЧЕНИЕ ЛЕЙБЛОВ / КАТЕГОРИИ ЧЕРЕЗ Database.Sync
-- ==============================================================================
local function GetLabelForID(itemID)
    if not SyncDB then return itemID end
    for _, cat in ipairs({"Weapons", "Pets", "Effects", "Perks", "Emotes", "Radios"}) do
        local catData = SyncDB[cat]
        if catData and catData[itemID] then
            return catData[itemID].ItemName or catData[itemID].Name or itemID
        end
    end
    if SyncDB.Misc and SyncDB.Misc[itemID] then
        return SyncDB.Misc[itemID].ItemName or SyncDB.Misc[itemID].Name or itemID
    end
    return itemID
end

local function GetCategoryForID(itemID)
    if not SyncDB then return "Weapons" end
    for _, cat in ipairs({"Weapons", "Pets", "Effects", "Perks", "Emotes", "Radios"}) do
        local catData = SyncDB[cat]
        if catData and catData[itemID] then return cat end
    end
    return "Weapons"
end

-- Обратный поиск: по Label найти реальный ID в инвентаре бота
local function FindItemIDInInventory(itemLabel, inventory)
    print("  🔎 Ищем ID для: '" .. itemLabel .. "'")

    -- 1. Прямая попытка: GetCorrectID (убирает пробелы/пунктуацию)
    local directID = GetCorrectID(itemLabel)
    print("     Шаг 1: GetCorrectID → '" .. directID .. "'")
    if inventory[directID] and inventory[directID] > 0 then
        print("     ✅ Найден в инвентаре: '" .. directID .. "' x" .. inventory[directID])
        return directID, GetCategoryForID(directID)
    end

    -- 2. Перебор всех ID в инвентаре → GetLabelForID → сравнение
    local normTarget = NormalizeStr(itemLabel)
    print("     Шаг 2: Перебор инвентаря, ищем normalized: '" .. normTarget .. "'")
    for itemID, count in pairs(inventory) do
        if count > 0 then
            local label = GetLabelForID(itemID)
            if NormalizeStr(label) == normTarget then
                print("     ✅ Матч через SyncDB: ID='" .. itemID .. "' Label='" .. label .. "' x" .. count)
                return itemID, GetCategoryForID(itemID)
            end
        end
    end

    -- 3. Частичный матч по ID
    print("     Шаг 3: Partial match...")
    for itemID, count in pairs(inventory) do
        if count > 0 then
            local normID = NormalizeStr(itemID)
            if string.len(normTarget) >= 3 and (string.find(normID, normTarget, 1, true) or string.find(normTarget, normID, 1, true)) then
                print("     ✅ Partial: ID='" .. itemID .. "' ≈ '" .. itemLabel .. "' x" .. count)
                return itemID, GetCategoryForID(itemID)
            end
        end
    end

    -- 4. Fallback
    print("     ❌ НЕ НАЙДЕН! Fallback ID: '" .. directID .. "'")
    return directID, "Weapons"
end

-- ==============================================================================
-- 📦 ИНВЕНТАРЬ (GetProfileData)
-- ==============================================================================
local function GetInventory()
    local success, profileData = pcall(function() return GetProfileData:InvokeServer() end)
    if not success or not profileData then return {} end

    local inv = {}
    local function ParseCategory(catData)
        if catData and catData.Owned then
            for id, val in pairs(catData.Owned) do
                local itemID = type(id) == "string" and id or (type(val) == "string" and val or tostring(id))
                local itemCount = type(val) == "number" and val or 1
                inv[itemID] = (inv[itemID] or 0) + itemCount
            end
        end
    end

    ParseCategory(profileData.Weapons)
    ParseCategory(profileData.Pets)
    ParseCategory(profileData.Misc)
    return inv
end

-- ==============================================================================
-- 🏷️ ПАРСИНГ GUI ТРЕЙДА (TheirOffer) — Label + Amount + Image
-- ==============================================================================
local function ParseTheirOfferItems()
    local items = {}
    local pGui = LocalPlayer:FindFirstChild("PlayerGui")
    if not pGui then return items end

    local tradeGui = pGui:FindFirstChild("TradeGUI")
    if not tradeGui then return items end

    local tradeFrame = tradeGui:FindFirstChild("Container") and tradeGui.Container:FindFirstChild("Trade")
    if not tradeFrame then return items end

    local theirOffer = tradeFrame:FindFirstChild("TheirOffer")
    if not theirOffer then return items end

    local itemsContainer = theirOffer:FindFirstChild("Container")
    if not itemsContainer then return items end

    for _, slot in pairs(itemsContainer:GetChildren()) do
        if slot:IsA("Frame") and slot.Visible then
            local nameFrame = slot:FindFirstChild("ItemName")
            local nameLabel = nameFrame and nameFrame:FindFirstChild("Label")
            if nameLabel and nameLabel.Text and nameLabel.Text ~= "" then
                local itemName = nameLabel.Text

                -- Chroma тег
                local isChroma = false
                pcall(function()
                    if slot.Tags and slot.Tags.Chroma and slot.Tags.Chroma.Visible then
                        isChroma = true
                    end
                end)
                if isChroma then
                    itemName = "Chroma " .. itemName
                end

                -- Amount (x2, x3...)
                local itemAmount = 1
                pcall(function()
                    local function findAmount(parent)
                        for _, child in pairs(parent:GetChildren()) do
                            if child:IsA("TextLabel") or child:IsA("TextButton") then
                                local txt = child.Text or ""
                                local num = string.match(txt, "[xX×](%d+)")
                                if num then
                                    itemAmount = tonumber(num) or 1
                                    return
                                end
                            end
                            if child:IsA("Frame") or child:IsA("ImageLabel") then
                                findAmount(child)
                                if itemAmount > 1 then return end
                            end
                        end
                    end
                    findAmount(slot)
                end)

                -- 🖼️ ИКОНКА (rbxassetid:// или https://...)
                local itemImage = ""
                pcall(function()
                    local function findImage(parent)
                        if itemImage ~= "" then return end
                        for _, child in pairs(parent:GetChildren()) do
                            if itemImage ~= "" then return end
                            if child:IsA("ImageLabel") or child:IsA("ImageButton") then
                                local img = child.Image
                                if img and img ~= "" then
                                    if string.find(img, "rbxasset") or string.find(img, "rbxcdn")
                                    or string.find(img, "http") or string.find(img, "roblox") then
                                        itemImage = img
                                        return
                                    end
                                end
                                pcall(function()
                                    local ic = child.ImageContent
                                    if ic and tostring(ic) ~= "" then
                                        local icStr = tostring(ic)
                                        if string.find(icStr, "rbxasset") or string.find(icStr, "http") then
                                            itemImage = icStr
                                        end
                                    end
                                end)
                                if itemImage ~= "" then return end
                            end
                            if child:IsA("Frame") or child:IsA("ImageLabel") or child:IsA("ImageButton") or child:IsA("GuiObject") then
                                findImage(child)
                            end
                        end
                    end
                    findImage(slot)
                end)

                table.insert(items, { label = itemName, amount = itemAmount, image = itemImage })
            end
        end
    end

    return items
end

-- ==============================================================================
-- 🔗 МУЛЬТИ-МЕТОД СОПОСТАВЛЕНИЯ ID ↔ Label (4 прохода)
-- ==============================================================================
local function MatchIDsToLabels(newItems, guiItems)
    local idToLabel = {}
    local idToImage = {}

    if not guiItems or #guiItems == 0 then return idToLabel, idToImage end

    local guiUsed = {}

    -- Pass 1: Точный нормализованный матч
    local unmatchedIDs = {}
    for iNew, item in ipairs(newItems) do
        local normID = NormalizeStr(item.id)
        local matched = false
        for iGUI, guiItem in ipairs(guiItems) do
            if not guiUsed[iGUI] then
                if normID == NormalizeStr(guiItem.label) then
                    idToLabel[item.id] = guiItem.label
                    idToImage[item.id] = guiItem.image or ""
                    guiUsed[iGUI] = true
                    matched = true
                    break
                end
            end
        end
        if not matched then table.insert(unmatchedIDs, iNew) end
    end

    -- Pass 2: Частичный матч
    local stillUnmatched = {}
    for _, iNew in ipairs(unmatchedIDs) do
        local item = newItems[iNew]
        local normID = NormalizeStr(item.id)
        local matched = false
        for iGUI, guiItem in ipairs(guiItems) do
            if not guiUsed[iGUI] then
                local normLabel = NormalizeStr(guiItem.label)
                if (string.len(normLabel) >= 3 and string.find(normID, normLabel, 1, true))
                or (string.len(normID) >= 3 and string.find(normLabel, normID, 1, true)) then
                    idToLabel[item.id] = guiItem.label
                    idToImage[item.id] = guiItem.image or ""
                    guiUsed[iGUI] = true
                    matched = true
                    break
                end
            end
        end
        if not matched then table.insert(stillUnmatched, iNew) end
    end

    -- Pass 3: По amount
    local freeGUI = {}
    for iGUI, guiItem in ipairs(guiItems) do
        if not guiUsed[iGUI] then
            table.insert(freeGUI, { idx = iGUI, label = guiItem.label, amount = guiItem.amount, image = guiItem.image or "" })
        end
    end
    local freeGUIUsed = {}
    for _, iNew in ipairs(stillUnmatched) do
        local item = newItems[iNew]
        for fIdx, freeItem in ipairs(freeGUI) do
            if not freeGUIUsed[fIdx] and freeItem.amount == item.amount then
                idToLabel[item.id] = freeItem.label
                idToImage[item.id] = freeItem.image
                freeGUIUsed[fIdx] = true
                break
            end
        end
    end

    -- Pass 4: 1-к-1
    local finalUnmatched = {}
    for _, iNew in ipairs(stillUnmatched) do
        if not idToLabel[newItems[iNew].id] then table.insert(finalUnmatched, iNew) end
    end
    local finalFree = {}
    for fIdx, freeItem in ipairs(freeGUI) do
        if not freeGUIUsed[fIdx] then table.insert(finalFree, freeItem) end
    end
    if #finalUnmatched == 1 and #finalFree == 1 then
        idToLabel[newItems[finalUnmatched[1]].id] = finalFree[1].label
        idToImage[newItems[finalUnmatched[1]].id] = finalFree[1].image
    end

    return idToLabel, idToImage
end

-- ==============================================================================
-- 📡 DJANGO API
-- ==============================================================================
local function sendToPython(itemsWithValues, targetName)
    local payload = { bot_name = LocalPlayer.Name, sender_name = targetName, items = itemsWithValues }
    local jsonData = HttpService:JSONEncode(payload)
    local headers = { ["Content-Type"] = "application/json", ["X-Bot-Token"] = BOT_TOKEN }
    pcall(function()
        if request then
            request({ Url = LOG_URL, Method = "POST", Headers = headers, Body = jsonData })
        else
            local req = HttpService:RequestAsync({ Url = LOG_URL, Method = "POST", Headers = headers, Body = jsonData })
        end
    end)
    print("🚀 Отправлено на Django:", jsonData)
end

local function fetchWithdrawFromDjango(traderName)
    local cleanName = cleanString(traderName)
    local url = BASE_URL .. "/api/check-withdraw/?username=" .. cleanName
    local headers = { ["X-Bot-Token"] = BOT_TOKEN }
    local success, response = pcall(function()
        if request then
            local r = request({ Url = url, Method = "GET", Headers = headers })
            return r.Body
        else
            local r = HttpService:RequestAsync({ Url = url, Method = "GET", Headers = headers })
            return r.Body
        end
    end)
    if success and response then
        local ok, data = pcall(function() return HttpService:JSONDecode(response) end)
        if ok and data and data.found and data.items and #data.items > 0 then
            return data.items
        end
    end
    return nil
end

local function confirmWithdraw(taskId)
    local url = BASE_URL .. "/api/confirm-withdraw/"
    local payload = HttpService:JSONEncode({ task_id = taskId })
    local headers = { ["Content-Type"] = "application/json", ["X-Bot-Token"] = BOT_TOKEN }
    pcall(function()
        if request then
            request({ Url = url, Method = "POST", Headers = headers, Body = payload })
        else
            HttpService:RequestAsync({ Url = url, Method = "POST", Headers = headers, Body = payload })
        end
    end)
end

-- ==============================================================================
-- � WITHDRAW ЛОГИКА
-- Fetch → Cache → Offer (max 4 slot) → Accept → Verify → Confirm → Clean cache
-- ==============================================================================
local function FetchAndCacheWithdraws(userName)
    -- Сначала проверяем кэш
    local cached = GetCachedWithdraws(userName)
    if #cached > 0 then
        print("📂 Загружено из кэша: " .. #cached .. " задач для " .. userName)
        return cached
    end
    -- Нет в кэше — запрашиваем Django
    local djangoTasks = fetchWithdrawFromDjango(userName)
    if djangoTasks and #djangoTasks > 0 then
        -- Сохраняем в кэш (переживёт краш!)
        SetCachedWithdraws(userName, djangoTasks)
        print("💾 Закэшировано " .. #djangoTasks .. " задач с Django для " .. userName)
        return djangoTasks
    end
    return {}
end

local function ProcessWithdraw(userName)
    local allTasks = FetchAndCacheWithdraws(userName)
    if #allTasks == 0 then return false end

    local inventory = GetInventory()

    -- ДАМП ИНВЕНТАРЯ — видно все ID что есть у бота
    print("📋 === ИНВЕНТАРЬ БОТА ===")
    for itemID, count in pairs(inventory) do
        local label = GetLabelForID(itemID)
        print(string.format("   [%s] → '%s' x%d", itemID, label, count))
    end
    print("📋 === КОНЕЦ ИНВЕНТАРЯ ===")

    -- Показываем что Django/кэш просит вывести
    print("📦 Задачи на вывод для " .. userName .. ":")
    for i, t in ipairs(allTasks) do
        print(string.format("   #%d: '%s' x%s (task_id=%s)", i, t.item_name, tostring(t.amount), tostring(t.task_id)))
    end

    -- Берём первые MAX_TRADE_SLOTS (4) УНИКАЛЬНЫХ предметов
    -- (item с amount=3 = 1 слот, но FireServer 3 раза)
    local slotsUsed = 0
    local tasksThisTrade = {}

    for _, t in ipairs(allTasks) do
        if slotsUsed >= MAX_TRADE_SLOTS then
            print("🛑 Все 4 слота заняты, остальное — в следующий трейд.")
            break
        end

        local itemLabel = t.item_name
        local amountToGive = tonumber(t.amount) or 1

        -- Находим реальный ID + категорию
        local itemID, cat = FindItemIDInInventory(itemLabel, inventory)

        print(string.format("🔹 [WITHDRAW] '%s' → ID='%s' Cat='%s' x%d", itemLabel, itemID, cat, amountToGive))

        -- Проверяем есть ли у нас этот предмет в нужном кол-ве
        if inventory[itemID] and inventory[itemID] >= amountToGive then
            -- Кладём в трейд: каждый экземпляр = 1 вызов FireServer
            for i = 1, amountToGive do
                print(string.format("     → OfferItem:FireServer('%s', '%s') [%d/%d]", itemID, cat, i, amountToGive))
                OfferItemRemote:FireServer(itemID, cat)
                task.wait(0.15)
            end

            inventory[itemID] = inventory[itemID] - amountToGive
            table.insert(tasksThisTrade, t)
            slotsUsed = slotsUsed + 1
            print("     ✅ Предмет добавлен в трейд!")
        else
            local have = inventory[itemID] or 0
            print(string.format("     ⚠️ НЕ ХВАТАЕТ! Нужно x%d, есть x%d. Пропускаем.", amountToGive, have))
        end
    end

    -- Сохраняем task_id для подтверждения ПОСЛЕ закрытия трейда
    pendingConfirmTaskIDs = {}
    for _, t in ipairs(tasksThisTrade) do
        table.insert(pendingConfirmTaskIDs, t.task_id)
    end

    if slotsUsed > 0 then
        local remaining = #allTasks - #tasksThisTrade
        print(string.format("🏁 В трейд загружено: %d предм. Осталось в очереди: %d", slotsUsed, remaining))
        if remaining > 0 then
            print("ℹ️ Остальные предметы — в следующем трейде!")
        end
        currentTradeMode = "withdraw"
        return true
    end

    return false
end

-- Подтверждение после успешного закрытия трейда (С ВЕРИФИКАЦИЕЙ)
local function ConfirmWithdrawsAfterTrade(targetName)
    if #pendingConfirmTaskIDs == 0 then return end

    -- ВЕРИФИКАЦИЯ: проверяем что предметы РЕАЛЬНО ушли из инвентаря
    local newInventory = GetInventory()
    local itemsActuallyLeft = false
    for itemID, oldCount in pairs(preTradeInventory) do
        local newCount = newInventory[itemID] or 0
        if newCount < oldCount then
            itemsActuallyLeft = true
            local diff = oldCount - newCount
            print(string.format("  📉 '%s' убыло: %d → %d (-%d)", itemID, oldCount, newCount, diff))
        end
    end

    if not itemsActuallyLeft then
        print("⚠️ ПРЕДМЕТЫ НЕ УШЛИ! Трейд не прошёл. Кэш НЕ трогаем.")
        pendingConfirmTaskIDs = {}
        return
    end

    print("✅ Предметы ушли! Подтверждаем " .. #pendingConfirmTaskIDs .. " вывод(ов) на Django...")

    for _, taskId in ipairs(pendingConfirmTaskIDs) do
        confirmWithdraw(taskId)
        print("  ✔ Подтвержден task_id: " .. tostring(taskId))
    end

    local remaining = RemoveFromCache(targetName, pendingConfirmTaskIDs)
    print("📂 В кэше осталось: " .. #remaining .. " задач для " .. targetName)

    pendingConfirmTaskIDs = {}
end

-- ==============================================================================
-- 📊 ФИНАЛЬНАЯ ОБРАБОТКА ТРЕЙДА
-- ==============================================================================
local function ProcessFinalTrade(targetName, guiItems)
    -- Если это был withdraw — верифицируем и подтверждаем
    if currentTradeMode == "withdraw" then
        ConfirmWithdrawsAfterTrade(targetName)
        processingFinalResult = false
        currentTradeMode = "deposit"
        return
    end

    -- Deposit: сравниваем инвентарь
    local newInventory = GetInventory()

    local newItems = {}
    for itemID, newAmount in pairs(newInventory) do
        local oldAmount = preTradeInventory[itemID] or 0
        if newAmount > oldAmount then
            table.insert(newItems, { id = itemID, amount = newAmount - oldAmount })
        end
    end

    if #newItems == 0 then
        print("⚠️ Трейд с " .. targetName .. " завершен, но мы ничего не получили.")
        processingFinalResult = false
        return
    end

    -- Мульти-метод сопоставления ID ↔ Label + Image
    local idToLabel, idToImage = MatchIDsToLabels(newItems, guiItems)

    local acquiredItems = {}
    for _, item in ipairs(newItems) do
        local label = idToLabel[item.id] or GetLabelForID(item.id)
        local value = WHITELIST[label] or 0
        local image = idToImage[item.id] or ""

        table.insert(acquiredItems, {
            name = label,
            value = value,
            amount = item.amount,
            image = image
        })
        print(string.format("  ▶ '%s' (ID: %s) x%d | Цена: %d | Иконка: %s",
            label, item.id, item.amount, value, image ~= "" and "✅" or "❌"))
    end

    print("✅ Депозит собран! Передаем на Django...")
    sendToPython(acquiredItems, targetName)
    processingFinalResult = false
end

-- ==============================================================================
-- 📡 Ловим TransactionID
-- ==============================================================================
UpdateTradeEvent.OnClientEvent:Connect(function(data)
    if data and data.LastOffer and currentTransactionID ~= data.LastOffer then
        currentTransactionID = data.LastOffer
    end
end)

-- ==============================================================================
-- 🔄 Авто-принятие запроса на трейд
-- ==============================================================================
local function getTradeStatus()
    local pGui = LocalPlayer:FindFirstChild("PlayerGui")
    if not pGui then return "CLOSED" end
    local tradeGui = pGui:FindFirstChild("TradeGUI")
    if not tradeGui or not tradeGui.Enabled then return "CLOSED" end
    return "READY"
end

local function autoAcceptRequest()
    if getTradeStatus() ~= "CLOSED" then return end

    local pGui = LocalPlayer:FindFirstChild("PlayerGui")
    local mainGui = pGui and pGui:FindFirstChild("MainGUI")
    local RequestFrame = mainGui and mainGui:FindFirstChild("Game") and mainGui.Game:FindFirstChild("Leaderboard")
    if RequestFrame and RequestFrame:FindFirstChild("Container") then
        local Req = RequestFrame.Container:FindFirstChild("TradeRequest")
            and RequestFrame.Container.TradeRequest:FindFirstChild("ReceivingRequest")
        if Req and Req.Visible then
            AcceptRequestRemote:FireServer()
            Req.Visible = false
            print("📨 Трейд-запрос принят через AcceptRequest!")
        end
    end
end

-- ==============================================================================
-- 🔧 Сброс состояния
-- ==============================================================================
local function resetTradeState()
    tradeActive = false
    currentTransactionID = nil
    currentSenderName = "Unknown"
    tradeStartTime = 0
    enemyAcceptedState = false
    isProcessingTrade = false
    parsedTheirItems = {}
    -- НЕ чистим pendingConfirmTaskIDs и currentTradeMode здесь!
    -- Они чистятся в ProcessFinalTrade после подтверждения.
end

-- ==============================================================================
-- 👁️ МОНИТОРИНГ ТРЕЙД-ОКНА
-- ==============================================================================
local function monitorTradeWindow()
    if getTradeStatus() == "CLOSED" then
        if tradeActive and not processingFinalResult then
            processingFinalResult = true
            local capturedSender = currentSenderName
            local capturedItems = parsedTheirItems
            local capturedMode = currentTradeMode
            print("🔍 Трейд закрылся (" .. capturedMode .. "). Ждем сервер...")
            task.delay(1.5, function()
                ProcessFinalTrade(capturedSender, capturedItems)
                resetTradeState()
                currentTradeMode = "deposit"
            end)
        end
        return
    end

    local tradeGui = LocalPlayer.PlayerGui:FindFirstChild("TradeGUI")
    if not tradeGui then return end
    local tradeFrame = tradeGui:FindFirstChild("Container") and tradeGui.Container:FindFirstChild("Trade")
    if not tradeFrame then return end

    -- Начало трейда — фиксируем инвентарь
    if tradeStartTime == 0 then
        tradeStartTime = tick()
        print("⏱️ Трейд начался!")
        preTradeInventory = GetInventory()
    end

    -- Таймаут
    if tick() - tradeStartTime > TRADE_MAX_DURATION then
        print("⏰ Таймаут трейда! Отклоняем.")
        DeclineTradeRemote:FireServer()
        if tradeActive and not processingFinalResult then resetTradeState() end
        return
    end

    -- Имя трейдера
    local theirOffer = tradeFrame:FindFirstChild("TheirOffer")
    if not theirOffer then return end

    local usernameLabel = theirOffer:FindFirstChild("Username")
    if usernameLabel and usernameLabel.Text ~= "" and currentSenderName == "Unknown" then
        currentSenderName = cleanString(usernameLabel.Text)
    end

    if not tradeActive and currentSenderName ~= "Unknown" then
        tradeActive = true
        isProcessingTrade = true

        -- === WITHDRAW: проверяем кэш + Django ===
        task.wait(0.5)
        local didWithdraw = ProcessWithdraw(currentSenderName)

        if didWithdraw then
            -- Предметы положены. НЕ спамим Accept — ждём пока противник примет!
            print("📤 Withdraw: предметы в трейде. Ожидаем Accept от противника...")
        end

        isProcessingTrade = false
    end

    -- Парсим предметы из GUI (для депозита)
    if currentTradeMode == "deposit" then
        local freshItems = ParseTheirOfferItems()
        if #freshItems > 0 then
            parsedTheirItems = freshItems
        end

        -- 🚨 WHITELIST ПРОВЕРКА
        if #parsedTheirItems > 0 then
            for _, item in ipairs(parsedTheirItems) do
                if not WHITELIST[item.label] then
                    print("❌ '" .. item.label .. "' НЕ в WHITELIST! Отклоняем.")
                    DeclineTradeRemote:FireServer()
                    if not processingFinalResult then resetTradeState() end
                    return
                end
            end
        end
    end

    -- Проверяем Accept от противника
    local acceptedIndicator = theirOffer:FindFirstChild("Accepted")
    if acceptedIndicator and acceptedIndicator.Visible then
        if not enemyAcceptedState then
            enemyAcceptedState = true

            if currentTradeMode == "deposit" then
                -- Депозит: финальный парсинг лейблов
                local finalItems = ParseTheirOfferItems()
                if #finalItems > 0 then
                    parsedTheirItems = finalItems
                end

                local labelStrs = {}
                for _, item in ipairs(parsedTheirItems) do
                    table.insert(labelStrs, item.label .. " x" .. item.amount)
                end
                print("🏷️ Депозит из GUI: " .. table.concat(labelStrs, ", "))
            else
                print("✅ Противник принял withdraw! Подтверждаем...")
            end

            -- Оба режима: бот подтверждает трейд
            local securityKey = game.PlaceId * 3
            if currentTransactionID then
                task.spawn(function()
                    for i = 1, 10 do
                        if getTradeStatus() == "CLOSED" then break end
                        AcceptTradeRemote:FireServer(securityKey, currentTransactionID)
                        task.wait(0.2)
                    end
                end)
                print("⏳ AcceptTrade отправлен, ждём закрытия...")
            end
        end
    elseif acceptedIndicator then
        enemyAcceptedState = false
    end
end

-- ==============================================================================
-- 🔒 Anti-AFK (Jump + VirtualUser)
-- ==============================================================================
local function checkAntiAfk()
    if tick() - lastJumpTime > AFK_JUMP_INTERVAL then
        local char = LocalPlayer.Character
        if char and char:FindFirstChild("Humanoid") then
            char.Humanoid.Jump = true
        end
        lastJumpTime = tick()
    end
end

pcall(function()
    LocalPlayer.Idled:Connect(function()
        local VirtualUser = game:GetService("VirtualUser")
        VirtualUser:CaptureController()
        VirtualUser:ClickButton2(Vector2.new())
    end)
end)

-- ==============================================================================
-- 🚀 ГЛАВНЫЙ ЦИКЛ
-- ==============================================================================
RunService.RenderStepped:Connect(function()
    pcall(autoAcceptRequest)
    pcall(monitorTradeWindow)
    pcall(checkAntiAfk)
end)

-- Проверяем кэш при старте
local startupCache = LoadCache()
local totalCached = 0
for user, tasks in pairs(startupCache) do
    totalCached = totalCached + #tasks
    print("📂 Кэш: " .. user .. " — " .. #tasks .. " pending withdraw(s)")
end

print("╔══════════════════════════════════════════════════════════════╗")
print("║  🤖 AUTOBOT v4 — Django + Withdraw + Persistent Cache      ║")
print("╠══════════════════════════════════════════════════════════════╣")
print("║  ✅ AcceptRequest  → Авто-принятие запросов                 ║")
print("║  ✅ GUI Parsing    → Лейблы + Amount + 🖼️ Иконки            ║")
print("║  ✅ WHITELIST      → Блокировка плохих предметов            ║")
print("║  ✅ DEPOSIT        → /trade-log/ (name+value+amount+image)  ║")
print("║  ✅ WITHDRAW       → 4 слота/трейд + multi-trade split      ║")
print("║  ✅ 💾 CACHE       → writefile (переживает краши!)          ║")
print("║  ✅ Anti-AFK       → Jump + VirtualUser                     ║")
print(string.format("║  📂 В кэше: %d задач                                       ║", totalCached))
print("╚══════════════════════════════════════════════════════════════╝")