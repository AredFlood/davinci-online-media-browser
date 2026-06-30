(function () {
  const params = new URLSearchParams(window.location.search);
  const apiBase = window.location.origin;
  let token = params.get("token") || localStorage.getItem("mediaBrowserToken") || "";
  let currentLang = localStorage.getItem("mediaBrowserLanguage") || "zh";
  let selectedAsset = null;
  let currentPreviewAspect = 16 / 9;
  let currentPreviewKind = "";
  let currentAssets = [];
  let isBusy = false;
  let activeView = "search";
  const PER_PAGE = 20;
  let searchPage = 1;
  let searchHasMore = false;
  let loadingMore = false;
  let searchCtx = { query: "", category: "all", license: "all" };
  const seenAssetKeys = new Set();
  const TASKS_KEY = "mediaBrowserDownloadTasks";
  const taskEvents = new Map();
  let taskSaveTimer = null;
  let downloadTasks = loadDownloadTasks();
  let creditText = "";
  const selectedTaskIds = new Set();
  let taskGroupBy = localStorage.getItem("mediaBrowserTaskGroup") || "none";
  let toastTimer = null;

  const els = {
    tokenBox: document.getElementById("tokenBox"),
    tokenLabel: document.getElementById("tokenLabel"),
    tokenInput: document.getElementById("tokenInput"),
    brandTitle: document.getElementById("brandTitle"),
    statusText: document.getElementById("statusText"),
    activityBar: document.getElementById("activityBar"),
    commandCenter: document.querySelector(".command-center"),
    queryInput: document.getElementById("queryInput"),
    categorySelect: document.getElementById("categorySelect"),
    licenseSelect: document.getElementById("licenseSelect"),
    languageSelect: document.getElementById("languageSelect"),
    filterGroups: Array.from(document.querySelectorAll(".filter[data-filter]")),
    searchButton: document.getElementById("searchButton"),
    railButtons: Array.from(document.querySelectorAll(".rail-button[data-view]")),
    resultsPanel: document.getElementById("resultsPanel"),
    resultsLoader: document.getElementById("resultsLoader"),
    resultsEnd: document.getElementById("resultsEnd"),
    downloadManager: document.getElementById("downloadManager"),
    downloadManagerTitle: document.getElementById("downloadManagerTitle"),
    downloadManagerSubtitle: document.getElementById("downloadManagerSubtitle"),
    downloadTaskList: document.getElementById("downloadTaskList"),
    clearFinishedButton: document.getElementById("clearFinishedButton"),
    taskGroupBy: document.getElementById("taskGroupBy"),
    selectAllTasks: document.getElementById("selectAllTasks"),
    copyCreditsButton: document.getElementById("copyCreditsButton"),
    creditButton: document.getElementById("creditButton"),
    creditPop: document.getElementById("creditPop"),
    warningList: document.getElementById("warningList"),
    resultsGrid: document.getElementById("resultsGrid"),
    detailPanel: document.getElementById("detailPanel"),
    assetTitle: document.getElementById("assetTitle"),
    collapsePreviewButton: document.getElementById("collapsePreviewButton"),
    previewStage: document.getElementById("previewStage"),
    assetDetails: document.getElementById("assetDetails"),
    downloadButton: document.getElementById("downloadButton"),
    importButton: document.getElementById("importButton"),
    cancelButton: document.getElementById("cancelButton"),
    progressWrap: document.getElementById("progressWrap"),
    progressBar: document.getElementById("progressBar"),
    licenseDialog: document.getElementById("licenseDialog"),
    licenseTitle: document.getElementById("licenseTitle"),
    licenseMessage: document.getElementById("licenseMessage"),
    licenseCancelButton: document.getElementById("licenseCancelButton"),
    licenseOkButton: document.getElementById("licenseOkButton"),
    suppressLicenseCheckbox: document.getElementById("suppressLicenseCheckbox"),
    apiKeyDialog: document.getElementById("apiKeyDialog"),
    apiKeyForm: document.getElementById("apiKeyForm"),
    apiKeyTitle: document.getElementById("apiKeyTitle"),
    apiKeySubtitle: document.getElementById("apiKeySubtitle"),
    apiKeyCloseButton: document.getElementById("apiKeyCloseButton"),
    apiKeyGuideDialogLink: document.getElementById("apiKeyGuideDialogLink"),
    pexelsKeyInput: document.getElementById("pexelsKeyInput"),
    pixabayKeyInput: document.getElementById("pixabayKeyInput"),
    freesoundClientIdInput: document.getElementById("freesoundClientIdInput"),
    freesoundKeyInput: document.getElementById("freesoundKeyInput"),
    freesoundOauthInput: document.getElementById("freesoundOauthInput"),
    pexelsKeyStatus: document.getElementById("pexelsKeyStatus"),
    pixabayKeyStatus: document.getElementById("pixabayKeyStatus"),
    freesoundClientIdStatus: document.getElementById("freesoundClientIdStatus"),
    freesoundKeyStatus: document.getElementById("freesoundKeyStatus"),
    freesoundOauthStatus: document.getElementById("freesoundOauthStatus"),
    sectionVideoImage: document.getElementById("sectionVideoImage"),
    sectionAudio: document.getElementById("sectionAudio"),
    sectionFreeKey: document.getElementById("sectionFreeKey"),
    mixkitEnabledInput: document.getElementById("mixkitEnabledInput"),
    mixkitEnabledLabel: document.getElementById("mixkitEnabledLabel"),
    apiKeyError: document.getElementById("apiKeyError"),
    apiKeyNeverButton: document.getElementById("apiKeyNeverButton"),
    apiKeySaveButton: document.getElementById("apiKeySaveButton"),
    apiKeySuccessDialog: document.getElementById("apiKeySuccessDialog"),
    apiKeySuccessTitle: document.getElementById("apiKeySuccessTitle"),
    apiKeySuccessMessage: document.getElementById("apiKeySuccessMessage"),
    apiKeySuccessOkButton: document.getElementById("apiKeySuccessOkButton"),
  };

  const dict = {
    zh: {
      brand: "达芬奇在线素材浏览器",
      token: "令牌",
      tokenPlaceholder: "Bearer token",
      ready: "就绪",
      searching: "搜索中...",
      previewLoading: "加载预览...",
      loadingResults: "加载素材...",
      previewAction: "预览",
      quickDownload: "下载",
      quickImport: "导入",
      closePreview: "关闭预览",
      missingToken: "缺少 token，请从启动器打开或粘贴 token",
      searchFailed: "搜索失败",
      noPreview: "未加载预览",
      noPreviewAvailable: "没有可用预览",
      selectAsset: "选择一个素材",
      noResults: "没有找到素材",
      results: "{n} 个结果",
      warnings: "警告",
      translated: "{src} -> {dst}",
      source: "来源",
      type: "类型",
      author: "作者",
      unknown: "未知",
      license: "授权",
      licenseUrl: "授权链接",
      originalUrl: "原始链接",
      tags: "关键词",
      download: "下载",
      import: "导入到 Media Pool",
      cancel: "取消",
      downloading: "下载中...",
      downloaded: "已下载",
      downloadFailed: "下载失败",
      cancelled: "已取消",
      importing: "导入中...",
      imported: "已导入 {n} 个素材",
      resolveUnavailable: "已下载，但当前进程无法连接 Resolve",
      importFailed: "导入失败",
      doNotShow: "一个月内不再提示授权确认",
      wfiImported: "已通过 Resolve 面板导入 {n} 个素材",
      continue: "继续",
      all: "全部",
      auto: "自动",
      video: "视频",
      image: "图片",
      music: "音乐",
      sfx: "音效",
      threeD: "3D",
      allLicenses: "全部授权",
      commercialOnly: "仅商用",
      noAttribution: "免署名",
      attributionRequired: "需署名",
      downloads: "下载管理",
      recent: "最近",
      settings: "设置",
      downloadsSubtitle: "后台下载和导入任务",
      noDownloadTasks: "还没有下载任务",
      clearFinished: "清理完成",
      downloadTask: "下载",
      importTask: "下载并导入",
      queued: "排队中",
      failed: "失败",
      taskAdded: "已加入下载管理",
      project: "项目",
      itemName: "项目名",
      mode: "模式",
      localPath: "本地路径",
      importNow: "导入",
      taskHistory: "任务记录",
      copyHint: "点击猫咪即可复制授权信息～",
      copied: "已复制授权信息",
      refreshing: "刷新中...",
      copyCredits: "复制授权信息",
      copySelected: "复制授权 ({n})",
      creditCopied: "已复制 {n} 条授权信息",
      copyFailed: "复制失败",
      groupNone: "不分组",
      groupDate: "按日期",
      groupProject: "按项目",
      selectAll: "全选",
      deselectAll: "取消全选",
      noProject: "未关联项目",
      guideLink: "获取 Key 指南",
      configureKeys: "配置 API Key",
      apiKeyTitle: "连接素材平台",
      apiKeySubtitle: "填写一个或多个 Key，保存时只校验新内容。",
      apiKeyPlaceholderEmpty: "未配置，粘贴后保存",
      apiKeyPlaceholderConfigured: "已配置：{masked}，留空则保持不变",
      fillApiKey: "填写 API Key",
      fillContent: "填写内容",
      sectionVideoImage: "视频 / 图片平台",
      sectionAudio: "音效平台",
      sectionFreeKey: "免 Key 来源",
      mixkitFreeSource: "免 Key 来源",
      deleteKey: "删除 {name}",
      mixkitEnabled: "启用 Mixkit（无需 Key）",
      save: "保存",
      saveValidate: "保存并校验",
      saveWithoutKeys: "暂不填写，直接保存",
      neverPrompt: "永不提示",
      neverPromptDone: "已设置不再自动弹出配置页",
      validatingKeys: "正在校验 API Key...",
      statusReady: "已就绪",
      statusChecking: "校验中",
      statusInvalid: "无效",
      statusDeleting: "待删除",
      keySavedTitle: "连接成功",
      keySavedMessage: "配置已保存，可以开始搜索素材啦。",
      keySaveFailed: "API Key 校验失败",
      configured: "已配置",
      notConfigured: "未配置",
      creditNotEligible: "未完成的任务暂不能复制授权",
    },
    en: {
      brand: "DaVinci Online Media Browser",
      token: "Token",
      tokenPlaceholder: "Bearer token",
      ready: "Ready",
      searching: "Searching...",
      previewLoading: "Loading preview...",
      loadingResults: "Loading assets...",
      previewAction: "Preview",
      quickDownload: "Download",
      quickImport: "Import",
      closePreview: "Close preview",
      missingToken: "Missing token. Open from launcher or paste token.",
      searchFailed: "Search failed",
      noPreview: "No preview loaded",
      noPreviewAvailable: "No preview available",
      selectAsset: "Select an asset",
      noResults: "No assets found",
      results: "{n} results",
      warnings: "Warnings",
      translated: "{src} -> {dst}",
      source: "Source",
      type: "Type",
      author: "Author",
      unknown: "Unknown",
      license: "License",
      licenseUrl: "License URL",
      originalUrl: "Original URL",
      tags: "Tags",
      download: "Download",
      import: "Import to Media Pool",
      cancel: "Cancel",
      downloading: "Downloading...",
      downloaded: "Downloaded",
      downloadFailed: "Download failed",
      cancelled: "Cancelled",
      importing: "Importing...",
      imported: "Imported {n} item(s)",
      resolveUnavailable: "Downloaded, but Resolve is unavailable from this process",
      importFailed: "Import failed",
      doNotShow: "Do not show this license reminder again for one month",
      wfiImported: "Imported {n} item(s) through the Resolve panel",
      continue: "Continue",
      all: "All",
      auto: "Auto",
      video: "Video",
      image: "Image",
      music: "Music",
      sfx: "SFX",
      threeD: "3D",
      allLicenses: "All licenses",
      commercialOnly: "Commercial only",
      noAttribution: "No attribution",
      attributionRequired: "Attribution required",
      downloads: "Downloads",
      recent: "Recent",
      settings: "Settings",
      downloadsSubtitle: "Background downloads and Media Pool imports",
      noDownloadTasks: "No download tasks yet",
      clearFinished: "Clear finished",
      downloadTask: "Download",
      importTask: "Download and import",
      queued: "Queued",
      failed: "Failed",
      taskAdded: "Added to download manager",
      project: "Project",
      itemName: "Item",
      mode: "Mode",
      localPath: "Local path",
      importNow: "Import",
      taskHistory: "Task history",
      copyHint: "Click the cat to copy license info~",
      copied: "Credit copied",
      refreshing: "Refreshing...",
      copyCredits: "Copy credits",
      copySelected: "Copy credits ({n})",
      creditCopied: "Copied {n} credit block(s)",
      copyFailed: "Copy failed",
      groupNone: "Flat",
      groupDate: "By date",
      groupProject: "By project",
      selectAll: "Select all",
      deselectAll: "Deselect all",
      noProject: "No project",
      guideLink: "Get API keys",
      configureKeys: "Configure API keys",
      apiKeyTitle: "Connect Media Platforms",
      apiKeySubtitle: "Enter one or more keys. Only newly entered values are validated on save.",
      apiKeyPlaceholderEmpty: "Not configured. Paste a key and save.",
      apiKeyPlaceholderConfigured: "Configured: {masked}. Leave blank to keep it.",
      fillApiKey: "Enter API key",
      fillContent: "Enter value",
      sectionVideoImage: "Video / Image",
      sectionAudio: "Audio",
      sectionFreeKey: "Key-free Source",
      mixkitFreeSource: "Key-free source",
      deleteKey: "Delete {name}",
      mixkitEnabled: "Enable Mixkit (no key needed)",
      save: "Save",
      saveValidate: "Save and validate",
      saveWithoutKeys: "Save without keys",
      neverPrompt: "Never show again",
      neverPromptDone: "The setup page will no longer pop up automatically",
      validatingKeys: "Validating API keys...",
      statusReady: "Ready",
      statusChecking: "Checking",
      statusInvalid: "Invalid",
      statusDeleting: "To delete",
      keySavedTitle: "Connected",
      keySavedMessage: "Settings saved. You can start searching media.",
      keySaveFailed: "API key validation failed",
      configured: "Configured",
      notConfigured: "Not configured",
      creditNotEligible: "Unfinished tasks cannot be copied yet",
    },
  };

  function t(key, values) {
    let text = (dict[currentLang] && dict[currentLang][key]) || dict.en[key] || key;
    values = values || {};
    Object.keys(values).forEach((name) => {
      text = text.replace("{" + name + "}", String(values[name]));
    });
    return text;
  }

  function applyLanguage() {
    document.documentElement.lang = currentLang === "zh" ? "zh-CN" : "en";
    document.title = t("brand");
    els.brandTitle.textContent = t("brand");
    els.tokenLabel.textContent = t("token");
    els.tokenInput.placeholder = t("tokenPlaceholder");
    els.searchButton.textContent = currentLang === "zh" ? "搜索" : "Search";
    els.downloadButton.textContent = t("download");
    els.importButton.textContent = t("import");
    els.cancelButton.textContent = t("cancel");
    setRailLabel("search", currentLang === "zh" ? "搜索" : "Search");
    setRailLabel("downloads", t("downloads"));
    setRailLabel("recent", t("recent"));
    setRailLabel("settings", t("configureKeys"));
    if (els.apiKeyTitle) els.apiKeyTitle.textContent = t("apiKeyTitle");
    if (els.apiKeySubtitle) els.apiKeySubtitle.textContent = t("apiKeySubtitle");
    if (els.apiKeyGuideDialogLink) els.apiKeyGuideDialogLink.textContent = t("guideLink");
    if (els.apiKeySaveButton && !els.apiKeySaveButton.disabled) els.apiKeySaveButton.textContent = t("save");
    if (els.apiKeyNeverButton) els.apiKeyNeverButton.textContent = t("neverPrompt");
    if (els.sectionVideoImage) els.sectionVideoImage.textContent = t("sectionVideoImage");
    if (els.sectionAudio) els.sectionAudio.textContent = t("sectionAudio");
    if (els.sectionFreeKey) els.sectionFreeKey.textContent = t("sectionFreeKey");
    if (els.mixkitEnabledLabel) els.mixkitEnabledLabel.textContent = t("mixkitFreeSource");
    if (els.apiKeySuccessTitle) els.apiKeySuccessTitle.textContent = t("keySavedTitle");
    if (els.apiKeySuccessMessage) els.apiKeySuccessMessage.textContent = t("keySavedMessage");
    if (els.apiKeySuccessOkButton) els.apiKeySuccessOkButton.textContent = t("continue");
    els.downloadManagerTitle.textContent = t("downloads");
    els.downloadManagerSubtitle.textContent = t("downloadsSubtitle");
    els.clearFinishedButton.textContent = t("clearFinished");
    els.collapsePreviewButton.title = t("closePreview");
    els.queryInput.placeholder = currentLang === "zh" ? "搜索在线素材，支持中文自动翻译" : "Search stock media";
    setSelectLabels(els.categorySelect, {
      all: t("all"),
      auto: t("auto"),
      video: t("video"),
      image: t("image"),
      music: t("music"),
      sfx: t("sfx"),
      "3d": t("threeD"),
    });
    setSelectLabels(els.licenseSelect, {
      all: t("allLicenses"),
      commercial: t("commercialOnly"),
      free: t("noAttribution"),
      attribution: t("attributionRequired"),
    });
    refreshFilters();
    els.suppressLicenseCheckbox.nextElementSibling.textContent = t("doNotShow");
    els.licenseCancelButton.textContent = t("cancel");
    els.licenseOkButton.textContent = t("continue");
    if (!selectedAsset) {
      els.assetTitle.textContent = t("selectAsset");
      els.previewStage.textContent = t("noPreview");
    } else {
      els.assetDetails.textContent = buildDetails(selectedAsset);
    }
    if (els.taskGroupBy) {
      setSelectLabels(els.taskGroupBy, {
        none: t("groupNone"),
        date: t("groupDate"),
        project: t("groupProject"),
      });
    }
    setCreditInfo(selectedAsset);
    if (currentAssets.length) renderResults(currentAssets);
    renderDownloadTasks();
  }

  function setRailLabel(view, label) {
    const button = els.railButtons.find((item) => item.dataset.view === view);
    if (button) button.title = label;
  }

  function setSelectLabels(select, labels) {
    Array.from(select.options).forEach((option) => {
      if (Object.prototype.hasOwnProperty.call(labels, option.value)) {
        option.textContent = labels[option.value];
      }
    });
  }

  // Compact hover-popover filter icons backed by the hidden native selects.
  const FILTER_SELECTS = {
    category: () => els.categorySelect,
    license: () => els.licenseSelect,
    language: () => els.languageSelect,
  };
  const FILTER_DEFAULTS = { category: "auto", license: "all", language: null };

  function setupFilters() {
    els.filterGroups.forEach((group) => {
      const kind = group.dataset.filter;
      const select = FILTER_SELECTS[kind] && FILTER_SELECTS[kind]();
      const menu = group.querySelector(".filter-menu");
      if (!select || !menu) return;
      menu.innerHTML = "";
      Array.from(select.options).forEach((option) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "filter-option";
        button.dataset.value = option.value;
        button.textContent = option.textContent;
        button.addEventListener("click", () => onFilterPick(kind, option.value, group));
        menu.appendChild(button);
      });
    });
    refreshFilters();
  }

  function onFilterPick(kind, value, group) {
    const select = FILTER_SELECTS[kind] && FILTER_SELECTS[kind]();
    if (!select) return;
    select.value = value;
    dismissFilterMenu(group);
    refreshFilters();
    if (kind === "language") {
      saveLanguage(value);
    } else if (els.queryInput.value.trim() && !isBusy) {
      search();
    }
  }

  function dismissFilterMenu(group) {
    // Drop hover/focus state so the popover closes after a pick.
    group.classList.add("dismissed");
    if (document.activeElement && group.contains(document.activeElement)) {
      document.activeElement.blur();
    }
    window.setTimeout(() => group.classList.remove("dismissed"), 240);
  }

  function refreshFilters() {
    els.filterGroups.forEach((group) => {
      const kind = group.dataset.filter;
      const select = FILTER_SELECTS[kind] && FILTER_SELECTS[kind]();
      const menu = group.querySelector(".filter-menu");
      if (!select || !menu) return;
      const current = select.value;
      Array.from(menu.querySelectorAll(".filter-option")).forEach((button) => {
        const option = Array.from(select.options).find((item) => item.value === button.dataset.value);
        if (option) button.textContent = option.textContent;
        button.classList.toggle("active", button.dataset.value === current);
      });
      const activeOption = select.options[select.selectedIndex];
      const icon = group.querySelector(".filter-icon");
      if (icon && activeOption) icon.title = activeOption.textContent;
      const isNonDefault = FILTER_DEFAULTS[kind] !== null && current !== FILTER_DEFAULTS[kind];
      group.classList.toggle("active", isNonDefault);
    });
  }

  function setActivity(isActive) {
    els.activityBar.classList.toggle("hidden", !isActive);
  }

  function setStatus(text) {
    els.statusText.textContent = text;
  }

  function setBusy(nextBusy) {
    isBusy = nextBusy;
    els.searchButton.disabled = nextBusy;
    els.downloadButton.disabled = nextBusy || !selectedAsset;
    els.importButton.disabled = nextBusy || !selectedAsset;
  }

  function setView(view) {
    if (view === "recent") {
      refreshCurrentView();
      return;
    }
    if (view === "settings") {
      openApiKeyDialog(false);
      return;
    }
    if (view !== "search" && view !== "downloads") {
      setStatus(view === "recent" ? t("taskHistory") : t("settings"));
      return;
    }
    activeView = view;
    els.resultsPanel.classList.toggle("hidden", view !== "search");
    els.downloadManager.classList.toggle("hidden", view !== "downloads");
    if (view !== "search") closePreviewPanel();
    els.railButtons.forEach((button) => {
      button.classList.toggle("active", button.dataset.view === view);
    });
    renderDownloadTasks();
  }

  function authHeaders(extra) {
    return Object.assign({ Authorization: "Bearer " + token }, extra || {});
  }

  async function apiJson(path, options) {
    if (!token) throw new Error(t("missingToken"));
    const response = await fetch(apiBase + path, Object.assign({
      headers: authHeaders({ "Content-Type": "application/json" }),
    }, options || {}));
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.message || payload.error || response.statusText);
    }
    return payload;
  }

  async function loadSettings() {
    if (!token) return;
    try {
      const payload = await apiJson("/settings");
      const lang = payload.settings && payload.settings.language;
      if (lang === "zh" || lang === "en") {
        currentLang = lang;
        localStorage.setItem("mediaBrowserLanguage", lang);
      }
      els.languageSelect.value = currentLang;
    } catch (_error) {
      // Keep local defaults.
    }
    applyLanguage();
  }

  async function saveLanguage(lang) {
    currentLang = lang;
    localStorage.setItem("mediaBrowserLanguage", lang);
    applyLanguage();
    if (!token) return;
    try {
      await apiJson("/settings", {
        method: "POST",
        body: JSON.stringify({ settings: { language: lang } }),
      });
    } catch (_error) {
      // Local language still works if settings are unavailable.
    }
  }

  async function loadApiKeyStatus() {
    if (!token) return null;
    try {
      return await apiJson("/api-keys");
    } catch (_error) {
      return null;
    }
  }

  async function maybePromptForApiKeys() {
    const payload = await loadApiKeyStatus();
    if (payload && payload.prompt_required) {
      openApiKeyDialog(true, payload);
    }
  }

  async function openApiKeyDialog(isFirstRun, cachedPayload) {
    if (!els.apiKeyDialog) return;
    const payload = cachedPayload || await loadApiKeyStatus();
    resetApiKeyForm(payload);
    els.apiKeyDialog.dataset.firstRun = isFirstRun ? "1" : "0";
    if (typeof els.apiKeyDialog.showModal === "function") {
      if (!els.apiKeyDialog.open) els.apiKeyDialog.showModal();
    } else {
      window.alert(t("configureKeys"));
    }
  }

  const API_KEY_INPUT_IDS = {
    pexels_api_key: "pexelsKeyInput",
    pixabay_api_key: "pixabayKeyInput",
    freesound_client_id: "freesoundClientIdInput",
    freesound_api_key: "freesoundKeyInput",
    freesound_oauth_access_token: "freesoundOauthInput",
  };
  const pendingDeletes = new Set();
  let lastApiKeyPayload = null;

  function delay(ms) {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
  }

  function apiKeyFields() {
    return Object.keys(API_KEY_INPUT_IDS).map((name) => {
      const input = document.getElementById(API_KEY_INPUT_IDS[name]);
      if (!input) return null;
      const row = input.closest("[data-field]");
      return {
        name: name,
        input: input,
        row: row,
        wrap: input.closest(".key-input-wrap"),
        status: row ? row.querySelector(".status-pill") : null,
      };
    }).filter(Boolean);
  }

  function fieldByName(name) {
    return apiKeyFields().find((field) => field.name === name) || null;
  }

  function defaultPlaceholder(name) {
    return name === "pexels_api_key" || name === "pixabay_api_key" ? t("fillApiKey") : t("fillContent");
  }

  function clearFieldState(field) {
    if (field.wrap) field.wrap.classList.remove("validating", "field-ready", "field-error");
  }

  function setFieldStatus(field, state, masked) {
    const pill = field.status;
    if (!pill) return;
    pill.classList.remove("is-ready", "is-error", "is-checking", "is-deleting");
    if (state === "configured") {
      pill.textContent = t("configured");
      pill.classList.add("is-ready");
    } else if (state === "ready") {
      pill.textContent = t("statusReady");
      pill.classList.add("is-ready");
    } else if (state === "checking") {
      pill.textContent = t("statusChecking");
      pill.classList.add("is-checking");
    } else if (state === "error") {
      pill.textContent = t("statusInvalid");
      pill.classList.add("is-error");
    } else if (state === "deleting") {
      pill.textContent = t("statusDeleting");
      pill.classList.add("is-deleting");
    } else {
      pill.textContent = t("notConfigured");
    }
    if (masked) pill.title = masked;
  }

  function resetApiKeyForm(payload) {
    lastApiKeyPayload = payload || null;
    const masked = (payload && payload.masked) || {};
    const configured = (payload && payload.configured) || {};
    pendingDeletes.clear();
    apiKeyFields().forEach((field) => {
      field.input.value = "";
      field.input.dataset.lastValidated = "";
      clearFieldState(field);
      if (field.row) field.row.classList.remove("to-delete");
      field.input.placeholder = configured[field.name]
        ? t("apiKeyPlaceholderConfigured", { masked: masked[field.name] || "" })
        : defaultPlaceholder(field.name);
      setFieldStatus(field, configured[field.name] ? "configured" : "empty", masked[field.name]);
    });
    if (els.mixkitEnabledInput) {
      els.mixkitEnabledInput.checked = !payload || !payload.configured || payload.configured.mixkit_enabled !== false;
    }
    hideApiKeyError();
  }

  // Auto-validate one field after the user finishes it: dither sweep, then the
  // box turns into a blue (ready) or red (invalid) flowing-light border.
  async function validateField(field) {
    if (!token || !field || pendingDeletes.has(field.name)) return;
    const value = field.input.value.trim();
    if (!value || value.startsWith("•")) {
      clearFieldState(field);
      const configured = lastApiKeyPayload && lastApiKeyPayload.configured && lastApiKeyPayload.configured[field.name];
      setFieldStatus(field, configured ? "configured" : "empty");
      return;
    }
    if (field.input.dataset.lastValidated === value && field.wrap
      && (field.wrap.classList.contains("field-ready") || field.wrap.classList.contains("field-error"))) {
      return;
    }
    field.input.dataset.lastValidated = value;
    if (field.wrap) {
      field.wrap.classList.remove("field-ready", "field-error");
      field.wrap.classList.add("validating");
    }
    setFieldStatus(field, "checking");
    const [result] = await Promise.all([
      apiJson("/validate-key", {
        method: "POST",
        body: JSON.stringify({ field: field.name, value: value }),
      }).catch((error) => ({ ok: false, error: String((error && error.message) || error) })),
      delay(950),
    ]);
    if (field.wrap) {
      field.wrap.classList.remove("validating");
      field.wrap.classList.add(result.ok ? "field-ready" : "field-error");
    }
    setFieldStatus(field, result.ok ? "ready" : "error");
  }

  function toggleDeleteField(name) {
    const field = fieldByName(name);
    if (!field) return;
    if (pendingDeletes.has(name)) {
      pendingDeletes.delete(name);
      if (field.row) field.row.classList.remove("to-delete");
      clearFieldState(field);
      const configured = lastApiKeyPayload && lastApiKeyPayload.configured && lastApiKeyPayload.configured[name];
      setFieldStatus(field, field.input.value.trim() ? "ready" : (configured ? "configured" : "empty"));
    } else {
      pendingDeletes.add(name);
      if (field.row) field.row.classList.add("to-delete");
      clearFieldState(field);
      setFieldStatus(field, "deleting");
    }
  }

  async function saveApiKeys() {
    if (!token) return;
    const keys = {};
    const deletes = {};
    apiKeyFields().forEach((field) => {
      const value = field.input.value.trim();
      if (value && !pendingDeletes.has(field.name)) keys[field.name] = value;
      deletes[field.name] = pendingDeletes.has(field.name);
    });
    keys.mixkit_enabled = Boolean(els.mixkitEnabledInput && els.mixkitEnabledInput.checked);

    hideApiKeyError();
    setApiKeySaving(true);
    setStatus(t("validatingKeys"));
    try {
      const response = await fetch(apiBase + "/api-keys", {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ keys: keys, delete: deletes }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw payload;
      }
      if (els.apiKeyDialog && els.apiKeyDialog.open) els.apiKeyDialog.close("saved");
      showApiKeySuccess();
      setStatus(t("keySavedMessage"));
    } catch (error) {
      const message = formatApiKeyError(error);
      showApiKeyError(message);
      window.alert(t("keySaveFailed") + "\n\n" + message);
      setStatus(t("keySaveFailed"));
    } finally {
      setApiKeySaving(false);
    }
  }

  function setApiKeySaving(isSaving) {
    if (els.apiKeyNeverButton) els.apiKeyNeverButton.disabled = isSaving;
    if (els.apiKeySaveButton) {
      els.apiKeySaveButton.disabled = isSaving;
      els.apiKeySaveButton.textContent = isSaving ? t("validatingKeys") : t("save");
    }
  }

  // "Never show again": stop the auto-popup without writing any keys. The settings
  // (⚙) button still opens this dialog manually afterwards.
  async function neverPromptApiKeys() {
    if (token) {
      try {
        await apiJson("/settings", {
          method: "POST",
          body: JSON.stringify({ settings: { api_keys_prompted: true } }),
        });
      } catch (_error) {
        // Best effort; the dialog still closes so the user isn't stuck.
      }
    }
    if (els.apiKeyDialog && els.apiKeyDialog.open) els.apiKeyDialog.close("never");
    showToast(t("neverPromptDone"));
  }

  function formatApiKeyError(error) {
    const errors = error && error.errors;
    if (errors && typeof errors === "object") {
      return Object.keys(errors).map((key) => key + ": " + errors[key]).join("\n");
    }
    return String((error && (error.message || error.error)) || error || t("keySaveFailed"));
  }

  function showApiKeyError(message) {
    if (!els.apiKeyError) return;
    els.apiKeyError.textContent = message;
    els.apiKeyError.classList.remove("hidden");
  }

  function hideApiKeyError() {
    if (!els.apiKeyError) return;
    els.apiKeyError.textContent = "";
    els.apiKeyError.classList.add("hidden");
  }

  function showApiKeySuccess() {
    if (els.apiKeySuccessTitle) els.apiKeySuccessTitle.textContent = t("keySavedTitle");
    if (els.apiKeySuccessMessage) els.apiKeySuccessMessage.textContent = t("keySavedMessage");
    if (els.apiKeySuccessDialog && typeof els.apiKeySuccessDialog.showModal === "function") {
      if (!els.apiKeySuccessDialog.open) els.apiKeySuccessDialog.showModal();
    } else {
      showToast(t("keySavedMessage"));
    }
  }

  function searchPath(query, category, license, page) {
    return "/search?query=" + encodeURIComponent(query)
      + "&category=" + encodeURIComponent(category)
      + "&license_filter=" + encodeURIComponent(license)
      + "&page=" + page
      + "&per_page=" + PER_PAGE;
  }

  async function search() {
    const query = els.queryInput.value.trim();
    if (!query) return;
    setView("search");
    setBusy(true);
    setActivity(true);
    setStatus(t("searching"));
    selectedAsset = null;
    currentAssets = [];
    seenAssetKeys.clear();
    searchPage = 1;
    searchHasMore = false;
    loadingMore = false;
    searchCtx = { query: query, category: els.categorySelect.value, license: els.licenseSelect.value };
    closePreviewPanel();
    renderPreview(null);
    els.downloadButton.disabled = true;
    els.importButton.disabled = true;
    setResultsEnd(false);
    renderSkeletons();
    setWarnings([]);
    try {
      const payload = await apiJson(searchPath(query, searchCtx.category, searchCtx.license, 1));
      const fresh = dedupeNewAssets(payload.assets || []);
      currentAssets = fresh;
      renderResults(currentAssets);
      setWarnings(payload.warnings || []);
      searchHasMore = (payload.total || 0) > 0 && fresh.length > 0;
      if (!searchHasMore) setResultsEnd(currentAssets.length > 0);
      const translated = payload.translated ? " · " + t("translated", { src: payload.query, dst: payload.effective_query }) : "";
      setStatus(t("results", { n: payload.shown || 0 }) + translated);
    } catch (error) {
      setStatus(t("searchFailed") + ": " + error.message);
      els.resultsGrid.innerHTML = "";
    } finally {
      setActivity(false);
      setBusy(false);
    }
  }

  function dedupeNewAssets(assets) {
    const fresh = [];
    assets.forEach((asset) => {
      const key = (asset.source || "") + ":" + (asset.id || "");
      if (seenAssetKeys.has(key)) return;
      seenAssetKeys.add(key);
      fresh.push(asset);
    });
    return fresh;
  }

  async function loadMoreResults() {
    if (loadingMore || !searchHasMore || activeView !== "search") return;
    loadingMore = true;
    setResultsLoading(true);
    const nextPage = searchPage + 1;
    try {
      const payload = await apiJson(searchPath(searchCtx.query, searchCtx.category, searchCtx.license, nextPage));
      const fresh = dedupeNewAssets(payload.assets || []);
      searchPage = nextPage;
      if ((payload.total || 0) === 0 || fresh.length === 0) {
        searchHasMore = false;
        setResultsEnd(true);
      } else {
        currentAssets = currentAssets.concat(fresh);
        appendResults(fresh);
        setStatus(t("results", { n: currentAssets.length }));
      }
    } catch (_error) {
      // Stop auto-loading on error; the user can scroll/retry.
      searchHasMore = false;
    } finally {
      loadingMore = false;
      setResultsLoading(false);
    }
  }

  function setResultsEnd(show) {
    if (els.resultsEnd) els.resultsEnd.classList.toggle("hidden", !show);
  }

  function setResultsLoading(show) {
    if (els.resultsLoader) els.resultsLoader.classList.toggle("hidden", !show);
  }

  function onResultsScroll() {
    const panel = els.resultsPanel;
    if (!panel) return;
    if (panel.scrollTop + panel.clientHeight >= panel.scrollHeight - 280) {
      loadMoreResults();
    }
  }

  async function refreshCurrentView() {
    setStatus(t("refreshing"));
    if (activeView === "downloads") {
      await loadPersistedDownloadTasks();
      renderDownloadTasks();
      setStatus(t("downloads"));
      return;
    }
    if (els.queryInput.value.trim()) {
      search();
      return;
    }
    if (currentAssets.length) {
      renderResults(currentAssets);
      setStatus(t("results", { n: currentAssets.length }));
      return;
    }
    renderDownloadTasks();
    setStatus(t("ready"));
  }

  function setWarnings(warnings) {
    if (!warnings.length) {
      els.warningList.classList.add("hidden");
      els.warningList.textContent = "";
      return;
    }
    els.warningList.classList.remove("hidden");
    els.warningList.textContent = t("warnings") + ":\n" + warnings.map((item) => {
      return "- " + item.source + ": " + item.message.slice(0, 180);
    }).join("\n");
  }

  function createCard(asset) {
    const card = document.createElement("article");
    card.className = "card";
    card.addEventListener("click", () => selectAsset(asset, card));
    card.style.setProperty("--thumb-ratio", previewAspectFromAsset(asset));
    if (asset.kind === "music" || asset.kind === "sfx") {
      card.classList.add("audio-card");
    }

    const thumb = document.createElement("div");
    thumb.className = "thumb";
    if (asset.thumbnail_url) {
      const img = document.createElement("img");
      img.loading = "lazy";
      card.classList.add("thumb-loading");
      img.addEventListener("load", () => card.classList.remove("thumb-loading"));
      setImageSourceWithFallback(img, asset.thumbnail_url, () => card.classList.remove("thumb-loading"));
      thumb.appendChild(img);
    } else {
      const placeholder = document.createElement("span");
      placeholder.className = "thumb-placeholder";
      placeholder.textContent = displayKind(asset.kind);
      thumb.appendChild(placeholder);
    }

    const source = document.createElement("span");
    source.className = "badge";
    source.textContent = asset.source;

    if (asset.license_badge) {
      const license = document.createElement("span");
      license.className = "badge license " + asset.license_badge;
      license.textContent = asset.license_badge;
      card.appendChild(license);
    }

    const title = document.createElement("div");
    title.className = "card-title";
    title.textContent = asset.title || asset.id;

    const meta = document.createElement("div");
    meta.className = "card-meta";
    const kindSpan = document.createElement("span");
    kindSpan.textContent = displayKind(asset.kind);
    const durSpan = document.createElement("span");
    durSpan.textContent = formatDuration(asset.duration);
    meta.appendChild(kindSpan);
    meta.appendChild(durSpan);

    const actions = document.createElement("div");
    actions.className = "card-actions";
    actions.appendChild(cardActionButton(t("previewAction"), () => selectAsset(asset, card)));
    actions.appendChild(cardActionButton(t("quickDownload"), () => {
      selectAsset(asset, card);
      downloadSelected();
    }, !canUseAsset(asset)));
    actions.appendChild(cardActionButton(t("quickImport"), () => {
      selectAsset(asset, card);
      importSelected();
    }, !canUseAsset(asset)));

    card.appendChild(thumb);
    card.appendChild(source);
    card.appendChild(title);
    card.appendChild(meta);
    card.appendChild(actions);
    return card;
  }

  function renderResults(assets) {
    els.resultsGrid.innerHTML = "";
    if (!assets.length) {
      const empty = document.createElement("div");
      empty.className = "empty-state";
      empty.textContent = t("noResults");
      els.resultsGrid.appendChild(empty);
      return;
    }
    assets.forEach((asset) => els.resultsGrid.appendChild(createCard(asset)));
  }

  function appendResults(assets) {
    assets.forEach((asset) => els.resultsGrid.appendChild(createCard(asset)));
  }

  function cardActionButton(label, handler, disabled) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.disabled = Boolean(disabled);
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      if (!button.disabled && !isBusy) handler();
    });
    return button;
  }

  function renderSkeletons(count) {
    els.resultsGrid.innerHTML = "";
    const total = count || 10;
    for (let index = 0; index < total; index += 1) {
      const card = document.createElement("article");
      card.className = "card skeleton-card";
      card.setAttribute("aria-label", t("loadingResults"));
      card.innerHTML = "<div class=\"thumb skeleton\"></div><div class=\"skeleton line wide\"></div><div class=\"skeleton line\"></div>";
      els.resultsGrid.appendChild(card);
    }
  }

  function selectAsset(asset, card) {
    selectedAsset = asset;
    document.querySelectorAll(".card.selected").forEach((item) => item.classList.remove("selected"));
    if (card) card.classList.add("selected");
    openPreviewPanel();
    els.assetTitle.textContent = asset.title || asset.id;
    els.assetDetails.textContent = buildDetails(asset);
    setCreditInfo(asset);
    const canDownload = canUseAsset(asset);
    els.downloadButton.disabled = !canDownload;
    els.importButton.disabled = !canDownload;
    renderPreview(asset);
  }

  function canUseAsset(asset) {
    return Boolean(asset && (asset.download_url || asset.preview_url));
  }

  function openPreviewPanel() {
    els.detailPanel.classList.remove("collapsed");
    els.detailPanel.classList.add("open");
  }

  function closePreviewPanel() {
    els.detailPanel.classList.remove("open");
    els.detailPanel.classList.add("collapsed");
  }

  function renderPreview(asset) {
    els.previewStage.innerHTML = "";
    els.previewStage.classList.remove("loading");
    els.previewStage.classList.remove("preview-image", "preview-video", "preview-audio");
    if (!asset) {
      currentPreviewAspect = 16 / 9;
      currentPreviewKind = "";
      fitPreviewStage(currentPreviewAspect, currentPreviewKind);
      els.previewStage.textContent = t("noPreview");
      return;
    }
    const url = asset.preview_url || asset.thumbnail_url || asset.source_url;
    if (!url) {
      currentPreviewAspect = previewAspectFromAsset(asset);
      currentPreviewKind = String(asset.kind || "");
      fitPreviewStage(currentPreviewAspect, currentPreviewKind);
      els.previewStage.textContent = t("noPreviewAvailable");
      return;
    }
    currentPreviewKind = String(asset.kind || "");
    currentPreviewAspect = previewAspectFromAsset(asset);
    els.previewStage.classList.add("preview-" + (currentPreviewKind === "video" ? "video" : currentPreviewKind === "image" ? "image" : "audio"));
    fitPreviewStage(currentPreviewAspect, currentPreviewKind);
    els.previewStage.dataset.loading = t("previewLoading");
    els.previewStage.classList.add("loading");
    if (asset.kind === "image") {
      const img = document.createElement("img");
      img.addEventListener("load", () => {
        els.previewStage.classList.remove("loading");
        if (img.naturalWidth && img.naturalHeight) {
          currentPreviewAspect = img.naturalWidth / img.naturalHeight;
          fitPreviewStage(currentPreviewAspect, currentPreviewKind);
        }
      }, { once: true });
      setImageSourceWithFallback(img, url, () => {
        els.previewStage.classList.remove("loading");
        els.previewStage.textContent = t("noPreviewAvailable");
      });
      els.previewStage.appendChild(img);
    } else if (asset.kind === "video") {
      const video = document.createElement("video");
      video.controls = true;
      video.autoplay = true;
      video.preload = "auto";
      video.src = url;
      els.previewStage.appendChild(video);
      bindPreviewMedia(video);
    } else {
      const audio = document.createElement("audio");
      audio.controls = true;
      audio.autoplay = true;
      audio.preload = "auto";
      audio.src = url;
      els.previewStage.appendChild(audio);
      bindPreviewMedia(audio);
    }
  }

  function bindPreviewMedia(media) {
    const clearLoading = () => els.previewStage.classList.remove("loading");
    const updateMediaSize = () => {
      if (media.videoWidth && media.videoHeight) {
        currentPreviewAspect = media.videoWidth / media.videoHeight;
        fitPreviewStage(currentPreviewAspect, currentPreviewKind);
      }
    };
    const tryPlay = () => {
      if (media.readyState >= 2) {
        clearLoading();
      }
      const promise = media.play();
      if (promise && typeof promise.catch === "function") {
        promise.catch(() => {
          // Browser policy can still block autoplay; controls remain visible.
        });
      }
    };
    media.addEventListener("loadedmetadata", () => {
      clearLoading();
      updateMediaSize();
    }, { once: true });
    media.addEventListener("canplay", tryPlay, { once: true });
    media.addEventListener("error", clearLoading, { once: true });
    tryPlay();
  }

  function setImageSourceWithFallback(img, url, onFinalError) {
    let usedProxy = false;
    img.referrerPolicy = "no-referrer";
    img.addEventListener("error", () => {
      if (!usedProxy && url) {
        usedProxy = true;
        img.src = thumbnailProxyUrl(url);
        return;
      }
      if (onFinalError) onFinalError();
    });
    img.src = url;
  }

  function thumbnailProxyUrl(url) {
    return apiBase + "/thumbnail?token=" + encodeURIComponent(token)
      + "&url=" + encodeURIComponent(url);
  }

  function previewAspectFromAsset(asset) {
    const width = Number(asset && asset.width);
    const height = Number(asset && asset.height);
    if (width > 0 && height > 0) {
      return clamp(width / height, 0.28, 4);
    }
    if (asset && asset.kind === "image") return 4 / 3;
    if (asset && asset.kind === "video") return 16 / 9;
    return 16 / 9;
  }

  function fitPreviewStage(aspect, kind) {
    const normalizedAspect = clamp(Number(aspect) || 16 / 9, 0.28, 4);
    currentPreviewAspect = normalizedAspect;
    currentPreviewKind = kind || currentPreviewKind || "";
    window.requestAnimationFrame(() => {
      const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 720;
      const panelWidth = Math.max(260, els.detailPanel.clientWidth || 430);
      const chromeHeight = 184;
      if (currentPreviewKind && currentPreviewKind !== "image" && currentPreviewKind !== "video") {
        els.previewStage.style.width = "100%";
        els.previewStage.style.height = "96px";
        return;
      }

      const availableHeight = Math.max(180, viewportHeight - chromeHeight);
      const horizontalLimit = Math.max(220, panelWidth - 26);
      let width = horizontalLimit;
      let height = Math.round(width / normalizedAspect);

      if (height > availableHeight) {
        height = availableHeight;
        width = Math.round(height * normalizedAspect);
      }

      if (normalizedAspect < 0.8) {
        width = Math.min(width, Math.round(height * normalizedAspect));
      }

      const minHeight = 156;
      height = clamp(height, minHeight, availableHeight);
      width = clamp(width, 140, horizontalLimit);
      els.previewStage.style.width = width + "px";
      els.previewStage.style.height = height + "px";
    });
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  async function confirmLicense(asset) {
    const decision = await apiJson("/license/evaluate", {
      method: "POST",
      body: JSON.stringify({ assets: [asset] }),
    });
    if (!decision.allowed) {
      window.alert(decision.title + "\n\n" + decision.message);
      return false;
    }
    const settings = await apiJson("/settings");
    if (!decision.requires_confirmation || settings.show_license_notice === false) {
      return true;
    }
    els.licenseTitle.textContent = decision.title;
    els.licenseMessage.textContent = decision.message;
    els.suppressLicenseCheckbox.checked = false;
    const result = await new Promise((resolve) => {
      if (typeof els.licenseDialog.showModal === "function") {
        els.licenseDialog.addEventListener("close", () => resolve(els.licenseDialog.returnValue), { once: true });
        els.licenseDialog.showModal();
      } else {
        resolve(window.confirm(decision.title + "\n\n" + decision.message) ? "ok" : "cancel");
      }
    });
    if (result !== "ok") return false;
    if (els.suppressLicenseCheckbox.checked) {
      await apiJson("/settings", {
        method: "POST",
        body: JSON.stringify({ suppress_license_notice_days: 30 }),
      });
    }
    return true;
  }

  async function downloadSelected() {
    if (!selectedAsset) return;
    if (!(await confirmLicense(selectedAsset))) return;
    queueDownload(selectedAsset, "download");
  }

  async function importSelected() {
    if (!selectedAsset) return;
    if (!(await confirmLicense(selectedAsset))) return;
    queueDownload(selectedAsset, "import");
  }

  function loadDownloadTasks() {
    try {
      const raw = localStorage.getItem(TASKS_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return normalizeDownloadTasks(parsed);
    } catch (_error) {
      return [];
    }
  }

  function normalizeDownloadTasks(tasks) {
    if (!Array.isArray(tasks)) return [];
    return tasks.filter((task) => task && typeof task === "object").map((task) => {
      return Object.assign({
        id: "",
        jobId: "",
        mode: "download",
        title: "",
        source: "",
        kind: "",
        projectName: "",
        asset: {},
        status: "downloaded",
        progress: 100,
        done: 0,
        total: 0,
        path: "",
        error: "",
        importedCount: 0,
        createdAt: "",
        completedAt: "",
        updatedAt: "",
      }, task);
    }).filter((task) => task.id).slice(0, 80);
  }

  function persistDownloadTasks() {
    try {
      localStorage.setItem(TASKS_KEY, JSON.stringify(downloadTasks.slice(0, 80)));
    } catch (_error) {
      // A full localStorage should not break downloads.
    }
    scheduleTaskSave();
  }

  function scheduleTaskSave() {
    if (!token) return;
    if (taskSaveTimer) window.clearTimeout(taskSaveTimer);
    taskSaveTimer = window.setTimeout(() => {
      taskSaveTimer = null;
      saveDownloadTasksToServer();
    }, 350);
  }

  async function saveDownloadTasksToServer() {
    if (!token) return;
    try {
      await apiJson("/tasks", {
        method: "POST",
        body: JSON.stringify({ tasks: downloadTasks.slice(0, 80) }),
      });
    } catch (_error) {
      // Local cache remains available if the service is shutting down.
    }
  }

  async function loadPersistedDownloadTasks() {
    if (!token) return;
    try {
      const payload = await apiJson("/tasks");
      closeAllTaskEvents();
      downloadTasks = normalizeDownloadTasks(payload.tasks || []);
      try {
        localStorage.setItem(TASKS_KEY, JSON.stringify(downloadTasks.slice(0, 80)));
      } catch (_error) {
        // Server-side persistence is the source of truth.
      }
      renderDownloadTasks();
      resumeActiveTasks();
    } catch (_error) {
      resumeActiveTasks();
    }
  }

  function createDownloadTask(asset, mode) {
    const now = new Date().toISOString();
    return {
      id: "task_" + Date.now().toString(36) + "_" + Math.random().toString(36).slice(2, 8),
      jobId: "",
      mode: mode,
      title: asset.display_title || asset.title || asset.id || t("unknown"),
      source: asset.source || "",
      kind: asset.kind || "",
      projectName: "",
      asset: asset,
      status: "queued",
      progress: 0,
      done: 0,
      total: 0,
      path: "",
      error: "",
      importedCount: 0,
      createdAt: now,
      completedAt: "",
      updatedAt: now,
    };
  }

  async function queueDownload(asset, mode) {
    const task = createDownloadTask(asset, mode);
    downloadTasks.unshift(task);
    downloadTasks = downloadTasks.slice(0, 80);
    persistDownloadTasks();
    renderDownloadTasks();
    setStatus(t("taskAdded") + ": " + task.title);

    resolveProjectName().then((name) => {
      if (name) updateTask(task.id, { projectName: name });
    });

    try {
      const payload = await apiJson("/download", {
        method: "POST",
        body: JSON.stringify({ asset: asset }),
      });
      updateTask(task.id, {
        jobId: payload.job_id,
        status: "downloading",
      });
      listenTaskDownload(task.id, payload.job_id);
    } catch (error) {
      updateTask(task.id, {
        status: "failed",
        error: t("downloadFailed") + ": " + error.message,
      });
      setStatus(t("downloadFailed") + ": " + error.message);
    }
  }

  function listenTaskDownload(taskId, jobId) {
    closeTaskEvents(taskId);
    const url = apiBase + "/download/events?job_id=" + encodeURIComponent(jobId)
      + "&token=" + encodeURIComponent(token);
    const events = new EventSource(url);
    taskEvents.set(taskId, events);

    events.addEventListener("queued", () => {
      updateTask(taskId, { status: "queued", progress: 0 });
    });
    events.addEventListener("started", () => {
      updateTask(taskId, { status: "downloading" });
    });
    events.addEventListener("progress", (event) => {
      const data = JSON.parse(event.data);
      const total = Number(data.total) || 0;
      const done = Number(data.done) || 0;
      const progress = total > 0 ? Math.min(99, Math.round(done / total * 100)) : 0;
      updateTask(taskId, {
        status: "downloading",
        done: done,
        total: total,
        progress: progress,
      });
    });
    events.addEventListener("completed", (event) => {
      const data = JSON.parse(event.data);
      closeTaskEvents(taskId);
      updateTask(taskId, {
        status: "downloaded",
        path: data.path || "",
        progress: 100,
        completedAt: new Date().toISOString(),
      });
      const task = getTask(taskId);
      if (task && task.mode === "import") {
        importDownloadedTask(taskId);
      } else if (task) {
        setStatus(t("downloaded") + ": " + task.title);
      }
    });
    events.addEventListener("failed", (event) => {
      const data = JSON.parse(event.data);
      closeTaskEvents(taskId);
      updateTask(taskId, {
        status: "failed",
        error: data.message || t("downloadFailed"),
      });
      setStatus(t("downloadFailed") + ": " + (data.message || ""));
    });
    events.addEventListener("cancelled", () => {
      closeTaskEvents(taskId);
      updateTask(taskId, { status: "cancelled" });
      setStatus(t("cancelled"));
    });
    events.onerror = () => {
      if (events.readyState === EventSource.CLOSED) {
        closeTaskEvents(taskId);
      }
    };
  }

  async function importDownloadedTask(taskId) {
    const task = getTask(taskId);
    if (!task) return;
    updateTask(taskId, { status: "importing", progress: 100, error: "" });
    setStatus(t("importing"));
    try {
      const payload = await importAssetPath(task.asset, task.path);
      updateTask(taskId, {
        status: "imported",
        importedCount: payload.imported_count || 0,
        projectName: payload.project_name || task.projectName || "",
        completedAt: task.completedAt || new Date().toISOString(),
      });
      setStatus(t("wfiImported", { n: payload.imported_count || 0 }));
    } catch (error) {
      updateTask(taskId, {
        status: "failed",
        error: t("importFailed") + ": " + error.message,
      });
      setStatus(t("importFailed") + ": " + error.message);
    }
  }

  async function importAssetPath(asset, localPath) {
    if (!localPath) {
      throw new Error("Downloaded file path is missing.");
    }
    if (hasWorkflowIntegration()) {
      return window.resolveWfi.importMedia({
        paths: [localPath],
        metadata: asset.resolve_metadata || {},
        asset: asset,
      });
    }

    const payload = await apiJson("/import", {
      method: "POST",
      body: JSON.stringify({ assets: [asset], paths: [localPath] }),
    });
    if (!payload.resolve_available) {
      throw new Error(t("resolveUnavailable") + (payload.warning ? ": " + payload.warning : ""));
    }
    return payload;
  }

  async function cancelTask(taskId) {
    const task = getTask(taskId);
    if (!task) return;
    closeTaskEvents(taskId);
    if (task.jobId) {
      try {
        await apiJson("/cancel", {
          method: "POST",
          body: JSON.stringify({ job_id: task.jobId }),
        });
      } catch (_error) {
        // Marking the local task cancelled is still useful if the SSE already closed.
      }
    }
    updateTask(taskId, { status: "cancelled" });
  }

  function cancelDownload() {
    const activeTask = downloadTasks.find((task) => task.status === "queued" || task.status === "downloading");
    if (activeTask) cancelTask(activeTask.id);
  }

  function closeTaskEvents(taskId) {
    const events = taskEvents.get(taskId);
    if (events) {
      events.close();
      taskEvents.delete(taskId);
    }
  }

  function closeAllTaskEvents() {
    Array.from(taskEvents.keys()).forEach((taskId) => closeTaskEvents(taskId));
  }

  function getTask(taskId) {
    return downloadTasks.find((task) => task.id === taskId) || null;
  }

  function updateTask(taskId, patch) {
    const task = getTask(taskId);
    if (!task) return;
    Object.assign(task, patch, { updatedAt: new Date().toISOString() });
    persistDownloadTasks();
    renderDownloadTasks();
  }

  function clearFinishedTasks() {
    const terminal = new Set(["downloaded", "imported", "failed", "cancelled"]);
    downloadTasks = downloadTasks.filter((task) => !terminal.has(task.status));
    persistDownloadTasks();
    renderDownloadTasks();
  }

  function renderDownloadTasks() {
    if (!els.downloadTaskList) return;
    // Drop selections whose tasks no longer exist.
    const ids = new Set(downloadTasks.filter(isCreditEligibleTask).map((task) => task.id));
    Array.from(selectedTaskIds).forEach((id) => {
      if (!ids.has(id)) selectedTaskIds.delete(id);
    });
    updateDownloadToolbar();
    els.downloadTaskList.innerHTML = "";
    if (!downloadTasks.length) {
      const empty = document.createElement("div");
      empty.className = "empty-state download-empty";
      empty.textContent = t("noDownloadTasks");
      els.downloadTaskList.appendChild(empty);
      return;
    }
    if (taskGroupBy === "date" || taskGroupBy === "project") {
      groupTasks(downloadTasks, taskGroupBy).forEach((group) => {
        els.downloadTaskList.appendChild(renderTaskGroupHeader(group));
        group.tasks.forEach((task) => {
          els.downloadTaskList.appendChild(renderDownloadTask(task));
        });
      });
    } else {
      downloadTasks.forEach((task) => {
        els.downloadTaskList.appendChild(renderDownloadTask(task));
      });
    }
  }

  function renderDownloadTask(task) {
    const item = document.createElement("article");
    item.className = "download-task status-" + task.status
      + (selectedTaskIds.has(task.id) ? " task-selected" : "");

    const header = document.createElement("div");
    header.className = "download-task-head";

    const select = document.createElement("input");
    select.type = "checkbox";
    select.className = "task-select";
    select.disabled = !isCreditEligibleTask(task);
    select.title = select.disabled ? t("creditNotEligible") : "";
    select.checked = selectedTaskIds.has(task.id);
    select.addEventListener("change", () => {
      if (select.checked) selectedTaskIds.add(task.id);
      else selectedTaskIds.delete(task.id);
      item.classList.toggle("task-selected", select.checked);
      updateDownloadToolbar();
    });
    header.appendChild(select);

    const titleWrap = document.createElement("div");
    const title = document.createElement("h3");
    title.textContent = task.title || t("unknown");
    const meta = document.createElement("p");
    meta.textContent = [
      task.source || t("unknown"),
      displayKind(task.kind),
      t("mode") + ": " + taskModeLabel(task.mode),
    ].filter(Boolean).join(" · ");
    titleWrap.appendChild(title);
    titleWrap.appendChild(meta);

    const status = document.createElement("span");
    status.className = "task-status";
    status.textContent = taskStatusLabel(task.status);

    header.appendChild(titleWrap);
    header.appendChild(status);
    item.appendChild(header);

    const progress = document.createElement("div");
    progress.className = "task-progress";
    const progressBar = document.createElement("div");
    progressBar.style.width = Math.max(0, Math.min(100, Number(task.progress) || 0)) + "%";
    progress.appendChild(progressBar);
    item.appendChild(progress);

    const info = document.createElement("div");
    info.className = "task-info";
    appendTaskInfo(info, t("itemName"), task.title || t("unknown"));
    if (task.projectName) appendTaskInfo(info, t("project"), task.projectName);
    if (task.path) appendTaskInfo(info, t("localPath"), task.path);
    if (task.error) appendTaskInfo(info, t("failed"), task.error);
    item.appendChild(info);

    const actions = document.createElement("div");
    actions.className = "task-actions";
    if (task.status === "queued" || task.status === "downloading") {
      actions.appendChild(taskButton(t("cancel"), () => cancelTask(task.id), "danger"));
    }
    if (task.status === "downloaded" && task.path) {
      actions.appendChild(taskButton(t("importNow"), () => importDownloadedTask(task.id)));
    }
    if (actions.childNodes.length) item.appendChild(actions);

    return item;
  }

  function resumeActiveTasks() {
    downloadTasks.forEach((task) => {
      if ((task.status === "queued" || task.status === "downloading") && task.jobId) {
        listenTaskDownload(task.id, task.jobId);
      } else if (task.status === "importing") {
        updateTask(task.id, {
          status: "failed",
          error: t("importFailed") + ": " + (currentLang === "zh" ? "任务被中断，请重新导入。" : "Task was interrupted. Import again."),
        });
      }
    });
  }

  function appendTaskInfo(container, label, value) {
    const row = document.createElement("div");
    const name = document.createElement("span");
    name.textContent = label;
    const text = document.createElement("strong");
    text.textContent = value;
    row.appendChild(name);
    row.appendChild(text);
    container.appendChild(row);
  }

  function taskButton(label, onClick, variant) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    if (variant) button.classList.add(variant);
    button.addEventListener("click", onClick);
    return button;
  }

  function taskModeLabel(mode) {
    return mode === "import" ? t("importTask") : t("downloadTask");
  }

  function taskStatusLabel(status) {
    const key = String(status || "");
    if (key === "downloaded") return t("downloaded");
    if (key === "imported") return currentLang === "zh" ? "已导入" : "Imported";
    if (key === "downloading") return t("downloading");
    if (key === "importing") return t("importing");
    if (key === "queued") return t("queued");
    if (key === "failed") return t("failed");
    if (key === "cancelled") return t("cancelled");
    return key;
  }

  async function resolveProjectName() {
    if (!hasWorkflowIntegration() || typeof window.resolveWfi.getProjectInfo !== "function") {
      return "";
    }
    try {
      const info = await window.resolveWfi.getProjectInfo();
      return (info && info.name) || "";
    } catch (_error) {
      return "";
    }
  }

  function hasWorkflowIntegration() {
    return Boolean(
      window.resolveWfi
      && window.resolveWfi.isAvailable
      && typeof window.resolveWfi.importMedia === "function"
    );
  }

  function buildDetails(asset) {
    return [
      t("source") + ": " + asset.source,
      t("type") + ": " + displayKind(asset.kind),
      t("author") + ": " + (asset.author || t("unknown")),
      t("license") + ": " + (asset.license_name || t("unknown")),
      t("licenseUrl") + ": " + (asset.license_url || ""),
      t("originalUrl") + ": " + (asset.source_url || ""),
      asset.tags && asset.tags.length ? t("tags") + ": " + asset.tags.slice(0, 12).join(", ") : "",
    ].filter(Boolean).join("\n");
  }

  // --- Credit (cat) button: hover shows the info, click copies it ---
  function setCreditInfo(asset) {
    creditText = asset ? buildDetails(asset) : "";
    if (!els.creditPop) return;
    els.creditPop.textContent = "";
    els.creditPop.appendChild(document.createTextNode(creditText || t("selectAsset")));
    if (creditText) {
      const hint = document.createElement("span");
      hint.className = "credit-hint";
      hint.textContent = t("copyHint");
      els.creditPop.appendChild(hint);
    }
  }

  async function copyCreditFromButton() {
    if (!creditText) return;
    const ok = await copyText(creditText);
    showToast(ok ? t("copied") : t("copyFailed"));
    if (ok && els.creditButton) {
      els.creditButton.classList.add("copied");
      window.setTimeout(() => els.creditButton.classList.remove("copied"), 1200);
    }
  }

  async function copyText(text) {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
        return true;
      }
    } catch (_error) {
      // Fall through to the legacy path below.
    }
    try {
      const area = document.createElement("textarea");
      area.value = text;
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(area);
      return ok;
    } catch (_error) {
      return false;
    }
  }

  function showToast(message) {
    let toast = document.getElementById("appToast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "appToast";
      toast.className = "toast";
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    window.requestAnimationFrame(() => toast.classList.add("show"));
    if (toastTimer) window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => toast.classList.remove("show"), 1600);
  }

  function randomizeCatWander() {
    const cat = els.creditButton && els.creditButton.querySelector(".credit-cat");
    if (!cat) return;
    cat.style.animationDelay = (-Math.random() * 6).toFixed(2) + "s";
  }

  function positionCreditPop() {
    if (!els.creditButton || !els.creditPop) return;
    const rect = els.creditButton.getBoundingClientRect();
    const popWidth = Math.min(320, Math.max(240, window.innerWidth - 20));
    els.creditPop.style.width = popWidth + "px";
    const popHeight = Math.min(320, Math.max(120, els.creditPop.scrollHeight || 220));
    let left = rect.right - popWidth;
    let top = rect.top - popHeight - 10;
    if (top < 10) top = rect.bottom + 10;
    left = clamp(left, 10, Math.max(10, window.innerWidth - popWidth - 10));
    top = clamp(top, 10, Math.max(10, window.innerHeight - Math.min(popHeight, 320) - 10));
    els.creditPop.style.setProperty("--credit-pop-left", left + "px");
    els.creditPop.style.setProperty("--credit-pop-top", top + "px");
  }

  function showCreditPop() {
    if (!els.creditPop) return;
    positionCreditPop();
    els.creditPop.classList.add("visible");
  }

  function hideCreditPop() {
    if (!els.creditPop) return;
    els.creditPop.classList.remove("visible");
  }

  // --- Download-page bulk credit copy ---
  function groupTasks(tasks, mode) {
    const order = [];
    const map = new Map();
    tasks.forEach((task) => {
      let key;
      let label;
      if (mode === "date") {
        key = (task.completedAt || task.updatedAt || task.createdAt || "").slice(0, 10) || t("unknown");
        label = key;
      } else {
        key = task.projectName || "";
        label = task.projectName || t("noProject");
      }
      if (!map.has(key)) {
        map.set(key, { key: key, label: label, tasks: [] });
        order.push(key);
      }
      map.get(key).tasks.push(task);
    });
    return order.map((key) => map.get(key));
  }

  function renderTaskGroupHeader(group) {
    const header = document.createElement("div");
    header.className = "task-group-header";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "task-select";
    const eligibleTasks = group.tasks.filter(isCreditEligibleTask);
    checkbox.disabled = eligibleTasks.length === 0;
    checkbox.checked = eligibleTasks.length > 0 && eligibleTasks.every((task) => selectedTaskIds.has(task.id));
    checkbox.title = checkbox.disabled ? t("creditNotEligible") : "";
    checkbox.addEventListener("change", () => {
      eligibleTasks.forEach((task) => {
        if (checkbox.checked) selectedTaskIds.add(task.id);
        else selectedTaskIds.delete(task.id);
      });
      renderDownloadTasks();
    });
    const label = document.createElement("strong");
    label.textContent = group.label;
    const count = document.createElement("span");
    count.className = "group-count";
    count.textContent = group.tasks.length;
    header.appendChild(checkbox);
    header.appendChild(label);
    header.appendChild(count);
    return header;
  }

  function updateDownloadToolbar() {
    const eligible = downloadTasks.filter(isCreditEligibleTask);
    const total = eligible.length;
    const allSelected = total > 0 && eligible.every((task) => selectedTaskIds.has(task.id));
    if (els.selectAllTasks) {
      els.selectAllTasks.textContent = allSelected ? t("deselectAll") : t("selectAll");
      els.selectAllTasks.disabled = total === 0;
    }
    if (els.copyCreditsButton) {
      const n = eligible.filter((task) => selectedTaskIds.has(task.id)).length;
      els.copyCreditsButton.disabled = n === 0;
      els.copyCreditsButton.textContent = n > 0 ? t("copySelected", { n: n }) : t("copyCredits");
    }
  }

  function toggleSelectAllTasks() {
    const eligible = downloadTasks.filter(isCreditEligibleTask);
    const allSelected = eligible.length > 0 && eligible.every((task) => selectedTaskIds.has(task.id));
    if (allSelected) eligible.forEach((task) => selectedTaskIds.delete(task.id));
    else eligible.forEach((task) => selectedTaskIds.add(task.id));
    renderDownloadTasks();
  }

  function changeTaskGrouping(mode) {
    taskGroupBy = mode;
    localStorage.setItem("mediaBrowserTaskGroup", mode);
    renderDownloadTasks();
  }

  function assetCreditText(asset, task) {
    const safeAsset = asset || {};
    const title = safeAsset.title || (task && task.title) || safeAsset.id || t("unknown");
    const lines = [
      title,
      t("source") + ": " + (safeAsset.source || (task && task.source) || ""),
      t("author") + ": " + (safeAsset.author || t("unknown")),
      t("license") + ": " + (safeAsset.license_name || t("unknown")),
    ];
    if (safeAsset.author_url) lines.push(t("author") + " URL: " + safeAsset.author_url);
    if (safeAsset.license_url) lines.push(t("licenseUrl") + ": " + safeAsset.license_url);
    if (safeAsset.source_url) lines.push(t("originalUrl") + ": " + safeAsset.source_url);
    if (task && task.projectName) lines.push(t("project") + ": " + task.projectName);
    if (task && task.path) lines.push(t("localPath") + ": " + task.path);
    return lines.join("\n");
  }

  function buildCreditsText(tasks) {
    return tasks.map((task) => assetCreditText(task.asset, task)).join("\n\n");
  }

  async function copySelectedCredits() {
    const selected = downloadTasks.filter((task) => selectedTaskIds.has(task.id) && isCreditEligibleTask(task));
    if (!selected.length) return;
    const ok = await copyText(buildCreditsText(selected));
    showToast(ok ? t("creditCopied", { n: selected.length }) : t("copyFailed"));
  }

  function isCreditEligibleTask(task) {
    return task && (task.status === "downloaded" || task.status === "imported");
  }

  function formatDuration(value) {
    if (!value) return "";
    const total = Math.max(0, Math.round(value));
    const minutes = Math.floor(total / 60);
    const seconds = total % 60;
    return minutes + ":" + String(seconds).padStart(2, "0");
  }

  function displayKind(kind) {
    const key = String(kind || "");
    if (key === "3d") return t("threeD");
    if (Object.prototype.hasOwnProperty.call(dict.en, key)) return t(key);
    return key;
  }

  els.tokenInput.value = token;
  if (params.get("token")) {
    localStorage.setItem("mediaBrowserToken", token);
    els.tokenBox.classList.add("hidden");
    // Scrub the token from the visible URL / browser history (it is already
    // captured above) so it does not linger in the address bar or history.
    try {
      const mode = params.get("mode");
      const cleanUrl = window.location.pathname + (mode ? "?mode=" + encodeURIComponent(mode) : "");
      window.history.replaceState({}, document.title, cleanUrl);
    } catch (_error) {
      // replaceState can fail in some embedded contexts; non-fatal.
    }
  }
  els.languageSelect.value = currentLang;
  els.tokenInput.addEventListener("change", () => {
    token = els.tokenInput.value.trim();
    localStorage.setItem("mediaBrowserToken", token);
    loadSettings();
    loadPersistedDownloadTasks();
  });
  els.languageSelect.addEventListener("change", () => saveLanguage(els.languageSelect.value));
  els.railButtons.forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.view));
  });
  els.searchButton.addEventListener("click", search);
  els.queryInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") search();
  });
  els.queryInput.addEventListener("focus", () => els.commandCenter.classList.add("is-typing"));
  els.queryInput.addEventListener("blur", () => els.commandCenter.classList.remove("is-typing"));
  els.downloadButton.addEventListener("click", downloadSelected);
  els.importButton.addEventListener("click", importSelected);
  els.cancelButton.addEventListener("click", cancelDownload);
  els.clearFinishedButton.addEventListener("click", clearFinishedTasks);
  if (els.taskGroupBy) {
    els.taskGroupBy.value = taskGroupBy;
    els.taskGroupBy.addEventListener("change", () => changeTaskGrouping(els.taskGroupBy.value));
  }
  if (els.selectAllTasks) els.selectAllTasks.addEventListener("click", toggleSelectAllTasks);
  if (els.copyCreditsButton) els.copyCreditsButton.addEventListener("click", copySelectedCredits);
  if (els.apiKeyForm) {
    els.apiKeyForm.addEventListener("submit", (event) => {
      event.preventDefault();
      if (event.submitter && event.submitter.value === "cancel") {
        els.apiKeyDialog.close("cancel");
        return;
      }
      saveApiKeys();
    });
  }
  if (els.apiKeyNeverButton) els.apiKeyNeverButton.addEventListener("click", neverPromptApiKeys);
  apiKeyFields().forEach((field) => {
    // Auto-validate when the user finishes a row (blur or Enter).
    field.input.addEventListener("blur", () => validateField(field));
    field.input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        field.input.blur();
      }
    });
    // Clear stale ready/error styling while the user edits; blur re-validates.
    field.input.addEventListener("input", () => {
      if (pendingDeletes.has(field.name)) return;
      clearFieldState(field);
      const configured = lastApiKeyPayload && lastApiKeyPayload.configured && lastApiKeyPayload.configured[field.name];
      setFieldStatus(field, !field.input.value.trim() && configured ? "configured" : "empty");
    });
  });
  if (els.apiKeyDialog) {
    els.apiKeyDialog.addEventListener("click", (event) => {
      const trash = event.target.closest(".trash-button");
      if (trash && trash.dataset.delete) {
        event.preventDefault();
        toggleDeleteField(trash.dataset.delete);
      }
    });
  }
  if (els.apiKeyCloseButton) {
    els.apiKeyCloseButton.addEventListener("click", (event) => {
      event.preventDefault();
      if (els.apiKeyDialog && els.apiKeyDialog.open) els.apiKeyDialog.close("cancel");
    });
  }
  if (els.creditButton) {
    if (els.creditPop && els.creditPop.parentElement !== document.body) {
      document.body.appendChild(els.creditPop);
    }
    els.creditButton.addEventListener("mouseenter", showCreditPop);
    els.creditButton.addEventListener("mousemove", positionCreditPop);
    els.creditButton.addEventListener("mouseleave", hideCreditPop);
    els.creditButton.addEventListener("focus", showCreditPop);
    els.creditButton.addEventListener("blur", hideCreditPop);
    els.creditButton.addEventListener("click", copyCreditFromButton);
    els.creditButton.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        copyCreditFromButton();
      }
    });
  }
  els.collapsePreviewButton.addEventListener("click", closePreviewPanel);
  window.addEventListener("resize", () => {
    fitPreviewStage(currentPreviewAspect, currentPreviewKind);
    positionCreditPop();
  });
  if (els.resultsPanel) els.resultsPanel.addEventListener("scroll", onResultsScroll, { passive: true });

  setupFilters();
  randomizeCatWander();
  applyLanguage();
  setView(activeView);
  fitPreviewStage(currentPreviewAspect, currentPreviewKind);
  loadSettings();
  loadPersistedDownloadTasks();
  maybePromptForApiKeys();
  setStatus(t("ready"));
})();
