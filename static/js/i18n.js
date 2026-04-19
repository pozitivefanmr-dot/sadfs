/* ================================================================
   MMFLIP i18n — EN/RU translation system
   Usage:
     - Add data-i18n="key"           -> replaces innerText
     - Add data-i18n-html="key"      -> replaces innerHTML
     - Add data-i18n-attr="attr:key" -> sets attribute value
     - window.I18N.t('key')          -> get current translation
     - setLanguage('en'|'ru')         -> switch language
   ================================================================ */
(function () {
    const TRANSLATIONS = {
        // ===== NAV =====
        "nav.dashboard": { en: "Dashboard", ru: "Главная" },
        "nav.history":   { en: "History",   ru: "История" },
        "nav.coinflip":  { en: "Coinflip",  ru: "Коинфлип" },
        "nav.admin":     { en: "Admin",     ru: "Админ" },

        // ===== HEADER =====
        "header.login":        { en: "LOGIN",              ru: "ВОЙТИ" },
        "header.loginRoblox":  { en: "LOGIN WITH ROBLOX",  ru: "ВОЙТИ ЧЕРЕЗ ROBLOX" },

        // ===== LANGUAGE DROPDOWN =====
        "lang.title":    { en: "Language",            ru: "Язык" },
        "lang.subtitle": { en: "Choose your language", ru: "Выберите язык" },

        // ===== SNOW DROPDOWN =====
        "snow.title":    { en: "Snow Effect",           ru: "Эффект снега" },
        "snow.subtitle": { en: "Particle system control", ru: "Управление частицами" },
        "snow.on":       { en: "ON",        ru: "ВКЛ" },
        "snow.off":      { en: "OFF",       ru: "ВЫКЛ" },
        "snow.intensity":{ en: "Intensity", ru: "Интенсивность" },
        "snow.low":      { en: "Low",       ru: "Низко" },
        "snow.med":      { en: "Med",       ru: "Средне" },
        "snow.high":     { en: "High",      ru: "Высоко" },
        "snow.enable":   { en: "ENABLE",    ru: "ВКЛЮЧИТЬ" },
        "snow.disable":  { en: "DISABLE",   ru: "ОТКЛЮЧИТЬ" },

        // ===== USER DROPDOWN =====
        "user.welcomeBack": { en: "Welcome back", ru: "С возвращением" },
        "user.deposit":     { en: "Deposit",      ru: "Депозит" },
        "user.addFunds":    { en: "Add funds",    ru: "Пополнить" },
        "user.withdraw":    { en: "Withdraw",     ru: "Вывод" },
        "user.cashOut":     { en: "Cash out",     ru: "Вывести" },
        "user.logout":      { en: "Logout",       ru: "Выйти" },
        "user.depositUp":   { en: "DEPOSIT",      ru: "ДЕПОЗИТ" },
        "user.withdrawUp":  { en: "WITHDRAW",     ru: "ВЫВОД" },
        "user.logoutUp":    { en: "LOGOUT",       ru: "ВЫЙТИ" },

        // ===== BOT MODAL =====
        "bot.selectBot":      { en: "SELECT BOT",      ru: "ВЫБЕРИТЕ БОТА" },
        "bot.depositItems":   { en: "DEPOSIT ITEMS",   ru: "ВНЕСТИ ПРЕДМЕТЫ" },
        "bot.withdrawItems":  { en: "WITHDRAW ITEMS",  ru: "ВЫВЕСТИ ПРЕДМЕТЫ" },
        "bot.join":           { en: "JOIN",            ru: "ВОЙТИ" },

        // ===== HOME PAGE =====
        "home.welcomeBack": { en: "WELCOME BACK,", ru: "С ВОЗВРАЩЕНИЕМ," },
        "home.manageDesc":  { en: "Manage your inventory and view statistics.", ru: "Управляйте инвентарём и смотрите статистику." },
        "home.heroBadgeTitle": { en: "MURDER MYSTERY 2",        ru: "MURDER MYSTERY 2" },
        "home.heroBadgeSub":   { en: "Roblox MM2 Trading & Flipping", ru: "Roblox MM2 — трейд и флип" },
        "home.heroTitlePre":   { en: "MURDER MYSTERY",          ru: "MURDER MYSTERY" },
        "home.heroTitleAcc":   { en: "COINFLIP",                ru: "КОИНФЛИП" },
        "home.heroDesc":       { en: "Stake your MM2 items in 1v1 coinflip duels. Fair odds, instant results, real inventory prizes.", ru: "Ставьте свои MM2 предметы в дуэлях 1v1. Честные шансы, мгновенные результаты, реальные призы из инвентаря." },
        "home.heroStart":      { en: "START PLAYING",           ru: "НАЧАТЬ ИГРАТЬ" },
        "home.heroWatch":      { en: "WATCH GAMES",             ru: "СМОТРЕТЬ ИГРЫ" },
        "home.giveawaysTitle": { en: "ACTIVE GIVEAWAYS",        ru: "АКТИВНЫЕ РОЗЫГРЫШИ" },
        "home.giveawaysSub":   { en: "Join & win free MM2 items", ru: "Участвуйте и выигрывайте MM2 предметы" },
        "home.noGiveaways":    { en: "No active giveaways right now.", ru: "Активных розыгрышей нет." },
        "home.gaEmptyHint":    { en: "Click <strong>GIVEAWAY</strong> on any item in your inventory to start one!", ru: "Нажмите <strong>РОЗЫГРЫШ</strong> на любом предмете в инвентаре, чтобы начать!" },
        "home.checkBackLater": { en: "Check back later!",        ru: "Загляните позже!" },
        "home.inventoryTitle": { en: "YOUR INVENTORY",           ru: "ВАШ ИНВЕНТАРЬ" },
        "home.mm2Value":       { en: "MM2 VALUE:",               ru: "ЦЕННОСТЬ MM2:" },
        "home.noItems":        { en: "No Items Yet",             ru: "Пока нет предметов" },
        "home.noItemsDesc":    { en: "Trade with one of our bots to deposit your MM2 items and start flipping.", ru: "Сделайте трейд с нашим ботом, чтобы внести MM2 предметы и начать играть." },
        "home.depositBtn":     { en: "DEPOSIT ITEMS",            ru: "ВНЕСТИ ПРЕДМЕТЫ" },
        "home.statsTitle":     { en: "YOUR STATISTICS",          ru: "ВАША СТАТИСТИКА" },
        "home.statsProfit":    { en: "PROFIT",                   ru: "ПРИБЫЛЬ" },
        "home.statsGames":     { en: "GAMES",                    ru: "ИГРЫ" },
        "home.statsWinRate":   { en: "WIN RATE",                 ru: "ВИНРЕЙТ" },
        "home.statsWins":      { en: "WINS",                     ru: "ПОБЕДЫ" },
        "home.statsLosses":    { en: "LOSSES",                   ru: "ПОРАЖЕНИЯ" },
        "home.ga.join":        { en: "JOIN",                     ru: "УЧАСТВОВАТЬ" },
        "home.ga.joined":      { en: "JOINED",                   ru: "УЧАСТВУЕТЕ" },
        "home.ga.loginBtn":    { en: "LOGIN",                    ru: "ВОЙТИ" },
        "home.ga.endNow":      { en: "END NOW",                  ru: "ЗАВЕРШИТЬ" },
        "home.ga.showMore":    { en: "Show more",                ru: "Показать ещё" },
        "home.ga.showLess":    { en: "Show less",                ru: "Свернуть" },
        "home.ga.showMoreWord":{ en: "SHOW",                     ru: "ЕЩЁ" },
        "home.ga.moreWord":    { en: "MORE",                     ru: "" },
        "home.feat1Title":     { en: "Coinflip Duels",           ru: "Дуэли коинфлип" },
        "home.feat1Desc":      { en: "Pick green or red, stake your MM2 items, flip — winner takes the entire pot", ru: "Выберите зелёный или красный, ставьте MM2 предметы, флипайте — победитель забирает весь банк" },
        "home.feat2Title":     { en: "Provably Fair",            ru: "Честная игра" },
        "home.feat2Desc":      { en: "Results powered by random.org — every game gets a SHA-256 hash for proof", ru: "Результаты от random.org — каждая игра получает SHA-256 хеш для доказательства" },
        "home.feat3Title":     { en: "Deposit & Withdraw",       ru: "Депозит и вывод" },
        "home.feat3Desc":      { en: "Send items to our Roblox bot, play instantly, cash out whenever you want", ru: "Отправьте предметы нашему Roblox боту, играйте сразу, выводите когда захотите" },
        "home.feat4Title":     { en: "Daily Giveaways",          ru: "Ежедневные розыгрыши" },
        "home.feat4Desc":      { en: "Players drop free items daily — just join and wait for the winner draw", ru: "Игроки каждый день дарят предметы — просто участвуйте и ждите розыгрыша" },
        "home.netWorth":       { en: "NET WORTH",                ru: "ОБЩЕЕ СОСТОЯНИЕ" },
        "home.supremeValues":  { en: "Supreme Values",           ru: "Supreme Values" },
        "home.totalItems":     { en: "TOTAL ITEMS",              ru: "ВСЕГО ПРЕДМЕТОВ" },
        "home.inInventory":    { en: "In your inventory",        ru: "В вашем инвентаре" },
        "home.withdrawBtn":    { en: "WITHDRAW",                 ru: "ВЫВОД" },
        "home.giveawayBtn":    { en: "GIVEAWAY",                 ru: "РОЗЫГРЫШ" },

        // ===== COINFLIP =====
        "cf.profitTitle":  { en: "TOTAL PROFIT",        ru: "ОБЩАЯ ПРИБЫЛЬ" },
        "cf.profitSub":    { en: "Your lifetime earnings on MMFLIP", ru: "Ваш общий заработок на MMFLIP" },
        "cf.createGame":   { en: "CREATE GAME",         ru: "СОЗДАТЬ ИГРУ" },
        "cf.createGameBtn":{ en: "CREATE NEW GAME",     ru: "СОЗДАТЬ ИГРУ" },
        "cf.activeGames":  { en: "ACTIVE GAMES",        ru: "АКТИВНЫЕ ИГРЫ" },
        "cf.finishedGames":{ en: "RECENT WINNERS",      ru: "НЕДАВНИЕ ПОБЕДИТЕЛИ" },
        "cf.noActive":     { en: "No active games",     ru: "Нет активных игр" },
        "cf.noActiveDesc": { en: "Be the first to create one!", ru: "Создайте первую!" },
        "cf.selectItems":  { en: "Select items to bet", ru: "Выберите предметы для ставки" },
        "cf.totalBet":     { en: "TOTAL BET",           ru: "ОБЩАЯ СТАВКА" },
        "cf.chooseSide":   { en: "Choose your side",    ru: "Выберите сторону" },
        "cf.cancel":       { en: "CANCEL",              ru: "ОТМЕНА" },
        "cf.confirm":      { en: "CREATE",              ru: "СОЗДАТЬ" },
        "cf.join":         { en: "JOIN",                ru: "ВОЙТИ" },
        "cf.watch":        { en: "WATCH",               ru: "СМОТРЕТЬ" },

        // (trade keys moved to TRADE / HISTORY PAGE section below)

        // ===== FOOTER =====
        "footer.brandDesc":   { en: "The #1 platform for Murder Mystery 2 coinflip battles. Flip your items, double your inventory — instantly and fairly.", ru: "Платформа №1 для коинфлип-боёв Murder Mystery 2. Флипайте свои предметы, удваивайте инвентарь — мгновенно и честно." },
        "footer.trust.fair":  { en: "Provably Fair",     ru: "Честная игра" },
        "footer.trust.uid":   { en: "Unique Game ID",    ru: "Уникальный ID игры" },
        "footer.trust.secure":{ en: "Secure",            ru: "Безопасно" },
        "footer.nav":         { en: "Navigation",        ru: "Навигация" },
        "footer.legal":       { en: "Legal",             ru: "Документы" },
        "footer.faq":         { en: "FAQ",               ru: "FAQ" },
        "footer.pfair":       { en: "Provably Fair",     ru: "Честная игра" },
        "footer.tos":         { en: "Terms of Service",  ru: "Условия использования" },
        "footer.privacy":     { en: "Privacy Policy",    ru: "Политика конфиденциальности" },
        "footer.howItWorks":  { en: "How It Works",      ru: "Как это работает" },
        "footer.howItWorksBody": { en: "Every coinflip result is powered by <strong>Random.org</strong> — true random numbers from atmospheric noise. Each game gets a <strong>unique game ID (UID)</strong> and the result is logged in our <strong>Discord server</strong> for full transparency. A <strong>~10% commission</strong> applies on pots over 50 SV with 4+ items.", ru: "Каждый результат коинфлипа генерируется через <strong>Random.org</strong> — истинно случайные числа из атмосферного шума. Каждой игре присваивается <strong>уникальный ID (UID)</strong>, а результат публикуется в нашем <strong>Discord</strong> для полной прозрачности. <strong>Комиссия ~10%</strong> применяется на банках свыше 50 SV с 4+ предметами." },
        "footer.community":   { en: "Community",         ru: "Сообщество" },
        "footer.discordSub":  { en: "Join our server",   ru: "Зайти на сервер" },
        "footer.telegramSub": { en: "Follow updates",    ru: "Следить за обновлениями" },
        "footer.faqTitle":    { en: "Frequently Asked Questions", ru: "Часто задаваемые вопросы" },
        "footer.copyright":   { en: "All rights reserved.", ru: "Все права защищены." },
        "footer.badge.uid":   { en: "Unique Game UID",   ru: "Уникальный UID игры" },
        "footer.badge.roblox":{ en: "Roblox MM2",        ru: "Roblox MM2" },
        "footer.badge.logs":  { en: "Discord Logs",      ru: "Discord логи" },

        // FAQ questions
        "faq.q1":  { en: "What is MMFLIP?", ru: "Что такое MMFLIP?" },
        "faq.a1":  { en: "MMFLIP is a coinflip platform for Roblox Murder Mystery 2 items. You deposit your MM2 weapons, create or join coinflip games, and the winner takes all items from both sides.", ru: "MMFLIP — это платформа для коинфлипа с предметами из Roblox Murder Mystery 2. Вы вносите свои MM2 оружия, создаёте или присоединяетесь к играм, а победитель забирает все предметы с обеих сторон." },
        "faq.q2":  { en: "Is it truly random?", ru: "Это действительно случайно?" },
        "faq.a2":  { en: "Yes! Every game outcome is generated using <strong>Random.org</strong> — a service that produces true random numbers from atmospheric noise, not computer algorithms. If Random.org is momentarily unavailable, we fall back to Python's cryptographically secure <strong>secrets</strong> module. Each game receives a unique ID (UID) and the result is logged in our Discord for verification.", ru: "Да! Каждый исход генерируется через <strong>Random.org</strong> — сервис, производящий истинно случайные числа из атмосферного шума, а не из компьютерных алгоритмов. Если Random.org временно недоступен, мы используем криптографически безопасный модуль <strong>secrets</strong> из Python. Каждая игра получает уникальный ID, а результат публикуется в Discord для проверки." },
        "faq.q3":  { en: "How do I deposit items?", ru: "Как внести предметы?" },
        "faq.a3":  { en: "Click the <strong>Deposit</strong> button in the header, select one of our trade bots, join their game in Roblox, and trade your MM2 items to the bot. They'll appear in your inventory within seconds.", ru: "Нажмите кнопку <strong>Депозит</strong> в шапке, выберите одного из наших трейд-ботов, присоединитесь к его игре в Roblox и передайте ему свои MM2 предметы. Они появятся в вашем инвентаре за секунды." },
        "faq.q4":  { en: "How do I withdraw winnings?", ru: "Как вывести выигрыш?" },
        "faq.a4":  { en: "Go to your Dashboard, hover over the item you want, and click <strong>Withdraw</strong>. Then join the trade bot in Roblox to receive your items.", ru: "Перейдите на Главную, наведите на нужный предмет и нажмите <strong>Вывод</strong>. Затем присоединитесь к трейд-боту в Roblox, чтобы получить предметы." },
        "faq.q5":  { en: "Can I verify game results?", ru: "Можно ли проверить результаты?" },
        "faq.a5":  { en: "Yes. Every game has a <strong>unique UID</strong> and stores the raw result code (1 or 2) from Random.org. All outcomes are automatically posted to our Discord log channel with full details — players, items, result code, and winner. You can cross-reference any game at any time.", ru: "Да. Каждая игра имеет <strong>уникальный UID</strong> и хранит сырой код результата (1 или 2) от Random.org. Все исходы автоматически публикуются в лог-канале Discord со всеми деталями — игроки, предметы, код и победитель. Вы можете проверить любую игру в любое время." },
        "faq.q6":  { en: "Does MMFLIP take a commission?", ru: "Берёт ли MMFLIP комиссию?" },
        "faq.a6":  { en: "Yes. A commission of approximately <strong>10%</strong> is taken from the winner's items when the total pot exceeds <strong>50 SV</strong> and the game contains more than <strong>4 items</strong>. The system picks the item(s) closest to the target value. If these conditions aren't met, <strong>no commission is charged</strong>.", ru: "Да. Комиссия около <strong>10%</strong> взимается с предметов победителя, когда общий банк превышает <strong>50 SV</strong> и в игре больше <strong>4 предметов</strong>. Система выбирает предмет(ы), ближайший к целевой сумме. Если условия не выполнены, <strong>комиссия не берётся</strong>." },
        "faq.q7":  { en: "What if I have a problem?", ru: "Что если возникла проблема?" },
        "faq.a7":  { en: "Reach out via the global chat, open a ticket in our Discord, or message us on Telegram. We resolve all disputes quickly and fairly.", ru: "Напишите в общий чат, откройте тикет в нашем Discord или напишите в Telegram. Мы решаем все споры быстро и честно." },

        // ===== TRADE / HISTORY PAGE =====
        "trade.heroTitle":        { en: "HISTORY",                    ru: "ИСТОРИЯ" },
        "trade.heroSub":          { en: "Your complete activity log", ru: "Полный лог вашей активности" },
        "trade.globalLogs":       { en: "GLOBAL LOGS",               ru: "ОБЩИЕ ЛОГИ" },
        "trade.globalLogsSub":    { en: "System monitor & incoming trades", ru: "Мониторинг системы и входящие трейды" },
        "trade.noTradeLogs":      { en: "No trade logs found.",      ru: "Логов трейдов не найдено." },
        "trade.tabGames":         { en: "GAMES",                     ru: "ИГРЫ" },
        "trade.tabDeposits":      { en: "DEPOSITS",                  ru: "ДЕПОЗИТЫ" },
        "trade.tabWithdrawals":   { en: "WITHDRAWALS",               ru: "ВЫВОДЫ" },
        "trade.gameHistory":      { en: "GAME HISTORY",              ru: "ИСТОРИЯ ИГР" },
        "trade.gameHistorySub":   { en: "Your recent coinflip results", ru: "Ваши последние результаты коинфлипа" },
        "trade.vs":               { en: "VS",                        ru: "VS" },
        "trade.win":              { en: "WIN",                       ru: "ПОБЕДА" },
        "trade.loss":             { en: "LOSS",                      ru: "ПОРАЖЕНИЕ" },
        "trade.noGames":          { en: "No games played yet",       ru: "Игр ещё не было" },
        "trade.playNow":          { en: "Play Now",                  ru: "Играть" },
        "trade.depositHistory":   { en: "DEPOSIT HISTORY",           ru: "ИСТОРИЯ ДЕПОЗИТОВ" },
        "trade.depositHistorySub":{ en: "Items sent to bots",        ru: "Предметы, отправленные ботам" },
        "trade.depositTo":        { en: "Deposit to",                ru: "Депозит на" },
        "trade.noDeposits":       { en: "No deposits yet",           ru: "Депозитов пока нет" },
        "trade.withdrawalHistory":{ en: "WITHDRAWAL HISTORY",        ru: "ИСТОРИЯ ВЫВОДОВ" },
        "trade.withdrawalHistorySub": { en: "Items withdrawn from your balance", ru: "Предметы, выведенные с вашего баланса" },
        "trade.noWithdrawals":    { en: "No withdrawals yet",        ru: "Выводов пока нет" },
        "trade.completed":        { en: "Completed",                 ru: "Выполнен" },
        "trade.pending":          { en: "Pending",                   ru: "В ожидании" },
        "trade.games":            { en: "games",                     ru: "игр" },
        "trade.deposits":         { en: "deposits",                  ru: "депозитов" },
        "trade.withdrawals":      { en: "withdrawals",               ru: "выводов" },

        // ===== COINFLIP (EXTRA) =====
        "cf.activeGamesLabel": { en: "ACTIVE GAMES",      ru: "АКТИВНЫЕ ИГРЫ" },
        "cf.profitLabel":      { en: "PROFIT",             ru: "ПРИБЫЛЬ" },
        "cf.tabAll":           { en: "ALL",                ru: "ВСЕ" },
        "cf.tab7d":            { en: "7D",                 ru: "7Д" },
        "cf.tab24h":           { en: "24H",                ru: "24Ч" },
        "cf.selected":         { en: "SELECTED",           ru: "ВЫБРАНО" },
        "cf.entryRange":       { en: "Entry Range",        ru: "Диапазон входа" },
        "cf.invEmptyTitle":    { en: "INVENTORY EMPTY",    ru: "ИНВЕНТАРЬ ПУСТ" },
        "cf.invEmptyDesc":     { en: "You don't have any items yet.<br>Use our bot to start playing.", ru: "У вас ещё нет предметов.<br>Используйте нашего бота, чтобы начать играть." },
        "cf.confirmJoin":      { en: "CONFIRM JOIN",       ru: "ПОДТВЕРДИТЬ ВХОД" },
        "cf.joinVs":           { en: "JOIN VS",            ru: "ВОЙТИ ПРОТИВ" },
        "cf.loginToPlay":      { en: "LOGIN TO PLAY",      ru: "ВОЙДИТЕ, ЧТОБЫ ИГРАТЬ" },
        "cf.loginToJoin":      { en: "LOGIN TO JOIN",      ru: "ВОЙДИТЕ ДЛЯ ВХОДА" },
        "cf.noGamesYet":       { en: "NO GAMES YET",       ru: "ИГР ПОКА НЕТ" },
        "cf.beFirst":          { en: "Be the first to create one!", ru: "Создайте первую!" },
        "cf.vs":               { en: "VS",                 ru: "VS" },
        "cf.gameItems":        { en: "GAME ITEMS",         ru: "ПРЕДМЕТЫ ИГРЫ" },
        "cf.joining":          { en: "JOINING...",          ru: "ВХОД..." },
        "cf.creating":         { en: "CREATING...",         ru: "СОЗДАНИЕ..." },

        // ===== FLIP RESULT OVERLAY =====
        "flip.youWon":       { en: "YOU WON!",       ru: "ВЫ ВЫИГРАЛИ!" },
        "flip.luckyOne":     { en: "Lucky one!",     ru: "Везунчик!" },
        "flip.youLost":      { en: "YOU LOST",       ru: "ВЫ ПРОИГРАЛИ" },
        "flip.loser":        { en: "Loser :(",       ru: "Неудачник :(" },
        "flip.totalBet":     { en: "TOTAL BET",      ru: "ОБЩАЯ СТАВКА" },
        "flip.close":        { en: "CLOSE",          ru: "ЗАКРЫТЬ" },

        // ===== LEADERBOARD =====
        "lb.title":      { en: "LEADERBOARD",         ru: "ЛИДЕРБОРД" },
        "lb.sub":        { en: "TOP COINFLIP WINNERS", ru: "ТОП ПОБЕДИТЕЛЕЙ КОИНФЛИПА" },
        "lb.allTime":    { en: "ALL TIME",            ru: "ЗА ВСЁ ВРЕМЯ" },
        "lb.week":       { en: "LAST 7 DAYS",         ru: "ПОСЛЕДНИЕ 7 ДНЕЙ" },
        "lb.player":     { en: "PLAYER",              ru: "ИГРОК" },
        "lb.games":      { en: "GAMES",               ru: "ИГРЫ" },
        "lb.wins":       { en: "WINS",                ru: "ПОБЕДЫ" },
        "lb.winRate":    { en: "WIN RATE",            ru: "ВИНРЕЙТ" },
        "lb.wonValue":   { en: "WON VALUE",           ru: "ВЫИГРАНО" },
        "lb.empty":      { en: "No games played yet. Be the first!", ru: "Пока нет сыгранных игр. Станьте первым!" },
        "nav.leaderboard": { en: "Leaderboard",       ru: "Лидерборд" },

        // ===== HOME MODALS =====
        "home.confirmWithdrawTitle": { en: "CONFIRM WITHDRAWAL",     ru: "ПОДТВЕРДИТЬ ВЫВОД" },
        "home.confirmWithdrawDesc":  { en: "You are about to withdraw this item. It will be sent to the trade bot for pickup.", ru: "Вы собираетесь вывести этот предмет. Он будет отправлен трейд-боту для получения." },
        "home.confirmWithdrawBtn":   { en: "CONFIRM",                ru: "ПОДТВЕРДИТЬ" },
        "home.processing":           { en: "PROCESSING...",          ru: "ОБРАБОТКА..." },
        "home.startGiveawayTitle":   { en: "START A GIVEAWAY?",      ru: "НАЧАТЬ РОЗЫГРЫШ?" },
        "home.startGiveawayDesc":    { en: "This item will be raffled among all participants. The giveaway lasts <strong>24 hours</strong> and <strong>cannot be undone</strong>.", ru: "Этот предмет будет разыгран среди всех участников. Розыгрыш длится <strong>24 часа</strong> и <strong>не может быть отменён</strong>." },
        "home.startGiveawayBtn":     { en: "START GIVEAWAY",         ru: "НАЧАТЬ РОЗЫГРЫШ" },
        "home.accessDenied":         { en: "ACCESS DENIED",          ru: "ДОСТУП ЗАПРЕЩЁН" },
        "home.gotIt":                { en: "GOT IT",                  ru: "ПОНЯТНО" },
        "home.ga.by":                { en: "by",                      ru: "от" },
        "home.ga.ended":             { en: "ENDED",                   ru: "ЗАВЕРШЁН" },
        "home.ga.endConfirm":        { en: "End this giveaway now? A random winner will be selected immediately.", ru: "Завершить розыгрыш сейчас? Случайный победитель будет выбран немедленно." },

        // ===== FOOTER MODALS =====
        "modal.pf.title":               { en: "Provably Fair",                    ru: "Честная игра" },
        "modal.pf.howTitle":             { en: "How Results Are Generated",        ru: "Как генерируются результаты" },
        "modal.pf.howBody":              { en: "Every coinflip outcome on MMFLIP is determined using the <strong>Random.org</strong> API — a service that generates true random numbers from <strong>atmospheric noise</strong>, not pseudo-random algorithms. This means the result is physically unpredictable and cannot be reproduced or influenced by software.", ru: "Каждый результат коинфлипа на MMFLIP определяется с помощью API <strong>Random.org</strong> — сервиса, который генерирует истинно случайные числа из <strong>атмосферного шума</strong>, а не псевдослучайных алгоритмов. Это означает, что результат физически непредсказуем и не может быть воспроизведён или изменён программно." },
        "modal.pf.noiseTitle":           { en: "Atmospheric Noise (Random.org)",   ru: "Атмосферный шум (Random.org)" },
        "modal.pf.noiseBody":            { en: "Random.org samples atmospheric noise — tiny electrical fluctuations in the atmosphere — and converts them into random numbers. This method is <strong>fundamentally different</strong> from computer-generated pseudo-randomness. The numbers are truly unpredictable and pass all statistical randomness tests (NIST, Diehard, TestU01).", ru: "Random.org считывает атмосферный шум — крошечные электрические колебания в атмосфере — и преобразует их в случайные числа. Этот метод <strong>принципиально отличается</strong> от компьютерной псевдослучайности. Числа действительно непредсказуемы и проходят все статистические тесты (NIST, Diehard, TestU01)." },
        "modal.pf.fallbackTitle":        { en: "Secure Fallback",                 ru: "Безопасный резерв" },
        "modal.pf.fallbackBody":         { en: "In the rare event that the Random.org API is temporarily unavailable, the system falls back to Python's <strong>secrets</strong> module — a cryptographically secure random number generator designed specifically for security-sensitive applications. Either way, the outcome is never predictable.", ru: "В редких случаях, когда API Random.org временно недоступен, система использует модуль <strong>secrets</strong> Python — криптографически безопасный генератор случайных чисел. В любом случае результат никогда не предсказуем." },
        "modal.pf.uidTitle":             { en: "Unique Game ID",                   ru: "Уникальный ID игры" },
        "modal.pf.uidBody":              { en: "Each coinflip game is assigned a <strong>unique identifier (UID)</strong> the moment it is created. This ID is permanently linked to both players, all wagered items, the random result code (1 or 2), and the winner. It serves as an immutable reference for any game.", ru: "Каждой игре присваивается <strong>уникальный идентификатор (UID)</strong> в момент создания. Этот ID навсегда связан с обоими игроками, всеми предметами, кодом результата (1 или 2) и победителем." },
        "modal.pf.discordTitle":         { en: "Discord Logging",                 ru: "Логирование в Discord" },
        "modal.pf.discordBody":          { en: "All game results — including the UID, player names, items wagered, the raw result code, and the winner — are automatically posted to a dedicated log channel in our <strong>Discord server</strong>. Anyone can join and verify any game result at any time.", ru: "Все результаты игр — включая UID, имена игроков, предметы, код результата и победителя — автоматически публикуются в лог-канале нашего <strong>Discord сервера</strong>. Любой может проверить результат любой игры." },
        "modal.pf.commissionTitle":      { en: "Commission",                      ru: "Комиссия" },
        "modal.pf.commissionBody":       { en: "MMFLIP takes a small <strong>~10% commission</strong> from the winner's items when the total pot exceeds <strong>50 SV</strong> and the game contains more than <strong>4 items</strong>. The system automatically selects the item(s) closest to the 10% target. Commissioned items are logged and fully traceable. If conditions aren't met, <strong>no commission is taken</strong>.", ru: "MMFLIP берёт небольшую <strong>комиссию ~10%</strong> с предметов победителя, когда общий банк превышает <strong>50 SV</strong> и в игре больше <strong>4 предметов</strong>. Система автоматически выбирает предмет(ы), ближайшие к 10%. Если условия не выполнены, <strong>комиссия не берётся</strong>." },
        "modal.pf.transparencyTitle":    { en: "Full Transparency",               ru: "Полная прозрачность" },
        "modal.pf.transparencyBody":     { en: "We don't hide the method. Our random source is Random.org (publicly documented), our logs are public in Discord, and every game has a traceable ID. There are no hidden algorithms and no way for administrators to influence outcomes.", ru: "Мы не скрываем метод. Наш источник случайности — Random.org (публично задокументирован), логи открыты в Discord, и у каждой игры есть отслеживаемый ID. Нет скрытых алгоритмов и нет возможности для администраторов влиять на результаты." },

        "modal.tos.title":              { en: "Terms of Service",                 ru: "Условия использования" },
        "modal.tos.1title":             { en: "1. Acceptance of Terms",            ru: "1. Принятие условий" },
        "modal.tos.1body":              { en: "By accessing or using MMFLIP, you agree to be bound by these Terms of Service. If you do not agree, you must discontinue use immediately.", ru: "Используя MMFLIP, вы соглашаетесь с данными Условиями использования. Если вы не согласны, прекратите использование немедленно." },
        "modal.tos.2title":             { en: "2. Eligibility",                   ru: "2. Право использования" },
        "modal.tos.2body":              { en: "You must have a valid Roblox account to use MMFLIP. You are solely responsible for maintaining the security of your account credentials. MMFLIP is not affiliated with Roblox Corporation.", ru: "Для использования MMFLIP необходим действующий аккаунт Roblox. Вы несёте полную ответственность за безопасность своих учётных данных. MMFLIP не связан с Roblox Corporation." },
        "modal.tos.3title":             { en: "3. Fair Play",                     ru: "3. Честная игра" },
        "modal.tos.3body":              { en: "All games on MMFLIP are provably fair. Attempting to exploit, cheat, or manipulate the system in any way will result in immediate account termination and forfeiture of all items.", ru: "Все игры на MMFLIP провально честные. Попытки эксплуатации, мошенничества или манипулирования системой приведут к немедленной блокировке аккаунта и конфискации всех предметов." },
        "modal.tos.4title":             { en: "4. Item Deposits & Withdrawals",   ru: "4. Депозит и вывод предметов" },
        "modal.tos.4body":              { en: "Items deposited become part of the MMFLIP ecosystem. Withdrawals are processed through our trade bots. MMFLIP is not responsible for items lost due to Roblox trade system errors or user negligence.", ru: "Внесённые предметы становятся частью экосистемы MMFLIP. Выводы обрабатываются через наших трейд-ботов. MMFLIP не несёт ответственности за предметы, потерянные из-за ошибок торговой системы Roblox или халатности пользователя." },
        "modal.tos.5title":             { en: "5. Commission",                    ru: "5. Комиссия" },
        "modal.tos.5body":              { en: "MMFLIP charges a commission of approximately 10% on coinflip winnings when the total pot exceeds 50 SV and contains more than 4 items. The commission is automatically deducted from the winner's items. If these conditions are not met, no commission is taken.", ru: "MMFLIP берёт комиссию около 10% с выигрышей в коинфлипе, когда общий банк превышает 50 SV и содержит более 4 предметов. Комиссия автоматически вычитается из предметов победителя. Если условия не выполнены, комиссия не берётся." },
        "modal.tos.6title":             { en: "6. No Guarantees",                 ru: "6. Без гарантий" },
        "modal.tos.6body":              { en: "Coinflip outcomes are random. MMFLIP does not guarantee winnings. You participate at your own risk. Only wager items you are prepared to lose.", ru: "Результаты коинфлипа случайны. MMFLIP не гарантирует выигрыш. Вы участвуете на свой риск. Ставьте только те предметы, которые готовы потерять." },
        "modal.tos.7title":             { en: "7. Prohibited Conduct",            ru: "7. Запрещённое поведение" },
        "modal.tos.7body":              { en: "Users may not: use automated scripts or bots, attempt to manipulate game outcomes, engage in fraud or chargebacks, harass other users, or create multiple accounts to gain unfair advantages.", ru: "Пользователям запрещено: использовать скрипты или ботов, пытаться манипулировать результатами, заниматься мошенничеством, преследовать других пользователей или создавать несколько аккаунтов." },
        "modal.tos.8title":             { en: "8. Limitation of Liability",       ru: "8. Ограничение ответственности" },
        "modal.tos.8body":              { en: "MMFLIP is provided \"as is\" without warranties. We are not liable for any losses, damages, or disputes arising from the use of our platform beyond the scope of our control.", ru: "MMFLIP предоставляется «как есть» без гарантий. Мы не несём ответственности за убытки, ущерб или споры, возникающие при использовании платформы." },
        "modal.tos.9title":             { en: "9. Changes to Terms",              ru: "9. Изменения условий" },
        "modal.tos.9body":              { en: "We reserve the right to modify these terms at any time. Continued use of MMFLIP after changes constitutes acceptance of the updated terms.", ru: "Мы оставляем за собой право изменять эти условия в любое время. Продолжение использования MMFLIP означает принятие обновлённых условий." },

        "modal.pp.title":              { en: "Privacy Policy",                    ru: "Политика конфиденциальности" },
        "modal.pp.1title":             { en: "1. Information We Collect",          ru: "1. Какую информацию мы собираем" },
        "modal.pp.1body":              { en: "We collect your Roblox username, avatar URL, and in-game trade data. We do not collect personal information such as email addresses, real names, or payment information.", ru: "Мы собираем ваш ник Roblox, URL аватара и данные внутриигровых трейдов. Мы не собираем личную информацию — email, реальные имена или платёжные данные." },
        "modal.pp.2title":             { en: "2. How We Use Your Data",            ru: "2. Как мы используем ваши данные" },
        "modal.pp.2body":              { en: "Your data is used solely to operate the platform: authenticate your identity, process trades, track inventory, display game history, and maintain platform integrity.", ru: "Ваши данные используются исключительно для работы платформы: аутентификация, обработка трейдов, инвентарь, история игр и поддержание целостности." },
        "modal.pp.3title":             { en: "3. Data Storage",                    ru: "3. Хранение данных" },
        "modal.pp.3body":              { en: "All data is stored securely on our servers. Game logs (UIDs, participants, outcomes) are also published to our Discord server for transparency purposes.", ru: "Все данные надёжно хранятся на наших серверах. Логи игр (UID, участники, результаты) также публикуются в Discord для прозрачности." },
        "modal.pp.4title":             { en: "4. Third-Party Services",            ru: "4. Сторонние сервисы" },
        "modal.pp.4body":              { en: "We interact with the Roblox API to verify accounts and retrieve avatar data. We do not sell, share, or distribute your data to any third parties for marketing or advertising purposes.", ru: "Мы взаимодействуем с API Roblox для проверки аккаунтов и получения аватаров. Мы не продаём и не передаём ваши данные третьим лицам." },
        "modal.pp.5title":             { en: "5. Cookies & Local Storage",         ru: "5. Куки и локальное хранилище" },
        "modal.pp.5body":              { en: "We use browser local storage to remember your preferences (e.g., chat state, snow settings). No tracking cookies are used.", ru: "Мы используем локальное хранилище браузера для запоминания настроек (чат, эффект снега). Отслеживающие куки не используются." },
        "modal.pp.6title":             { en: "6. Your Rights",                     ru: "6. Ваши права" },
        "modal.pp.6body":              { en: "You may request deletion of your account and associated data at any time by contacting an administrator through Discord or the in-game chat.", ru: "Вы можете запросить удаление аккаунта и связанных данных в любое время, обратившись к администратору через Discord или чат." },
        "modal.pp.7title":             { en: "7. Changes to This Policy",          ru: "7. Изменения политики" },
        "modal.pp.7body":              { en: "We may update this Privacy Policy from time to time. We will notify users of significant changes via our Discord server.", ru: "Мы можем время от времени обновлять эту Политику. О значительных изменениях мы уведомляем через Discord." },

        // ===== AUTH / BASE =====
        "auth.checking":      { en: "Checking profile for code...", ru: "Проверяем профиль на наличие кода..." },
        "auth.enterUsername":  { en: "Please enter a username",     ru: "Введите имя пользователя" },
        "auth.userNotFound":   { en: "User not found",              ru: "Пользователь не найден" },
        "auth.connectionError":{ en: "Connection error. Try again.", ru: "Ошибка подключения. Попробуйте снова." },
        "auth.codeNotFound":   { en: "Code not found in your profile. Please paste the code into your Roblox About section and try again.", ru: "Код не найден в профиле. Вставьте код в раздел About вашего Roblox и попробуйте снова." },
        "auth.verifyError":    { en: "Error verifying code. Try again.", ru: "Ошибка проверки кода. Попробуйте снова." },

        // ===== PREFIX MODAL =====
        "prefix.title":       { en: "PREFIXES",        ru: "ПРЕФИКСЫ" },
        "prefix.gamesPlayed": { en: "Games played:",    ru: "Игр сыграно:" },
        "prefix.preview":     { en: "Preview:",         ru: "Предпросмотр:" },
        "prefix.selectPrefix":{ en: "SELECT PREFIX",    ru: "ВЫБЕРИТЕ ПРЕФИКС" },
        "prefix.selectColor": { en: "SELECT COLOR",     ru: "ВЫБЕРИТЕ ЦВЕТ" },
        "prefix.save":        { en: "SAVE PREFIX",      ru: "СОХРАНИТЬ ПРЕФИКС" },
        "prefix.saving":      { en: "SAVING...",        ru: "СОХРАНЕНИЕ..." },
        "prefix.saved":       { en: "SAVED!",           ru: "СОХРАНЕНО!" },
        "prefix.none":        { en: "None",             ru: "Нет" },
        "prefix.free":        { en: "Free",             ru: "Бесплатно" },

        // ===== STATS MODAL =====
        "stats.loading":      { en: "Loading stats...",          ru: "Загрузка статистики..." },
        "stats.player":       { en: "Player",                    ru: "Игрок" },
        "stats.allTime":      { en: "All Time",                  ru: "За всё время" },
        "stats.30days":       { en: "30 Days",                   ru: "30 дней" },
        "stats.7days":        { en: "7 Days",                    ru: "7 дней" },
        "stats.today":        { en: "Today",                     ru: "Сегодня" },
        "stats.profit":       { en: "PROFIT",                    ru: "ПРИБЫЛЬ" },
        "stats.games":        { en: "GAMES",                     ru: "ИГРЫ" },
        "stats.winRate":      { en: "WIN RATE",                  ru: "ВИНРЕЙТ" },
        "stats.gameHistory":  { en: "GAME HISTORY",              ru: "ИСТОРИЯ ИГР" },
        "stats.noGames":      { en: "No games found",            ru: "Игр не найдено" },
        "stats.noGamesInPeriod": { en: "No games in this period", ru: "Нет игр за этот период" },
        "stats.error":        { en: "Error loading stats",       ru: "Ошибка загрузки статистики" },

        // ===== CHAT =====
        "chat.title":    { en: "LIVE CHAT",          ru: "ЖИВОЙ ЧАТ" },
        "chat.subtitle": { en: "real-time messages", ru: "сообщения в реальном времени" },
        "chat.placeholder": { en: "Message...",      ru: "Сообщение..." },
        "chat.connecting":  { en: "Connecting to server...", ru: "Подключение к серверу..." },

        // ===== AUTH MODAL =====
        "auth.step1Title":   { en: "ROBLOX LOGIN",         ru: "ВХОД ЧЕРЕЗ ROBLOX" },
        "auth.step1Desc":    { en: "Enter your Roblox username to start.", ru: "Введите ваш ник Roblox, чтобы начать." },
        "auth.usernamePh":   { en: "Username...",          ru: "Ник..." },
        "auth.nextStep":     { en: "NEXT STEP",            ru: "ДАЛЕЕ" },
        "auth.verifyTitle":  { en: "VERIFICATION",         ru: "ПРОВЕРКА" },
        "auth.helloLead":    { en: "Hello,",               ru: "Привет," },
        "auth.pasteCode":    { en: "Paste this code into your Roblox", ru: "Вставьте этот код в ваш Roblox" },
        "auth.pasteCodeHtml":{ en: "Paste this code into your Roblox <b>About</b> section:", ru: "Вставьте этот код в раздел <b>About</b> вашего Roblox:" },
        "auth.pasted":       { en: "I PASTED THE CODE",    ru: "Я ВСТАВИЛ КОД" },
        "auth.cancel":       { en: "Cancel / Back",        ru: "Отмена / Назад" }
    };

    function getLang() {
        return localStorage.getItem('mmflip_lang') || 'en';
    }

    function t(key) {
        const entry = TRANSLATIONS[key];
        if (!entry) return key;
        const lang = getLang();
        return entry[lang] || entry.en || key;
    }

    function applyTranslations(root) {
        const scope = root || document;

        scope.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            const val = t(key);
            if (val && val !== key) el.textContent = val;
        });

        scope.querySelectorAll('[data-i18n-html]').forEach(el => {
            const key = el.getAttribute('data-i18n-html');
            const val = t(key);
            if (val && val !== key) el.innerHTML = val;
        });

        scope.querySelectorAll('[data-i18n-attr]').forEach(el => {
            const spec = el.getAttribute('data-i18n-attr');
            if (!spec) return;
            spec.split(',').forEach(pair => {
                const [attr, key] = pair.split(':').map(s => s.trim());
                if (!attr || !key) return;
                const val = t(key);
                if (val && val !== key) el.setAttribute(attr, val);
            });
        });

        scope.querySelectorAll('[data-i18n-dynamic]').forEach(el => {
            const key = el.getAttribute('data-i18n-dynamic');
            const val = t(key);
            if (val && val !== key) el.textContent = val;
        });
    }

    function updateLangUI(lang) {
        const codeEl = document.getElementById('langCurrentCode');
        if (codeEl) codeEl.textContent = lang.toUpperCase();

        document.querySelectorAll('.lang-option, .mobile-lang-option').forEach(el => {
            el.classList.toggle('active', el.getAttribute('data-lang') === lang);
        });

        document.documentElement.lang = lang === 'ru' ? 'ru' : 'en';
    }

    window.setLanguage = function (lang) {
        if (lang !== 'en' && lang !== 'ru') lang = 'en';
        localStorage.setItem('mmflip_lang', lang);
        updateLangUI(lang);
        applyTranslations();
    };

    window.I18N = {
        t: t,
        apply: applyTranslations,
        getLang: getLang
    };

    function init() {
        const lang = getLang();
        updateLangUI(lang);
        applyTranslations();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
