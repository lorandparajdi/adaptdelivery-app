// =======  The 1st code block ========  //
function classifyDevice() {
  const ua = (navigator.userAgent || navigator.vendor || window.opera || "");
  const touch = (navigator.maxTouchPoints || 0) > 0;

  const isIPhone       = /iPhone/.test(ua);
  const isIPod         = /iPod/.test(ua);
  const isAndroid      = /Android/.test(ua);
  const isAndroidPhone = isAndroid && /Mobile/.test(ua);
  const isWinPhone     = /Windows Phone/.test(ua);
  const isiPad         = /iPad/.test(ua);
  const isAndroidTab   = /Android/.test(ua) && !/Mobile/.test(ua);
  const otherTabletUA  = /Tablet|PlayBook|Silk/.test(ua);

  const coarse = window.matchMedia("(hover: none) and (pointer: coarse)").matches || touch;
  const narrow = window.matchMedia("(max-width: 599px)").matches;
  const wide   = window.matchMedia("(min-width: 720px)").matches;

  const phoneUA  = isIPhone || isIPod || isAndroidPhone || isWinPhone || /Mobile/.test(ua);
  const tabletUA = isiPad || isAndroidTab || otherTabletUA;

  if (phoneUA)  return "phone";
  if (tabletUA) return "tablet";

  // Fallback only when the user agent is ambiguous, for example in devtools:
  if (coarse && narrow) return "phone";
  if (coarse && wide)   return "tablet";

  return "desktop";
}


function applyDeviceMode() {
  const kind = classifyDevice();
  const isPhone = (kind === "phone");

  document.documentElement.classList.toggle("mobile-mode", isPhone);
}

// Run immediately
applyDeviceMode();

// Re-evaluate on viewport, orientation, or visibility changes
window.addEventListener("resize", applyDeviceMode, { passive: true });
window.addEventListener("orientationchange", applyDeviceMode, { passive: true });
document.addEventListener("visibilitychange", () => requestAnimationFrame(applyDeviceMode));



// =======  The 2nd code block ========  //
function updateActiveContentScrollGap() {
  if (document.documentElement.classList.contains("mobile-mode")) {
    document.querySelectorAll("main > .content").forEach((content) => {
      content.classList.remove("has-scroll-gap");
    });
    return;
  }

  const mainEl = document.querySelector("main");
  const activeContent = document.querySelector("main > .content.active");

  if (!mainEl || !activeContent) return;

  const card = activeContent.querySelector(":scope > .card");
  if (!card) return;

  // First remove the spacing so only the real content is measured.
  activeContent.classList.remove("has-scroll-gap");

  requestAnimationFrame(() => {
    const availableHeight = mainEl.clientHeight;

    /*
      The card scrollHeight represents the real height required by the content.
	  The 2 px tolerance prevents activation caused by browser rounding differences.
    */
    const cardNeedsScroll = card.scrollHeight > availableHeight + 2;

    activeContent.classList.toggle("has-scroll-gap", cardNeedsScroll);
  });
}

let activeCardResizeObserver = null;

function observeActiveContentCard() {
  if (activeCardResizeObserver) {
    activeCardResizeObserver.disconnect();
  }

  const activeCard = document.querySelector(
    "main > .content.active > .card"
  );

  if (!activeCard) return;

  activeCardResizeObserver = new ResizeObserver(() => {
    requestAnimationFrame(updateActiveContentScrollGap);
  });

  activeCardResizeObserver.observe(activeCard);

  updateActiveContentScrollGap();
}

document.addEventListener("DOMContentLoaded", () => {
  requestAnimationFrame(observeActiveContentCard);
});
		
function showContent(contentId, event) {
    // 🔁 Disable all visible sections
    document.querySelectorAll(".content").forEach((content) => content.classList.remove("active"));

    // 🔁 Disable all buttons, including submenu and main buttons
    document.querySelectorAll(".menu-item").forEach((btn) => btn.classList.remove("active"));

    // 🔁 If the user clicked something other than gradius/sasa/diffusion, close the submenu
    if (!["gradius", "sasa", "diffusion"].includes(contentId)) {
        const container = document.getElementById("submenu-container");
        const polymerBtn = document.getElementById("btn-polymer");

        if (container.classList.contains("show")) {
			// height: scrollHeight -> 0 for a smooth transition
			container.style.height = container.scrollHeight + "px";
			void container.offsetHeight;       // force one reflow
			container.style.height = "0px";

			const closeCleanup = () => {
				container.classList.remove("show");
				container.style.height = "";
				container.style.display = "";
			};
			const t = setTimeout(closeCleanup, 380);  // fallback
			container.addEventListener("transitionend", (e) => {
				if (e.propertyName === "height") {
					clearTimeout(t);
					closeCleanup();
				}
			}, { once: true });

			polymerBtn.classList.remove("active");
			const arrow = document.getElementById("arrow");
			if (arrow) arrow.style.transform = "rotate(0deg)";
		}
    }

    // 🔁 Activează doar secțiunea potrivită
    const contentElement = document.getElementById(contentId);
	if (contentElement) {
	  contentElement.classList.add("active");

	  const mainEl = document.querySelector("main");
	  if (mainEl) {
		mainEl.scrollTop = 0;
	  }
	  
	  requestAnimationFrame(observeActiveContentCard);
	}

    // 🔁 Activează butonul apăsat; dacă funcția este apelată programatic,
	// caută automat butonul corespunzător din sidebar
	if (event && event.currentTarget) {
		event.currentTarget.classList.add("active");
	} else {
		document.querySelectorAll("#sidebar .menu-item").forEach((btn) => {
			const onclickValue = btn.getAttribute("onclick") || "";
			if (onclickValue.includes(`showContent('${contentId}'`)) {
				btn.classList.add("active");
			}
		});
	}

    // 🔁 Dacă e subbuton, activează și butonul principal „Properties Generator”
    if (["gradius", "sasa", "diffusion"].includes(contentId)) {
        document.getElementById("btn-polymer").classList.add("active");
    }
	
	// Auto-close drawer pe mobil după click pe un meniu
    if (isTouchDrawerMode()) {
		const sidebar = document.getElementById("sidebar");
		if (sidebar?.classList.contains("open")) toggleMenu(false);
	}
}


function isTouchDrawerMode() {
   return document.documentElement.classList.contains('mobile-mode');
}


function toggleMenu(forceState) {
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("mobileOverlay");
  if (!sidebar) return;

  // doar lățimea decide mobil vs web (vezi isTouchDrawerMode)
  const isMobile = isTouchDrawerMode();

  const willOpen = (typeof forceState === "boolean")
    ? forceState
    : !sidebar.classList.contains("open");

  // helpers scroll-lock
  const lockScroll = () => {
    // dacă un modal a blocat deja scroll-ul, nu suprascriem
    if (document.body.dataset.scrollLocked === "1") return;
  
    window.__savedScrollY = window.scrollY || document.documentElement.scrollTop || 0;
    const s = document.body.style;
    s.position = "fixed";
    s.top = `-${window.__savedScrollY}px`;
    s.left = "0"; s.right = "0"; s.width = "100%"; s.overflow = "hidden";
  };
  const unlockScroll = () => {
    // dacă un modal este deschis și ține scroll-ul blocat, nu deblocăm aici
    if (document.body.dataset.scrollLocked === "1") return;
  
    const s = document.body.style;
    s.position = ""; s.top = ""; s.left = ""; s.right = ""; s.width = ""; s.overflow = "";
    if (typeof window.__savedScrollY === "number") window.scrollTo(0, window.__savedScrollY);
  };

  // ——— MOBILE (drawer) ———
  if (isMobile) {
    if (willOpen) {
      sidebar.classList.add("open");
      overlay && overlay.classList.add("show");
      lockScroll();
    } else {
      sidebar.classList.remove("open");
      overlay && overlay.classList.remove("show");
      unlockScroll();
    }
    // în modul mobil nu folosim „collapsed”
    sidebar.classList.remove("collapsed");
    return;
  }

  // ——— DESKTOP (sidebar collapsible) ———
  overlay && overlay.classList.remove("show");
  sidebar.classList.remove("open");
  unlockScroll();

	sidebar.classList.toggle("collapsed");
}

// Tap pe overlay închide drawer-ul
document.getElementById("mobileOverlay")?.addEventListener("click", () => toggleMenu(false));

// Tap/click în afara meniului închide drawer-ul (NUMAI pe mobil)
document.addEventListener("click", function (event) {
  const sidebar = document.getElementById("sidebar");
  if (!sidebar) return;

  // doar în modul mobil (drawer)
  if (!isTouchDrawerMode()) return;

  // dacă meniul nu e deschis, nu facem nimic
  if (!sidebar.classList.contains("open")) return;

  const target = event.target;

  // dacă am dat click în interiorul meniului, nu îl închidem
  if (sidebar.contains(target)) return;

  // dacă am dat click pe butonul ☰, nu îl închidem aici
  const toggleBtn = document.getElementById("menuToggle");
  if (toggleBtn && toggleBtn.contains(target)) return;

  // orice alt click în afara meniului => închidem meniul
  toggleMenu(false);
});


function isMobileLandscape() {
  return document.documentElement.classList.contains('mobile-mode') &&
         window.matchMedia("(orientation: landscape)").matches;
}


function isSmallMobilePortrait() {
  // activ doar pe telefon (nu tabletă)
  if (!document.documentElement.classList.contains('mobile-mode')) return false;

  const isPortrait = window.matchMedia("(orientation: portrait)").matches;
  // prindem iPhone SE (320), 360 și alte telefoane scurte
  const narrowW = window.matchMedia("(max-width: 380px)").matches;
  const shortH  = window.matchMedia("(max-height: 700px)").matches;

  return isPortrait && (narrowW || shortH);
}


function toggleSubmenu(event) {
  if (event?.currentTarget?.disabled) return;
  event?.stopPropagation();
  event?.preventDefault?.();

  const container  = document.getElementById("submenu-container");
  const polymerBtn = document.getElementById("btn-polymer");
  const arrow      = document.getElementById("arrow");   // poate lipsi
  const sidebar    = document.getElementById("sidebar"); // drawer-ul care SCROLL-ează
  if (!container || !polymerBtn) return;

  const isOpening = !container.classList.contains("show");

  // ===== iOS/touch FIX: fără height și pe landscape, și pe portret foarte mic =====
  if (isMobileLandscape() || isSmallMobilePortrait()) {
    if (isOpening) {
      // pregătire: arătăm instant, dar lăsăm fade+slide să se aplice
      container.classList.add("show", "submenu-anim");
      container.style.height = "auto";            // fără height-transition în landscape
      polymerBtn.classList.add("active");
      if (arrow) arrow.style.transform = "rotate(180deg)";

      // pornește efectul într-un frame nou
      requestAnimationFrame(() => {
        container.classList.add("enter");
      });

      // adu submeniul în viewport după ce devine vizibil
      const doScroll = () => {
        if (!sidebar) return;
        const y = container.offsetTop - 12;
        if (typeof sidebar.scrollTo === "function") {
          sidebar.scrollTo({ top: Math.max(0, y), behavior: "auto" });
        } else {
          sidebar.scrollTop = Math.max(0, y);
        }
      };
      requestAnimationFrame(() => requestAnimationFrame(doScroll));

    } else {
      // închidere: scoatem .enter (devine invizibil), apoi curățăm starea
      container.classList.remove("enter");

      const closeCleanup = () => {
        container.classList.remove("show", "submenu-anim");
        container.style.height = "";
        container.style.display = "";
        polymerBtn.classList.remove("active");
        if (arrow) arrow.style.transform = "rotate(0deg)";
        container.removeEventListener("transitionend", onEnd);
      };

      const onEnd = (e) => {
        if (e.target === container && (e.propertyName === "opacity" || e.propertyName === "transform")) {
          closeCleanup();
        }
      };

      // fallback în caz că Safari nu emite transitionend
      const t = setTimeout(closeCleanup, 260);
      container.addEventListener("transitionend", (evt) => {
        clearTimeout(t);
        onEnd(evt);
      }, { once: true });
    }
    return; // în landscape ne oprim aici; ramura standard rămâne pentru portret/desktop
  }

  // ===== PORTRET / DESKTOP: animația ta pe height rămâne neschimbată =====
  // scoate "active" de pe toate butoanele principale
  document.querySelectorAll(".menu-item").forEach(btn => btn.classList.remove("active"));

  // helper: aduce submeniul complet în viewportul drawer-ului
  const scrollSubmenuIntoDrawer = () => {
    if (!sidebar) return;
    const pr = sidebar.getBoundingClientRect();
    const cr = container.getBoundingClientRect();
    const overTop    = cr.top    - pr.top;     // <0 => ascuns sus
    const overBottom = cr.bottom - pr.bottom;  // >0 => ascuns jos
    if (overTop < 0) {
      sidebar.scrollBy({ top: overTop - 12, behavior: "smooth" });
    } else if (overBottom > 0) {
      sidebar.scrollBy({ top: overBottom + 12, behavior: "smooth" });
    }
  };

  if (isOpening) {
    // anulăm orice display inline rămas de la o închidere anterioară
    container.style.removeProperty("display");
    container.classList.add("show");

    // 0 -> scrollHeight
    const target = container.scrollHeight;   // măsoară o singură dată
	container.style.height = "0px";
	requestAnimationFrame(() => {
		requestAnimationFrame(() => {
			container.style.height = target + "px";
		});
	});

    // după tranziție: height:auto și abia apoi scroll
    const onOpenEnd = (e) => {
      if (e.propertyName !== "height") return;
      container.style.height = "auto";
      requestAnimationFrame(scrollSubmenuIntoDrawer);
    };
    container.addEventListener("transitionend", onOpenEnd, { once: true });

    // fallback în caz că transitionend nu se emite
    setTimeout(() => {
      if (container.classList.contains("show")) {
        container.style.height = "auto";
        scrollSubmenuIntoDrawer();
      }
    }, 380);

    polymerBtn.classList.add("active");
    if (arrow) arrow.style.transform = "rotate(180deg)";
  } else {
    // scrollHeight -> 0
    container.style.height = container.scrollHeight + "px";
    void container.offsetHeight;
    container.style.height = "0px";

    const closeCleanup = () => {
      container.classList.remove("show");
      container.style.height = "";
      container.style.display = ""; // curățăm orice inline vechi
    };

    // fallback dacă nu vine transitionend
    const t = setTimeout(closeCleanup, 380);

    container.addEventListener("transitionend", (e) => {
      if (e.propertyName === "height") {
        clearTimeout(t);
        closeCleanup();
      }
    }, { once: true });

    polymerBtn.classList.remove("active");
    if (arrow) arrow.style.transform = "rotate(0deg)";
  }
}


// ==== Dynamic tick config for X axis ====
function isPlotlyReady(el) {
  return !!(el && el.classList && el.classList.contains('js-plotly-plot') && el._fullLayout);
}


function xTickConfig(el) {
  const w = el?.clientWidth || 800;

  // ~1 tick / 80px, între 4 și 14 ticks
  const nticks = Math.max(4, Math.min(14, Math.round(w / 80)));

  // Ajustare unghi & font în funcție de lățime
  let angle = 0;
  let tickSize = 12;
  if (w < 520) { angle = -45; tickSize = 10; }
  if (w < 380) { angle = -65; tickSize = 9; }

  return {
    'xaxis.nticks': nticks,
    'xaxis.tickangle': angle,
    'xaxis.tickfont.size': tickSize,
    'xaxis.automargin': true
  };
}


// Normalizează graficul imediat după generare, ca să fie identic cu starea după un resize
function stabilizeAndNormalizeTicks(id) {
  const el = document.getElementById(id);
  if (!isPlotlyReady(el)) return;  // evită relayout pe div neinițializat

  // rulează pe frame-ul următor, când DOM-ul are lățimea finală
  requestAnimationFrame(() => {
    const w = el.clientWidth || 800;

    // Config dinamic de bază (nticks, unghi, font) + resize
    Plotly.Plots.resize(el);

    // Pe ecrane late forțăm 100 (cum ți-ai dorit); altfel lăsăm auto + xTickConfig
    const prefer50 = w >= 1100; // prag de la care graficul e „alungit”
	const dynamicCfg = xTickConfig(el);
	const extra = prefer50
		? { 'xaxis.tickmode': 'linear', 'xaxis.dtick': 50 }  // <— 50 în loc de 100
		: { 'xaxis.tickmode': 'auto',   'xaxis.dtick': null };

	Plotly.relayout(el, { ...dynamicCfg, ...extra });
  });
}


// === Limităm zoom-out la span-ul inițial al graficului 2D (variantă robustă) ===
function attachZoomClampToInitialRange(graphDivId) {
  const div = document.getElementById(graphDivId);
  if (!div) return;

  // Plotly.newPlot poate reseta handler-ele interne.
  // Curățăm listenerul vechi și îl reatașăm.
  if (typeof div.removeAllListeners === "function") {
    div.removeAllListeners("plotly_relayout");
  }

  // inițializăm span-ul inițial din layout
  function initSpans() {
    const layout = div.layout;
    if (!layout || !layout.xaxis || !layout.yaxis) return false;

    const xr = layout.xaxis.range;
    const yr = layout.yaxis.range;
    if (!xr || xr.length !== 2 || !yr || yr.length !== 2) return false;

    div._zoomClampInitialXSpan = xr[1] - xr[0];
    div._zoomClampInitialYSpan = yr[1] - yr[0];
    return true;
  }

  // dacă la momentul apelului layout-ul nu e încă complet, mai încercăm o dată pe frame-ul următor
  if (!initSpans()) {
    requestAnimationFrame(() => requestAnimationFrame(initSpans));
  }

  div.on("plotly_relayout", function () {
    const layout = div.layout;
    if (!layout || !layout.xaxis || !layout.yaxis) return;

    const initX = div._zoomClampInitialXSpan;
    const initY = div._zoomClampInitialYSpan;
    if (!initX && !initY) return;   // nu avem cu ce compara

    const upd = {};
    let need = false;

    // --- X ---
    const xr = layout.xaxis.range;
    if (initX && xr && xr.length === 2) {
      const spanX = xr[1] - xr[0];
      if (!Number.isFinite(spanX) || spanX > initX * 1.0001) {
        const centerX = (xr[0] + xr[1]) / 2;
        const halfX = initX / 2;
        upd["xaxis.autorange"] = false;
        upd["xaxis.range"] = [centerX - halfX, centerX + halfX];
        need = true;
      }
    }

    // --- Y ---
    const yr = layout.yaxis.range;
    if (initY && yr && yr.length === 2) {
      const spanY = yr[1] - yr[0];
      if (!Number.isFinite(spanY) || spanY > initY * 1.0001) {
        const centerY = (yr[0] + yr[1]) / 2;
        const halfY = initY / 2;
        upd["yaxis.autorange"] = false;
        upd["yaxis.range"] = [centerY - halfY, centerY + halfY];
        need = true;
      }
    }

    if (need) {
      Plotly.relayout(div, upd);
    }
  });
}


// ==== Debounce resize handler ====
let __rzTimer = null;
window.addEventListener('resize', () => {
  clearTimeout(__rzTimer);

  __rzTimer = setTimeout(() => {
    resizeGraphs();
    updateActiveContentScrollGap();

    const c = document.getElementById('submenu-container');

    if (c && c.classList.contains('show')) {
      c.style.height = 'auto';
    }
  }, 120);
});

window.addEventListener('orientationchange', () => {
  setTimeout(() => {
    const c  = document.getElementById('submenu-container');
    const sb = document.getElementById('sidebar');

    if (c && c.classList.contains('show')) {
      c.style.height = 'auto';

      if (sb) {
        const y = c.offsetTop - 12;

        if (typeof sb.scrollTo === 'function') {
          sb.scrollTo({
            top: Math.max(0, y),
            behavior: 'auto'
          });
        } else {
          sb.scrollTop = Math.max(0, y);
        }
      }
    }

    requestAnimationFrame(updateActiveContentScrollGap);
  }, 250);
});


const POLYMER_STRUCTURE_MAP = {
  "PE": "PE_repeat_unit.png",
  "PEO": "PEO_repeat_unit.png",
  "PEI": "PEI_repeat_unit.png",
  "PAM": "PAM_repeat_unit.png",
  "PAAMR": "PAAMR_repeat_unit.png",
  "PNIPAAMR": "PNIPAAMR_repeat_unit.png",
  "PVMKR": "PVMKR_repeat_unit.png",
  "GUAI": "GUAI_repeat_unit.png",
  "PHP": "PHP_repeat_unit.png",
  "SYR": "SYR_repeat_unit.png"
};

const POLYMER_FULLNAME_MAP = {
  "PE": "Polyethylene",
  "PEO": "Polyethylene oxide",
  "PEI": "Polyethyleneimine",
  "PAM": "Polyacrylamide",
  "PAAMR": "Poly(allyamine) isotactic (R)",
  "PNIPAAMR": "Poly(N-isopropylacrylamide) isotactic (R)",
  "PVMKR": "Poly(vinyl methyl ketone) isotactic (R)",
  "GUAI": "Guaiacyl unit (G-unit) of lignin",
  "PHP": "p-Hydroxyphenyl unit (H-unit) of lignin",
  "SYR": "Syringyl unit (S-unit) of lignin"
};

function hidePolymerStructure(kind){
  const variants = ["", "Mobile"]; // Desktop + Mobile

  variants.forEach(v => {
    const box = document.getElementById(`polymerStructureBox${v}_${kind}`);
    const img = document.getElementById(`polymerStructureImg${v}_${kind}`);
    const lbl = document.getElementById(`polymerStructureLabel${v}_${kind}`);

    if (box) box.style.display = "none";
    if (img) img.src = "";
    if (lbl) lbl.textContent = "";
  });
}

function updatePolymerStructure(kind){
  hidePolymerStructure(kind);
  const select = document.getElementById(`polymer_type_${kind}`);
  if (!select) return;

  const code = (select.value || "").trim();
  const file = POLYMER_STRUCTURE_MAP[code];

  if (!code || !file){
    hidePolymerStructure(kind);
    return;
  }

  const nameFull = POLYMER_FULLNAME_MAP[code] || code;
  const isMobile = window.matchMedia("(max-width: 991px)").matches;
  const variants = isMobile ? ["Mobile"] : [""];

  variants.forEach(v => {
    const box = document.getElementById(`polymerStructureBox${v}_${kind}`);
    const img = document.getElementById(`polymerStructureImg${v}_${kind}`);
    const lbl = document.getElementById(`polymerStructureLabel${v}_${kind}`);

    if (!box || !img) return;

    img.src = `/static/chemical_structures/${file}`;
    box.style.display = "block";
    if (lbl) lbl.textContent = nameFull;
  });
}
// ........... //


// ===== NEW: actualizează lista de polimeri în funcție de tipul selectat =====
function updatePolymerOptions(kind) {
  hidePolymerStructure(kind);
  const category = document.getElementById("polymer_category_" + kind).value;

  const familySelect  = document.getElementById("polymer_family_" + kind);
  const nameSelect    = document.getElementById("polymer_type_" + kind); // rămâne FINAL (backend)

  // reset
  familySelect.innerHTML = "";
  familySelect.disabled = true;

  nameSelect.innerHTML = "";
  nameSelect.disabled = true;

  // dacă nu e selectat Class -> totul rămâne blocat
  if (!category) {
    if (kind === "gradius") validateInputGradius();
    else validateInputSasa();
    return;
  }

  let familyList = [];

  if (category === "Natural") {
    familyList = ["Lignin"];
  } else if (category === "Synthetic") {
    familyList = ["Acrylamides","Amines","Amides","Imines","Ketones","Olefins","Oxides","Vinyls"];
  }

  // adăugăm prima opțiune placeholder
  const defaultFamilyOption = document.createElement("option");
  defaultFamilyOption.value = "";
  defaultFamilyOption.textContent = "Select...";
  defaultFamilyOption.selected = true;
  defaultFamilyOption.disabled = false;
  familySelect.appendChild(defaultFamilyOption);

  // populate family select
  familyList.forEach(item => {
    const opt = document.createElement("option");
    opt.value = item;
    opt.textContent = item;
    familySelect.appendChild(opt);
  });

  familySelect.disabled = false;

  // Polymer Name rămâne complet gol până alegi efectiv Polymer Type
  nameSelect.innerHTML = "";
  nameSelect.disabled = true;

  if (kind === "gradius") validateInputGradius();
  else validateInputSasa();
}


function updatePolymerNameOptions(kind) {
  const category = document.getElementById("polymer_category_" + kind).value;
  const family   = document.getElementById("polymer_family_" + kind).value;

  const nameSelect = document.getElementById("polymer_type_" + kind); // FINAL (backend)
  nameSelect.innerHTML = "";
  nameSelect.disabled = true;

  // dacă nu e selectată familia, Polymer Name rămâne gol
  if (!category || !family) {
    hidePolymerStructure(kind);

    if (kind === "gradius") validateInputGradius();
    else validateInputSasa();
    return;
  }

  // doar după selectarea Polymer Type afișăm placeholder-ul Select...
  const defaultNameOption = document.createElement("option");
  defaultNameOption.value = "";
  defaultNameOption.textContent = "Select...";
  defaultNameOption.selected = true;
  defaultNameOption.disabled = false;
  nameSelect.appendChild(defaultNameOption);

  // mapping din Polymer Class.txt
  const mapSynthetic = {
    "Acrylamides": ["PNIPAAMR"],
    "Amines":      ["PAAMR"],
    "Amides":      ["PAM"],
    "Imines":      ["PEI"],
    "Ketones":     ["PVMKR"],
    "Olefins":     ["PE"],
    "Oxides":      ["PEO"],
    "Vinyls":      ["PE"]   // da, tot PE în fișierul tău
  };

  // Natural: trimitem direct GUAI / PHP / SYR către backend
  let list = [];
  if (category === "Natural") {
      list = ["GUAI", "PHP", "SYR"];
  } else {
      list = mapSynthetic[family] || [];
  }

  list.forEach(item => {
    const opt = document.createElement("option");
    opt.value = item;
    opt.textContent = item;
    nameSelect.appendChild(opt);
  });

  nameSelect.disabled = false;
  nameSelect.value = "";

  if (kind === "gradius") validateInputGradius();
  else validateInputSasa();
  
  hidePolymerStructure(kind);
}


function validateInputGradius() {
  const inputField    = document.getElementById("lengths_gradius");
  const errorMessage  = document.getElementById("error-message-gradius");
  const generateButton = document.getElementById("generate-button-gradius");
  const polymer       = document.getElementById("polymer_type_gradius").value;

  const value = inputField.value.trim();
  const regex = /^[1-9]\d*$/;

  // 1.Dacă nu e nimic scris → ascundem mesajul, dezactivăm butonul
  if (value === "") {
    errorMessage.classList.add("hidden");
    generateButton.disabled = true;
    return;
  }

  // 2️.Dacă inputul e valid numeric
  if (regex.test(value)) {
    const numericValue = parseInt(value, 10);

    // 2.a) Dacă >1000 → afișăm mesajul roșu
    if (numericValue > 1000) {
      errorMessage.classList.remove("hidden");
      errorMessage.textContent = "*Please enter a single positive integer less than or equal to 1000.";
      generateButton.disabled = true;
      return;
    }

    // 2.b) Număr OK, dar verificăm dacă polimerul este selectat
    errorMessage.classList.add("hidden");

    if (polymer !== "") {
      generateButton.disabled = false;
    } else {
      generateButton.disabled = true;
    }

    return;
  }

  // 3.Dacă nu e număr valid → afișăm mesaj roșu
  errorMessage.classList.remove("hidden");
  errorMessage.textContent = "*Please enter a single positive integer less than or equal to 1000.";
  generateButton.disabled = true;
}


// === 3D viewer simplu pentru PDB (3Dmol.js) ===
function updatePdbViewer(containerId, polymerType, monomerNumber) {
  const container = document.getElementById(containerId);
  if (!container || typeof $3Dmol === "undefined") return;

  // Curățăm orice viewer anterior
  container.innerHTML = "";

  // Dăm o înălțime clară ...
  container.style.width = "100%";
  container.style.height = "230px";
  container.style.position = "relative";
  container.style.zIndex = "1";

  const config = { backgroundColor: "white" };
  const viewer = $3Dmol.createViewer(container, config);
  container._pdbViewer = viewer;

  // salvăm N ca să știm la reset ce lungime are lanțul
  container._pdbMeta = {
    monomerNumber: Number(monomerNumber) || 0,
    polymerType: polymerType || ""
  };

  // tipul de pagină (gradius / sasa) – folosit pentru label-ul 3D
  const kind =
    containerId.includes('gradius') ? 'gradius' :
    (containerId.includes('sasa') ? 'sasa' : '');
  container.dataset.kind = kind;
  
  
  // lăsăm viewer-ul 3D gol și NU mai facem fetch la PDB
  //const lowerType = (polymerType || '').toLowerCase();
  //if (lowerType === 'syr') {
  //  try {
  //    viewer.removeAllModels();
  //    viewer.clear();        // dacă există în versiunea ta 3Dmol, ok; dacă nu, nu strică (catch)
  //  } catch (e) {}
  //  viewer.render();
  //  return; // NU facem fetch, NU afișăm eroare
  //}

  // stare inițială controale 3D
  if (!container.dataset.panMode) {
    container.dataset.panMode = "0";
  }
  if (!container.dataset.scrollZoom) {
    container.dataset.scrollZoom = "0";
  }
  
  // pregătim controlul pentru zoom din rotiță (implicit dezactivat)
  setupPdbWheelControl(containerId);
  setupPdbPanControl(containerId);
  setupPdbCursorHelpers(containerId);
  setupPdbTouchControls(containerId);

  const url = `/pdb_polymer?type=${encodeURIComponent(polymerType)}&n=${encodeURIComponent(monomerNumber)}`;

  fetch(url)
    .then(resp => {
      if (!resp.ok) throw new Error(`Failed to load PDB structure (status ${resp.status}).`);
      return resp.text();
    })
	.then(pdbText => {
	  // adăugăm modelul PDB
	  viewer.addModel(pdbText, "pdb", { keepH: true });

	  // determinăm kind-ul (gradius sau sasa) din ID-ul containerului
	  let kind = null;
	  if (containerId.includes("gradius")) {
		kind = "gradius";
	  } else if (containerId.includes("sasa")) {
		kind = "sasa";
	  }

	  // aplicăm stilul + display (all / noh) în funcție de radiourile din box
	  if (kind) {
		applyPdbStyleAndDisplay(kind, false); // aplică stilul fără render
	  } else {
		// fallback (nu ar trebui să ajungă aici, dar punem ceva safe)
		viewer.setStyle({}, { stick: { radius: 0.25 } });
		viewer.render();
	  }

	  // ===== NEW: force same default zoom/camera always =====
	  if (kind) {
		const projKind = getCurrentProjectionKind(kind);

		// IMPORTANT: default-ul se calibrează pe N=490, nu pe primul N introdus
		pdbEnsureDefaultViewExistsForTemplate(projKind).then(() => {
		pdbNormalizeCamera(viewer, projKind);
		});
	  }
	})
	.catch(err => {
	  console.error("3D viewer error:", err);
	  container.innerHTML = `<span class="text-red-500 text-xs">3D viewer error: ${err.message}</span>`;
	});
}


function getPdbViewer(containerId) {
  const container = document.getElementById(containerId);
  return container && container._pdbViewer ? container._pdbViewer : null;
}


function getCurrentPdbStyle(kind) {
  let name = null;

  if (kind === "gradius") {
    name = "pdb-style-gradius";
  } else if (kind === "sasa") {
    name = "pdb-style-sasa";
  } else {
    return "stick";
  }

  const input = document.querySelector(`input[name="${name}"]:checked`);
  return input ? input.value : "stick";
}

function getCurrentPdbDisplay(kind) {
  let name = null;

  if (kind === "gradius") {
    name = "pdb-display-gradius";
  } else if (kind === "sasa") {
    name = "pdb-display-sasa";
  } else {
    return "all";
  }

  const input = document.querySelector(`input[name="${name}"]:checked`);
  return input ? input.value : "all";
}

function getCurrentPdbProjection(kind) {
  const name = (kind === "gradius") ? "pdb-projection-gradius" :
               (kind === "sasa") ? "pdb-projection-sasa" : null;
  if (!name) return "perspective";

  const input = document.querySelector(`input[name="${name}"]:checked`);
  return input ? input.value : "perspective";
}


// ===== PDB: Same camera distance/zoom ALWAYS + recenter on current model =====
window.__PDB_DEFAULT_VIEW = window.__PDB_DEFAULT_VIEW || {
  perspective: null,
  orthographic: null
};

// 1.0 = fit exact, 1.6–2.2 = mai aproape (DOAR la calibrare)
const PDB_DEFAULT_CLOSEUP_MULT = 90;
const PDB_ORTHO_ZOOM_COMP = 0.40;

const PDB_CALIBRATION_N = 490;

// calibrare default-view pe N=490 (ca să nu depindă de primul N ales de user)
async function pdbEnsureDefaultViewExistsForTemplate(projKind) {
  // dacă e deja calibrat, gata
  if (window.__PDB_DEFAULT_VIEW && window.__PDB_DEFAULT_VIEW[projKind]) return true;

  // container ascuns (nu afectează UI)
  const tmp = document.createElement("div");
  tmp.style.cssText = "position:absolute;left:-99999px;top:-99999px;width:300px;height:300px;opacity:0;pointer-events:none;";
  document.body.appendChild(tmp);

  try {
    const tmpViewer = $3Dmol.createViewer(tmp, { backgroundColor: "white" });

    //const calibrationType = "PNIPAAMR"; // Synthetic reference camera; independent of the first generated polymer
	const calibrationType = "PEI"; // Synthetic reference camera; independent of the first generated polymer
	const url = `/pdb_polymer?type=${encodeURIComponent(calibrationType)}&n=${PDB_CALIBRATION_N}`;
    const resp = await fetch(url);
    if (!resp.ok) throw new Error("Calibration PDB load failed");
    const pdbText = await resp.text();

    tmpViewer.addModel(pdbText, "pdb", { keepH: true });
    if (typeof tmpViewer.setProjection === "function") {
      tmpViewer.setProjection(projKind === "orthographic" ? "orthographic" : "perspective");
    }

    // fit + close-up → salvăm VIEW COMPLET
    tmpViewer.zoomTo();
    const z = (projKind === "orthographic")
      ? (PDB_DEFAULT_CLOSEUP_MULT * PDB_ORTHO_ZOOM_COMP)
      : PDB_DEFAULT_CLOSEUP_MULT;

    tmpViewer.zoom(z);
    tmpViewer.render();

    window.__PDB_DEFAULT_VIEW = window.__PDB_DEFAULT_VIEW || { perspective: null, orthographic: null };
    window.__PDB_DEFAULT_VIEW[projKind] = tmpViewer.getView();

    return true;
  } catch (e) {
    console.warn("Default view calibration failed:", e);
    return false;
  } finally {
    document.body.removeChild(tmp);
  }
}

function getCurrentProjectionKind(kind) {
  const proj = getCurrentPdbProjection(kind);
  return (proj === "orthographic") ? "orthographic" : "perspective";
}

function pdbHasViewAPI(viewer) {
  return viewer && (typeof viewer.getView === "function") && (typeof viewer.setView === "function");
}

// Normalize: recenter pe modelul curent, DAR păstrăm camera (zoom+distance+rot) identică
function pdbNormalizeCamera(viewer, projKind) {
  if (!viewer || !pdbHasViewAPI(viewer)) return;

  const def = window.__PDB_DEFAULT_VIEW[projKind];
  if (!def) {
    viewer.zoomTo();
    const z = (projKind === "orthographic")
	  ? (PDB_DEFAULT_CLOSEUP_MULT * PDB_ORTHO_ZOOM_COMP)
	  : PDB_DEFAULT_CLOSEUP_MULT;

	viewer.zoom(z);
    viewer.render(); // UN SINGUR render
    return;
  }

  // 1) Facem fit (dar fără render intermediar)
  viewer.zoomTo();

  const centered = viewer.getView();
  if (!centered || typeof centered !== "object") {
    viewer.render();
    return;
  }

  // 2) Construim view final: păstrăm centrul, forțăm camera din default
  const v = { ...centered };

  const KEEP_CENTER_KEYS = [
    "trans", "translation", "center", "origin", "target", "lookat", "focus",
    "pan", "shift", "offset",
    "t", "tx", "ty", "tz"
  ];

  for (const k in def) {
    if (!Object.prototype.hasOwnProperty.call(def, k)) continue;

    const lk = String(k).toLowerCase();
    const keep = KEEP_CENTER_KEYS.some(s => lk === s || lk.includes(s));
    if (keep) continue;

    v[k] = def[k];
  }

  viewer.setView(v);

  // 3) Optional: centrează, dar tot fără render intermediar
  if (typeof viewer.center === "function") {
    viewer.center();
  }

  viewer.render(); // UN SINGUR render final
}


function applyPdbStyleAndDisplay(kind, doRender = true) {
  let viewerId = null;

  if (kind === "gradius") {
    viewerId = "pdb-viewer-gradius";
  } else if (kind === "sasa") {
    viewerId = "pdb-viewer-sasa";
  } else {
    return;
  }

  const viewer = getPdbViewer(viewerId);
  if (!viewer) return;

  const style = getCurrentPdbStyle(kind);
  const display = getCurrentPdbDisplay(kind);
  const proj = getCurrentPdbProjection(kind);

  let styleSpec;

  if (style === "line") {
    styleSpec = { stick: { radius: 0.08 } };
  } else if (style === "stick") {
    styleSpec = { stick: { radius: 0.25 } };
  } else if (style === "cpk") {
    styleSpec = { stick: { radius: 0.12 }, sphere: { scale: 0.25 } };
  } else if (style === "vdw") {
    styleSpec = { sphere: { scale: 1.0 } };
  } else {
    styleSpec = { stick: { radius: 0.25 } };
  }

  // aplicăm stilul de bază pentru toți atomii
  viewer.setStyle({}, styleSpec);

  // dacă display = "noh", ștergem stilul de pe hidrogeni
  if (display === "noh") {
    viewer.setStyle({ elem: "H" }, {});
  }
  
  // proiectia orthographic
  if (typeof viewer.setProjection === "function") {
    if (proj === "orthographic") {
      viewer.setProjection("orthographic");
    } else {
      viewer.setProjection("perspective");
    }
  }
  if (doRender) viewer.render();
}


// Schimbă reprezentarea 3D în viewer: lines / licorice / CPK / VDW
function changePdbStyle(kind) {
  // nu avem nevoie de 'style' din argument, citim direct radio curent
  applyPdbStyleAndDisplay(kind);
}

// Schimbă modul de display: all / noh
function changePdbDisplay(kind) {
  // la fel, citim direct radio curent
  applyPdbStyleAndDisplay(kind);
}


function changePdbProjection(kind) {
  applyPdbStyleAndDisplay(kind, false);

  // după schimbarea proiecției, reaplicăm view-ul default pentru acel mod
  const viewerId = (kind === "gradius") ? "pdb-viewer-gradius"
                : (kind === "sasa") ? "pdb-viewer-sasa"
                : null;
  if (!viewerId) return;

  const viewer = getPdbViewer(viewerId);
  if (!viewer) return;

  const projKind = getCurrentProjectionKind(kind);

  // Reaplicăm default view pentru proiecția selectată
  pdbEnsureDefaultViewExistsForTemplate(projKind).then(() => {
    pdbNormalizeCamera(viewer, projKind);
  });
}


function pdbZoomIn(containerId) {
  const v = getPdbViewer(containerId);
  if (!v) return;
  v.zoom(1.25);
  v.render();
}

function pdbZoomOut(containerId) {
  const v = getPdbViewer(containerId);
  if (!v) return;
  v.zoom(0.8);
  v.render();
}

function pdbResetView(containerId) {
  const container = document.getElementById(containerId);
  if (!container || !container._pdbViewer) return;

  const v = container._pdbViewer;
  
  // reset la default view (same zoom always)
  const kind = container.dataset.kind || (containerId.includes("gradius") ? "gradius" : "sasa");
  const projKind = getCurrentProjectionKind(kind);

  // NU mai așteptăm ensure() ca să evităm delay.
  // Dacă default view există deja, normalizează imediat.
  // În paralel, rulează ensure ca fallback pentru viitor.
  if (window.__PDB_DEFAULT_VIEW && window.__PDB_DEFAULT_VIEW[projKind]) {
    pdbNormalizeCamera(v, projKind);
  } else {
    pdbNormalizeCamera(v, projKind);
    pdbEnsureDefaultViewExistsForTemplate(projKind).catch(() => {});
  }
}

function downloadPdbPng(containerId) {
  const v = getPdbViewer(containerId);
  if (!v || typeof v.pngURI !== "function") return;

  // ne asigurăm că e randat
  v.render();

  const uri = v.pngURI(); // data:image/png;base64,...

  if (!uri) return;

  const a = document.createElement("a");
  a.href = uri;
  a.download = "Polymer3D.png";   // poți schimba numele dacă vrei
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}


function setupPdbWheelControl(viewerId) {
  const container = document.getElementById(viewerId);
  if (!container) return;

  // implicit: scroll-zoom dezactivat
  if (!container.dataset.scrollZoom) {
    container.dataset.scrollZoom = "0";
  }

  // atașăm handlerul o singură dată
  if (container._pdbWheelHandlerAttached) return;
  container._pdbWheelHandlerAttached = true;

  container.addEventListener(
    "wheel",
    function (event) {
      const allowZoom = this.dataset.scrollZoom === "1";

      if (!allowZoom) {
        // NU vrem zoom în 3D → blocăm handlerul 3Dmol,
        // dar lăsăm scroll-ul paginii să meargă normal.
        if (event.stopImmediatePropagation) {
          event.stopImmediatePropagation();
        } else {
          event.stopPropagation();
        }
        // NU dăm preventDefault → pagina scroll-ează
        return;
      } else {
        // Zoom activ din buton → zoom în 3D, nu în pagină
        event.preventDefault();
      }
    },
    { passive: false, capture: true }
  );
}


function setupPdbPanControl(viewerId) {
  const container = document.getElementById(viewerId);
  if (!container) return;

  // atașăm o singură dată
  if (container._pdbPanHandlerAttached) return;
  container._pdbPanHandlerAttached = true;

  function forceCtrlKey(e) {
    // dacă Pan nu e activ → nu facem nimic
    if (container.dataset.panMode !== "1") return;

    try {
      // încercăm să suprascriem ctrlKey pentru acest eveniment
      Object.defineProperty(e, "ctrlKey", {
        get: () => true,
        configurable: true
      });
    } catch (_) {
      // fallback (unele browsere pot permite direct atribuire)
      e.ctrlKey = true;
    }
    // NU facem preventDefault/stopPropagation ca 3Dmol să primească evenimentul
  }

  // în capture-phase, înainte de handler-ele 3Dmol
  container.addEventListener("mousedown", forceCtrlKey, true);
  container.addEventListener("mousemove", forceCtrlKey, true);
}


function setupPdbTouchControls(viewerId) {
  const container = document.getElementById(viewerId);
  if (!container) return;

  if (container._pdbTouchHandlerAttached) return;
  container._pdbTouchHandlerAttached = true;

  // 3Dmol ascultă pe canvas – pe mobil canvas-ul poate apărea după attach,
  // deci îl căutăm DINAMIC de fiecare dată.
  function getCanvas() {
    return container.querySelector("canvas") || container;
  }

  let lastX = null, lastY = null;

  function dispatchCtrlMouse(type, x, y) {
    const ev = new MouseEvent(type, {
      bubbles: true,
      cancelable: true,
      clientX: x,
      clientY: y,
      buttons: 1,
      ctrlKey: true
    });
    getCanvas().dispatchEvent(ev);
  }

  function dispatchWheel(deltaY, x, y) {
    const ev = new WheelEvent("wheel", {
      bubbles: true,
      cancelable: true,
      clientX: x,
      clientY: y,
      deltaY: deltaY
    });
    getCanvas().dispatchEvent(ev);
  }

  container.addEventListener("touchstart", (e) => {
    if (e.touches.length !== 1) return;

    const t = e.touches[0];
    lastX = t.clientX; 
    lastY = t.clientY;

    const panOn  = container.dataset.panMode === "1";
    const zoomOn = container.dataset.scrollZoom === "1";

    // Dacă Pan/Zoom sunt active -> blocăm scroll-ul paginii și controlăm noi gestul
    if (panOn || zoomOn) {
      if (e.cancelable) e.preventDefault();
      e.stopImmediatePropagation();
	  
	  if (panOn) dispatchCtrlMouse("mousedown", lastX, lastY);
	  
    } else {
      return;
    }

  }, { passive: false, capture: true });

  container.addEventListener("touchmove", (e) => {
    if (e.touches.length !== 1) return;

    const t = e.touches[0];
    const x = t.clientX, y = t.clientY;

    const panOn  = container.dataset.panMode === "1";
    const zoomOn = container.dataset.scrollZoom === "1";

    if (panOn) {
      if (e.cancelable) e.preventDefault();
      e.stopImmediatePropagation();
      dispatchCtrlMouse("mousemove", x, y);
    } else if (zoomOn) {
      if (e.cancelable) e.preventDefault();
      e.stopImmediatePropagation();

      // drag vertical = zoom (simulăm wheel)
      const dy = y - lastY;
      dispatchWheel(dy * 2.2, x, y);
    } else {
      return;
    }

    lastX = x; 
    lastY = y;
	
  }, { passive: false, capture: true });

  container.addEventListener("touchend", () => {
    if (container.dataset.panMode === "1" && lastX != null && lastY != null) {
      dispatchCtrlMouse("mouseup", lastX, lastY);
    }
    lastX = lastY = null;
  }, { passive: true });

  container.addEventListener("touchcancel", () => {
    if (container.dataset.panMode === "1" && lastX != null && lastY != null) {
      dispatchCtrlMouse("mouseup", lastX, lastY);
    }
    lastX = lastY = null;
  }, { passive: true });
}


function setupPdbCursorHelpers(viewerId) {
  const container = document.getElementById(viewerId);
  if (!container) return;

  const canvas = container.querySelector('canvas');
  if (!canvas) {
    // încearcă din nou pe frame-ul următor (canvas poate apărea mai târziu)
    requestAnimationFrame(() => setupPdbCursorHelpers(viewerId));
    return;
  }

  // atașăm helperii o singură dată per canvas
  if (canvas._pdbCursorHelpersAttached) return;
  canvas._pdbCursorHelpersAttached = true;

  let ctrlDown = false;
  let middleDown = false;

  function updateCursor() {
    const panMode = container.dataset.panMode === "1";

    if (panMode || ctrlDown || middleDown) {
      // Pan sau Ctrl sau middle mouse
      canvas.style.cursor = 'move';
    } else {
      // stare normală
      canvas.style.cursor = 'default';
    }
  }

  // îl facem vizibil și din alte funcții (Pan button)
  canvas._updatePdbCursor = updateCursor;

  window.addEventListener('keydown', (e) => {
    if (e.key === 'Control') {
      ctrlDown = true;
      updateCursor();
    }
  });

  window.addEventListener('keyup', (e) => {
    if (e.key === 'Control') {
      ctrlDown = false;
      updateCursor();
    }
  });

  canvas.addEventListener('mousedown', (e) => {
    // butonul de scroll = middle button = 1
    if (e.button === 1) {
      middleDown = true;
      updateCursor();
    }
  });

  window.addEventListener('mouseup', (e) => {
    if (e.button === 1) {
      middleDown = false;
      updateCursor();
    }
  });

  canvas.addEventListener('mouseleave', () => {
    middleDown = false;
    updateCursor();
  });

  // stare inițială
  updateCursor();
}


// bara Plotly pentru 3D
function attachPlotlyModebarTo3D(graphDivId, wrapperId, viewerId) {
  const plotDiv = document.getElementById(graphDivId);
  const wrapper = document.getElementById(wrapperId);
  if (!plotDiv || !wrapper) return;
  
  // Host dedicat pentru bara 3D (în afara viewer-ului): pdb-toolbar-gradius / pdb-toolbar-sasa
  const hostId = wrapperId.replace("pdb-wrapper", "pdb-toolbar");
  const host = document.getElementById(hostId) || wrapper;

  // wrapper-ul trebuie să fie "relative" ca bara absolută să stea corect în colț
  if (!wrapper.style.position) wrapper.style.position = "relative";
  
  const isCoarsePointer = window.matchMedia("(hover: none) and (pointer: coarse)").matches;

  // ne asigurăm că viewerul are controlul de scroll configurat
  setupPdbWheelControl(viewerId);
  setupPdbPanControl(viewerId);
  setupPdbTouchControls(viewerId);

  const oldClone = host.querySelector(".modebar-3d-clone");
  if (oldClone) oldClone.remove();

  // Luăm bara originală Plotly de pe graficul 2D
  const originalModebar = plotDiv.querySelector(".modebar");
  if (!originalModebar) return;

  // Clonăm bara cu tot HTML-ul, iconițele și data-title-urile
  const clone = originalModebar.cloneNode(true);
  clone.classList.add("modebar-3d-clone");

  // O poziționăm în HOST (în afara viewer-ului), fără absolute / top negativ
  clone.style.position = "relative";
  clone.style.top = "0";
  clone.style.right = "0";
  clone.style.left = "auto";
  clone.style.zIndex = "1";
  clone.style.pointerEvents = "auto";

  // === referințe la butoane pentru exclusivitate ===
  let zoomToolBtn = null; // "Zoom" (scroll-zoom)
  let panToolBtn = null;  // "Pan"

  function killStickyFocus(el) {
    if (!el) return;
    try { el.blur(); } catch (_) {}
    if (isCoarsePointer) {
      // pe mobil uneori focus-ul rămâne pe activeElement
      requestAnimationFrame(() => {
        try { document.activeElement && document.activeElement.blur && document.activeElement.blur(); } catch (_) {}
      });
    }
  }

  function setBtnOn(btn, isOn) {
    if (!btn) return;
    btn.classList.toggle("active", !!isOn);
    // unele build-uri Plotly mai folosesc și asta (nu strică)
    btn.classList.toggle("modebar-btn--active", !!isOn);
    btn.setAttribute("aria-pressed", isOn ? "true" : "false");
    killStickyFocus(btn);
  }

  function deactivateZoom(target) {
    if (!target) return;
    target.dataset.scrollZoom = "0";
    setBtnOn(zoomToolBtn, false);
    const canvas = target.querySelector("canvas");
    if (canvas && typeof canvas._updatePdbCursor === "function") canvas._updatePdbCursor();
  }

  function deactivatePan(target) {
    if (!target) return;
    target.dataset.panMode = "0";
    setBtnOn(panToolBtn, false);
    const canvas = target.querySelector("canvas");
    if (canvas && typeof canvas._updatePdbCursor === "function") canvas._updatePdbCursor();
  }

  function activateZoom(target) {
    if (!target) return;
    target.dataset.scrollZoom = "1";
    setBtnOn(zoomToolBtn, true);
    const canvas = target.querySelector("canvas");
    if (canvas && typeof canvas._updatePdbCursor === "function") canvas._updatePdbCursor();
  }

  function activatePan(target) {
    if (!target) return;
    target.dataset.panMode = "1";
    setBtnOn(panToolBtn, true);
    const canvas = target.querySelector("canvas");
    if (canvas && typeof canvas._updatePdbCursor === "function") canvas._updatePdbCursor();
  }

  // Re-mapează butoanele spre viewerul 3D
  clone.querySelectorAll(".modebar-group .modebar-btn").forEach((btn) => {
	const rawTitle = btn.getAttribute("data-title") || "";
    const title = rawTitle.trim().toLowerCase();
	
	// Mobile (touch): afișăm eticheta (tooltip) la tap, timp de ~1s
    if (isCoarsePointer) {
      btn.addEventListener("click", () => {
        btn.classList.add("show-tooltip");
        if (btn._tooltipTimer) clearTimeout(btn._tooltipTimer);
        btn._tooltipTimer = setTimeout(() => {
          btn.classList.remove("show-tooltip");
        }, 1200);
      }, true);
    }

    if (title === "zoom") {
      zoomToolBtn = btn;
    } else if (title.includes("pan")) {
      panToolBtn = btn;
    }

    // scoatem handler-ele vechi (pentru 2D)
    btn.onmouseover = null;
    btn.onmouseout = null;
    btn.onmousedown = null;
    btn.onmouseup = null;

    if (title.includes("zoom in")) {
      // Zoom in pe 3D
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        pdbZoomIn(viewerId);
      });
    } else if (title.includes("zoom out")) {
      // Zoom out pe 3D
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        pdbZoomOut(viewerId);
      });
    } else if (title.includes("autoscale") || title.includes("reset axes")) {
      // Reset view 3D
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        pdbResetView(viewerId);
      });
    } else if (title === "zoom") {
      // Zoom 3D: toggle ON/OFF; dacă îl aprindem, stingem Pan
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const target = document.getElementById(viewerId);
        if (!target) return;

        const wasActive = target.dataset.scrollZoom === "1";

        if (wasActive) {
          // era activ -> îl oprim (ambele pot fi OFF)
          deactivateZoom(target);
        } else {
          // era oprit -> îl aprindem și stingem Pan
          activateZoom(target);
          deactivatePan(target);
        }
		// FIX mobile: scoate orice focus/pressed vizual rămas după toggle
        killStickyFocus(btn);
      });
    } else if (title.includes("pan")) {
      // Pan 3D: toggle ON/OFF; dacă îl aprindem, stingem Zoom
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const target = document.getElementById(viewerId);
        if (!target) return;

        const wasActive = target.dataset.panMode === "1";

        if (wasActive) {
          // era activ -> îl oprim (ambele pot fi OFF)
          deactivatePan(target);
        } else {
          // era oprit -> îl aprindem și stingem Zoom
          activatePan(target);
          deactivateZoom(target);
        }
		// FIX mobile: scoate orice focus/pressed vizual rămas după toggle
		killStickyFocus(btn);
      });
    } else if (title.includes("download") && title.includes("png")) {
      // Butonul "Download plot as a png" din bara 3D → salvează imaginea 3D
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        downloadPdbPng(viewerId);
      });
    } else {
      // Restul butoanelor nu fac nimic în 3D
      btn.addEventListener("click", (e) => e.preventDefault());
    }

    // prevenim “drag” pe desktop fără să stricăm tap-ul pe mobile
	if (!window.matchMedia("(hover: none) and (pointer: coarse)").matches) {
	  btn.addEventListener("mousedown", (e) => e.preventDefault());
	}
	btn.addEventListener("dragstart", (e) => e.preventDefault());
  });

  // Atașăm bara clonată peste wrapper-ul 3D
  host.appendChild(clone);

  // Stare inițială: Zoom OFF, Pan OFF (scroll în pagină permis)
  const target = document.getElementById(viewerId);
  if (target) {
    deactivateZoom(target);
    deactivatePan(target);
  }
}


function generateGradius() {
  const btn = document.getElementById("generate-button-gradius");
  btn.disabled = true;

  const polymer = document.getElementById("polymer_type_gradius").value;
  if (!polymer) {
    btn.disabled = false;
    return;
  }

  const lengthsInput = document.getElementById("lengths_gradius").value.trim();
  const n = parseInt(lengthsInput, 10);
  const lengths = [n];

  fetch("/generate_gradius", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ polymer_type: polymer, lengths })
  })
    .then((resp) => resp.json())
    .then((data) => {
      if (!data.success) {
        throw new Error(data.message || "Error");
      }

      // 1) Facem secțiunile vizibile
	  ["graph-section-gradius", "predictions-section-gradius", "pdb-section-gradius"]
		.forEach((id) => {
		  const el = document.getElementById(id);
		  if (el) el.style.display = "block";
		});

	  const headerG = document.getElementById("computed-header-gradius");
	  if (headerG) headerG.style.display = "flex";

	  // afișăm panoul 3D Display options în dreapta
	  show3DMenu("gradius");

      // 2) Traces
      const traceRadiusTest = {
        x: data.gradius_test_x,
        y: data.gradius_test_y,
        mode: "markers",
        name: "Test Predictions",
        type: "scattergl",
        marker: { color: "black", size: 3 }
      };

      const traceRadiusUser = {
        x: data.Distance,
        y: data.pred_gradius,
        mode: "markers",
        name: "User Input",
        type: "scattergl",
        marker: { color: "red", size: 9 }
      };

      // 2.1) FIX: blocăm axa Oy la un range stabil (nu mai sare când folosești zoom/pan)
      const allY = []
        .concat(data.gradius_test_y || [])
        .concat(data.pred_gradius || []);

      let yMin = Math.min.apply(null, allY);
      let yMax = Math.max.apply(null, allY);

      if (!Number.isFinite(yMin) || !Number.isFinite(yMax)) {
        yMin = 0;
        yMax = 1;
      }

      const ySpan = yMax - yMin || 1;
      const yPad  = 0.05 * ySpan; // 5% padding sus/jos
      yMin -= yPad;
      yMax += yPad;

      // 3) Resetare forțată la modul normal (fără Pub) înainte de replotare
      const graphDiv = document.getElementById("graph-radius");
      graphDiv.classList.remove("pub");
      graphDiv.isResized = false;
      document.getElementById("toggle-size-btn-gradius").innerHTML =
        "📐 Resize Graph for Publication";

      // 4) Plot 2D
      Plotly.newPlot(
        "graph-radius",
        [traceRadiusTest, traceRadiusUser],
        {
          // title: { text: `Length vs Radius of Gyration for ${data.polymer}`, x: 0.08 },
          xaxis: {
            title: { text: "Monomer number", standoff: 10 },
            tick0: 0,
            zeroline: true,
            showline: true,
            linecolor: "black",
            linewidth: 1,
            autorange: false,
            range: [-20, 1030]
          },
          yaxis: {
            title: "Radius [\u212B]",
            zeroline: false,
            autorange: false,          // <-- important
            range: [yMin, yMax],        // <-- range fix calculat mai sus
			fixedrange: false
          },
          template: "plotly_white",
          margin: { l: 60, r: 20, t: 40, b: 60 },
          height: 300,
          width: null,
          ...xTickConfig(graphDiv)
        },
        {
          displayModeBar: true,
          displaylogo: false,
          responsive: true,
          modeBarButtons: [
            [
              "toImage",
              "zoom2d",
              "pan2d",
              "zoomIn2d",
              "zoomOut2d",
              "resetScale2d"
            ]
          ],
          toImageButtonOptions: {
            format: "png",
            filename: "RG_figure"
          }
        }
      );

      stabilizeAndNormalizeTicks("graph-radius");
	  attachZoomClampToInitialRange("graph-radius");

      // 5) Label „for …”
      const lblG = document.getElementById("selected-polymer-label-gradius");
      if (lblG) {
        lblG.textContent = `for ${data.polymer}:`;
      }
	  
	  // Titlu dinamic grafic 2D
	  const titleG = document.getElementById("graph-title-polymer-gradius");
	  if (titleG) {
		titleG.textContent = data.polymer;
	  }

      // Titlu dinamic pentru 3D (3D Polymer Configuration for X :)
      const pdbLabelG = document.getElementById("pdb-polymer-label-gradius");
      if (pdbLabelG) {
        pdbLabelG.textContent = `for ${data.polymer}`;
      }

      // 6) Stats + detalii
      let details = '<span class="section-text" style="display:block; margin-top:0;">';
      for (let i = 0; i < data.Distance.length; i++) {
        details +=
          `Monomer Number: ${data.Distance[i]} <br>` +
          `Radius of Gyration: ${data.pred_gradius[i].toFixed(3)} \u212B<br>`;
      }
      details += "</span>";

      const gradius_stats = `
        <div class="section-text" style="margin:0 0 0.5em 0;">
          Average predicted value = ${data.gradius_avg_pred_gradius.toFixed(3)} \u212B<br>
          Average test set error = ${data.gradius_avg_error_gradius.toFixed(3)} \u212B
        </div>`;

      document.getElementById("predictions-gradius").innerHTML = details;
      document.getElementById("stats-gradius").innerHTML = gradius_stats;

      // 7) 3D VIEWER
      const monomerNumber = lengths[0]; // ce a introdus userul
      const polymerType = polymer;      // PE, PEI etc.

      updatePdbViewer("pdb-viewer-gradius", polymerType, monomerNumber);
      attachPlotlyModebarTo3D(
        "graph-radius",
        "pdb-wrapper-gradius",
        "pdb-viewer-gradius"
      );

      btn.disabled = false;
    })
    .catch((err) => {
      document.getElementById("predictions-gradius").innerHTML =
        `<span class="text-red-500">${err.message}</span>`;
      btn.disabled = false;
    });
}


function validateInputSasa() {
  const inputField     = document.getElementById("lengths_sasa");
  const errorMessage   = document.getElementById("error-message-sasa");
  const generateButton = document.getElementById("generate-button-sasa");
  const polymer        = document.getElementById("polymer_type_sasa").value;  // hidden

  const value = inputField.value.trim();
  const regex = /^[1-9]\d*$/;

  const polymerOk = polymer !== "" && polymer !== null;

  //  dacă inputul e gol → ascund mesajul, dezactivez butonul
  if (value === "") {
    errorMessage.classList.add("hidden");
    generateButton.disabled = true;
    return;
  }

  //  dacă este număr valid
  if (regex.test(value)) {
    const numericValue = parseInt(value, 10);

    // dacă e > 1000 → EROARE (indiferent dacă polimerul e selectat sau nu!)
    if (numericValue > 1000) {
      errorMessage.classList.remove("hidden");
      errorMessage.textContent =
        "*Please enter a single positive integer less than or equal to 1000.";
      generateButton.disabled = true;
      return;
    }

    //  număr valid între 1 și 1000 → mesaj ascuns
    errorMessage.classList.add("hidden");

    //  butonul se activează DOAR dacă polimerul este selectat
    generateButton.disabled = !polymerOk;
    return;
  }

  //  dacă NU e număr valid
  errorMessage.classList.remove("hidden");
  errorMessage.textContent =
    "*Please enter a single positive integer less than or equal to 1000.";
  generateButton.disabled = true;
}


function generateSasa() {
  const btn = document.getElementById("generate-button-sasa");
  btn.disabled = true;

  const polymer = document.getElementById("polymer_type_sasa").value;
  if (!polymer) {
    btn.disabled = false;
    return;
  }

  const lengthsInput = document.getElementById("lengths_sasa").value.trim();
  const n = parseInt(lengthsInput, 10);
  const lengths = [n];

  fetch("/generate_sasa", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ polymer_type: polymer, lengths })
  })
    .then((resp) => resp.json())
    .then((data) => {
      if (!data.success) {
        throw new Error(data.message || "Error");
      }

      // 1) Afișăm secțiunile înainte să plotezi
	  ["graph-section-sasa", "predictions-section-sasa", "pdb-section-sasa"]
		.forEach((id) => {
		  const el = document.getElementById(id);
		  if (el) el.style.display = "block";
		});

	  const headerS = document.getElementById("computed-header-sasa");
	  if (headerS) headerS.style.display = "flex";
	  
	  // afișăm panoul 3D Display options în dreapta
	  show3DMenu("sasa");

      // 2) Traces
      const traceSasaTest = {
        x: data.sasa_test_x,
        y: data.sasa_test_y,
        mode: "markers",
        name: "Test Predictions",
        type: "scattergl",
        marker: { color: "black", size: 3 }
      };

      const traceSasaUser = {
        x: data.Distance,
        y: data.pred_sasa,
        mode: "markers",
        name: "User Input",
        type: "scattergl",
        marker: { color: "red", size: 9 }
      };

      // 3) Resetare mod „publication”
      const graphDiv = document.getElementById("graph-sasa");
      graphDiv.classList.remove("pub");
      graphDiv.isResized = false;
      document.getElementById("toggle-size-btn-sasa").innerHTML =
        "📐 Resize Graph for Publication";
		
	  // FIX: calculează yMin/yMax ca la GRADIUS
	  const allY = []
		.concat(data.sasa_test_y || [])
		.concat(data.pred_sasa || []);

	  let yMin = Math.min.apply(null, allY);
	  let yMax = Math.max.apply(null, allY);

	  if (!Number.isFinite(yMin) || !Number.isFinite(yMax)) {
		yMin = 0;
		yMax = 1;
	  }

	  const ySpan = yMax - yMin || 1;
	  const yPad  = 0.05 * ySpan;
	  yMin -= yPad;
	  yMax += yPad;

      // 4) Plot 2D
      Plotly.newPlot(
        "graph-sasa",
        [traceSasaTest, traceSasaUser],
        {
          // title: { text: `Length vs SASA for ${data.polymer}`, x: 0.08 },
          xaxis: {
            title: { text: "Monomer number", standoff: 10 },
            tick0: 0,
            zeroline: true,
            showline: true,
            linecolor: "black",
            linewidth: 1,
            autorange: false,
            range: [-20, 1030]
          },
          yaxis: {
			title: "SASA [\u212B\u00B2]",
			zeroline: false,
			autorange: false,
			range: [yMin, yMax],
			fixedrange: false      // ⬅️ la fel, o “înghețăm”
		  },
          template: "plotly_white",
          margin: { l: 60, r: 20, t: 40, b: 60 },
          height: 300,
          width: null,
          ...xTickConfig(graphDiv)
        },
        {
          displayModeBar: true,
          displaylogo: false,
          responsive: true,
          modeBarButtons: [
            [
              "toImage",
              "zoom2d",
              "pan2d",
              "zoomIn2d",
              "zoomOut2d",
              "resetScale2d"
            ]
          ],
          // setări pentru salvare imagine/publicație
          toImageButtonOptions: {
            format: "png",        // sau 'svg' pentru vectorial
            filename: "SASA_figure"
          }
        }
      );

      stabilizeAndNormalizeTicks("graph-sasa");
	  attachZoomClampToInitialRange("graph-sasa");

      // 5) Label polymer
      const lblS = document.getElementById("selected-polymer-label-sasa");
      if (lblS) {
        lblS.textContent = `for ${data.polymer}:`;
      }
	  
	  // Titlu dinamic grafic 2D
	  const titleS = document.getElementById("graph-title-polymer-sasa");
	  if (titleS) {
		titleS.textContent = data.polymer;
	  }

      // Titlu dinamic pentru 3D
      const pdbLabelS = document.getElementById("pdb-polymer-label-sasa");
      if (pdbLabelS) {
        pdbLabelS.textContent = `for ${data.polymer}`;
      }

      // 6) Stats și detalii
      let details =
        '<span class="section-text" style="display:block; margin-top:0;">';
      for (let i = 0; i < data.Distance.length; i++) {
        details +=
          `Monomer Number: ${data.Distance[i]} <br>` +
          `SASA: ${data.pred_sasa[i].toFixed(3)} \u212B\u00B2<br>`;
      }
      details += "</span>";

      const sasa_stats = `
		<div class="section-text" style="margin:0 0 0.5em 0;">
		  Average predicted value = ${data.sasa_avg_pred_sasa.toFixed(3)} Å²<br>
		  Average test set error = ${data.sasa_avg_error_sasa.toFixed(3)} Å²
		</div>`;

      document.getElementById("predictions-sasa").innerHTML = details;
      document.getElementById("stats-sasa").innerHTML = sasa_stats;

      // 7) 3D VIEWER
      const monomerNumber = lengths[0];
      const polymerType = polymer;

      updatePdbViewer("pdb-viewer-sasa", polymerType, monomerNumber);
      attachPlotlyModebarTo3D(
        "graph-sasa",
        "pdb-wrapper-sasa",
        "pdb-viewer-sasa"
      );

      btn.disabled = false;
    })
    .catch((err) => {
      document.getElementById("predictions-sasa").innerHTML =
        `<span class="text-red-500">${err.message}</span>`;
      btn.disabled = false;
    });
}


// Afișează panoul 3D Display options pentru GRADIUS / SASA
function show3DMenu(kind) {
  let wrapperId = null;

  if (kind === "gradius") {
    wrapperId = "pdb-wrapper-gradius";
  } else if (kind === "sasa") {
    wrapperId = "pdb-wrapper-sasa";
  } else {
    return;
  }

  const wrapper = document.getElementById(wrapperId);
  if (!wrapper) return;  // protecție: nu aruncăm eroare dacă nu există

  const menu = wrapper.querySelector(".pdb-3d-menu");
  if (!menu) return;

  menu.classList.add("visible");
}


function switch3DMenuTab(btn, tabName) {
  const menu = btn.closest(".pdb-3d-menu");
  if (!menu) return;

  // tab-urile
  const tabs = menu.querySelectorAll(".pdb-3d-tab");
  tabs.forEach((t) => {
    t.classList.toggle("active", t === btn);
  });

  // conținutul tab-urilor
  const contents = menu.querySelectorAll(".pdb-3d-tab-content");
  contents.forEach((c) => {
    const isTarget = c.dataset.tab === tabName;
    c.style.display = isTarget ? "" : "none";
  });
}


function toggleGraphSize(graphId, btnId) {
  const plot = document.getElementById(graphId);
  const btn  = document.getElementById(btnId);
  if (!plot || !btn) return;
  if (!isPlotlyReady(plot)) return;  // nu încerca să relayout dacă graficul nu e creat încă

  // NOTĂ: nu mai setăm width fix -> lăsăm Plotly să ocupe 100% din container
  if (!plot.isResized) {
    // intrăm în modul „publication”: limităm containerul, nu graficul
    plot.classList.add('pub');

    // înălțime puțin mai mare + margini pentru hârtie
    Plotly.relayout(plot, {
		autosize: false,    // dezactivăm autosize, altfel ignoră width/height fixe
		width: 680,         // ≈ 85 mm, single-column standard
		height: 400,        // proporțional, clar pentru publicații
		margin: { l: 60, r: 30, t: 50, b: 60 },
		'xaxis.title.standoff': 20,
		'yaxis.title.standoff': 20,
		'xaxis.zeroline': true,
		'xaxis.zerolinecolor': 'black',
		'xaxis.autorange': false,
		'xaxis.range': [-50, 1100],
		'yaxis.zeroline': false
	});
	
	const xMin = -50;
	const xMax = 1100;
	plot._zoomClampInitialXSpan = xMax - xMin; // 1100
	
	 // ADĂUGĂ: export FIX pentru publicare (PNG ~300 dpi)
    if (plot._context) {
      plot._context.toImageButtonOptions = {
        format: 'png',
        filename: (plot.id || graphId || 'figure') + '_publication',
        width: 680,
        height: 400,
        scale: 4
      };
    }

    // normalizează ticks în funcție de noua lățime
    stabilizeAndNormalizeTicks(graphId);

    btn.innerHTML = "🔄 Reset Graph Size";
    plot.isResized = true;
  } else {
    // ieșim din modul „publication”
    plot.classList.remove('pub');

    Plotly.relayout(plot, {
      autosize: true,
      width: null,
      height: 300,
      margin: { l: 60, r: 20, t: 40, b: 60 },
      'xaxis.title.standoff': 10,
	  'xaxis.zeroline': true,
	  'xaxis.zerolinecolor': 'black',
	  'xaxis.autorange': false,
	  'xaxis.range': [-20, 1030],
	  'yaxis.zeroline': false
    });
	
	// ADĂUGĂ: export „ca pe ecran” (alungit/responsive)
    if (plot._context) {
      plot._context.toImageButtonOptions = {
        format: 'png',
        filename: plot.id || graphId || 'figure' // fără width/height/scale
      };
    }

    // normalizează din nou pentru containerul normal
    stabilizeAndNormalizeTicks(graphId);

    btn.innerHTML = "📐 Resize Graph for Publication";
    plot.isResized = false;
  }
  // asigură-te că reacționează ca la Generate Graph
  Plotly.Plots.resize(plot);
  // plot.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}


// Funcție globală de reflow (o folosim și în resize și în toggleMenu)
function resizeGraphs() {
  const graphs = [
    document.getElementById('graph-radius'),
    document.getElementById('graph-sasa')
  ];

  graphs.forEach(el => {
    if (!el) return;
	if (!isPlotlyReady(el)) return;  // oprește înainte de Plotly.Plots.resize/relayout

    if (el.isResized) {
      const containerW = (el.parentElement?.clientWidth || 560) - 16;
      const W = Math.max(320, Math.min(680, containerW));
      const Hcap = Math.floor(window.innerHeight * 0.5);
      const H = Math.min(420, Math.round(W * 3/4), Hcap);

      const dynamicCfg = xTickConfig(el);
      Plotly.relayout(el, {
        autosize: false,
        width: W,
        height: H,
        ...dynamicCfg,
        'xaxis.autorange': false,
        'xaxis.range': [-50, 1100]
      });
      Plotly.Plots.resize(el);
      return;
    }

    Plotly.Plots.resize(el);

    const w = el.clientWidth || 800;
    const prefer50 = w >= 1100;

    const dynamicCfg = xTickConfig(el);
    const extra = prefer50
      ? { 'xaxis.tickmode': 'linear', 'xaxis.dtick': 50 }
      : { 'xaxis.tickmode': 'auto',   'xaxis.dtick': null };

    Plotly.relayout(el, { 
      ...dynamicCfg, 
      ...extra,
      'xaxis.autorange': false,
      'xaxis.range': [-50, 1100]
    });
  });
}
  
  // expune funcțiile pentru atributul onclick=""
  window.toggleSubmenu = toggleSubmenu;
  window.toggleMenu    = toggleMenu;
  window.showContent   = showContent;
  
//  Function for Documentation page  //
function openLearnMoreDocumentation(event) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }

  showContent("learn-more", null);

  if (typeof isTouchDrawerMode === "function" && isTouchDrawerMode()) {
    const sidebar = document.getElementById("sidebar");
    if (sidebar?.classList.contains("open")) {
      toggleMenu(false);
    }
  }

  const mainEl = document.querySelector("main");
  if (mainEl) {
    mainEl.scrollTo({ top: 0, behavior: "smooth" });
  }
}

window.openLearnMoreDocumentation = openLearnMoreDocumentation;



// =======  The 3rd code block ========  //
function validatePassword() {
    const password = document.getElementById('signUpPassword').value;

    const numberMessage = document.getElementById('passwordNumber');
    const lengthMessage = document.getElementById('passwordLength');
    const upperMessage = document.getElementById('passwordUpper');
    const specialMessage = document.getElementById('passwordSpecial');

    if (password.length === 0) {
        // Hide all messages if password is empty
        numberMessage.classList.add('hidden');
        lengthMessage.classList.add('hidden');
        upperMessage.classList.add('hidden');
        specialMessage.classList.add('hidden');
        return;
    }

    const hasNumber = /\d/.test(password);
    const isLongEnough = password.length >= 8;
    const hasUpper = /[A-Z]/.test(password);
    const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(password);

    numberMessage.classList.toggle('hidden', hasNumber);
    lengthMessage.classList.toggle('hidden', isLongEnough);
    upperMessage.classList.toggle('hidden', hasUpper);
    specialMessage.classList.toggle('hidden', hasSpecial);
}
	
		
function validateConfirmPassword() {
    const password = document.getElementById('signUpPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const message = document.getElementById('confirmMessage');

    message.classList.toggle('hidden', password === confirmPassword);
}
		
			
function validateResetPassword() {
    const password = document.getElementById('newPassword').value;

    const numberMessage = document.getElementById('resetNumber');
    const lengthMessage = document.getElementById('resetLength');
    const upperMessage = document.getElementById('resetUpper');
    const lowerMessage = document.getElementById('resetLower');
    const specialMessage = document.getElementById('resetSpecial');

    if (password.length === 0) {
        numberMessage.classList.add('hidden');
        lengthMessage.classList.add('hidden');
        upperMessage.classList.add('hidden');
        lowerMessage.classList.add('hidden');
        specialMessage.classList.add('hidden');
        return;
    }

    numberMessage.classList.toggle('hidden', /\d/.test(password));
    lengthMessage.classList.toggle('hidden', password.length >= 8);
    upperMessage.classList.toggle('hidden', /[A-Z]/.test(password));
    lowerMessage.classList.toggle('hidden', /[a-z]/.test(password));
    specialMessage.classList.toggle('hidden', /[!@#$%^&*(),.?":{}|<>]/.test(password));
}


function validateResetConfirmPassword() {
    const password = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmNewPassword').value;
    const message = document.getElementById('resetConfirmMessage');

    message.classList.toggle('hidden', password === confirmPassword);
}


// ===== Scroll lock (doar cât timp modalul e deschis) =====
function lockBodyScroll() {
  if (document.body.dataset.scrollLocked === "1") return;

  const y = window.scrollY || document.documentElement.scrollTop || 0;
  document.body.dataset.scrollLocked = "1";
  document.body.dataset.scrollY = String(y);

  document.body.style.position = "fixed";
  document.body.style.top = `-${y}px`;
  document.body.style.left = "0";
  document.body.style.right = "0";
  document.body.style.width = "100%";
  document.body.style.overflow = "hidden";
}

function unlockBodyScroll() {
  if (document.body.dataset.scrollLocked !== "1") return;

  const y = parseInt(document.body.dataset.scrollY || "0", 10) || 0;
  document.body.dataset.scrollLocked = "0";
  document.body.dataset.scrollY = "";

  document.body.style.position = "";
  document.body.style.top = "";
  document.body.style.left = "";
  document.body.style.right = "";
  document.body.style.width = "";
  document.body.style.overflow = "";

  window.scrollTo(0, y);
}

function openModal(id) {
    const modal = document.getElementById(id);
    if (modal) {
      modal.classList.remove("hidden");
		
	  // Blochează scroll pentru toate modalele din "allClosed"
      if (id === "loginModal" || id === "signUpModal" || id === "forgotPasswordModal" || id === "emailConfirmationModal" || id === "resetPasswordModal" || id === "historyModal") {
		  lockBodyScroll();
      }
	}
}

function closeModal(id) {
    document.getElementById(id).classList.add("hidden");

    const allClosed =
        document.getElementById("loginModal").classList.contains("hidden") &&
        document.getElementById("signUpModal").classList.contains("hidden") &&
        document.getElementById("forgotPasswordModal").classList.contains("hidden") &&
		document.getElementById("emailConfirmationModal").classList.contains("hidden") &&
		document.getElementById("resetPasswordModal").classList.contains("hidden") &&
		document.getElementById("historyModal").classList.contains("hidden");
		
    if (allClosed) {
		unlockBodyScroll(); // << ADĂUGAT (deblochează scroll când nu mai e niciun modal deschis)
        checkLoginStatus(); // va activa/dezactiva corect butonul pe baza /status
        document.getElementById("topBar").classList.remove("topbar-blur", "bg-opacity-50");
    }
}


function showLoginModal() {
    closeModal("signUpModal");
    closeModal("forgotPasswordModal");
	openModal("loginModal");
    document.getElementById("topBar").classList.add("topbar-blur", "bg-opacity-50");
    disableToggleButton();
			
	if (typeof grecaptcha !== "undefined" && loginWidgetId === null) {
		loginWidgetId = grecaptcha.render('recaptcha-login', { 'sitekey': window.RECAPTCHA_SITE_KEY });
	}
}


function showSignUpModal() {
    closeModal("loginModal");
    closeModal("forgotPasswordModal");
	openModal("signUpModal");
    document.getElementById("topBar").classList.add("topbar-blur", "bg-opacity-50");
    disableToggleButton();
			
	if (typeof grecaptcha !== "undefined" && signupWidgetId === null) {
		signupWidgetId = grecaptcha.render('recaptcha-signup', { 'sitekey': window.RECAPTCHA_SITE_KEY });
	}
}


function showForgotPasswordModal() {
    closeModal("loginModal");
    closeModal("signUpModal");
    openModal("forgotPasswordModal");
    disableToggleButton();

    if (typeof grecaptcha !== "undefined" && forgotWidgetId === null) {
        forgotWidgetId = grecaptcha.render('recaptcha-forgot', { 'sitekey': window.RECAPTCHA_SITE_KEY });
    }
}
		
let pendingConfirmationToken = null;
		
function showEmailConfirmationModal(status) {
    const title = document.getElementById("confirmationTitle");
    const msg1 = document.getElementById("confirmationMessage1");
    const msg2 = document.getElementById("confirmationMessage2");
    const note = document.getElementById("confirmationNote");
	const actionButton = document.getElementById("confirmationActionButton");

    // Reset all text content
    title.textContent = "";
    msg1.textContent = "";
    msg2.textContent = "";
    note.textContent = "";

    // Reset all title color classes
    title.className = "text-2xl font-semibold mb-4";  // base style only

	if (actionButton) {
		actionButton.textContent = "Go to Login";
		actionButton.dataset.action = "login";
	}

	if (status === "confirm_pending") {
		title.textContent = "Confirm Your Email";
		title.classList.add("text-blue-600");
		msg1.textContent = "Please confirm your email address to activate your account.";
		msg2.textContent = "Click the button below to complete confirmation.";
		note.textContent = "If you did not create this account, no further action is needed.";
		if (actionButton) {
			actionButton.textContent = "Confirm Email";
			actionButton.dataset.action = "confirm";
		}
	} else if (status === "pending") {
        title.textContent = "Check Your Email";
        title.classList.add("text-blue-600");  // BLUE
        msg1.textContent = "We've sent a confirmation link to your email address.";
        msg2.textContent = "Please click the link in the email to verify your email address before logging in.";
        note.textContent = "Email delivery may take a few minutes. Please check your spam folder if it doesn't arrive.";
    } else if (status === "success") {
        title.textContent = "Email Confirmed";
        title.classList.add("text-green-600");  // GREEN
        msg1.textContent = "Your email has been successfully confirmed.";
		msg2.textContent = "You can now log in.";
    } else if (status === "already") {
        title.textContent = "Already Confirmed";
        title.classList.add("text-blue-600");  // BLUE
        msg1.textContent = "Your email has already been confirmed.";
		msg2.textContent = "You can log in.";
    } else if (status === "expired") {
        title.textContent = "Link Expired";
        title.classList.add("text-red-600");  // RED
        msg1.textContent = "Your confirmation link has expired.";
		msg2.textContent = "Please sign up again.";
    } else if (status === "invalid") {
        title.textContent = "Invalid Link";
        title.classList.add("text-red-600");  // RED
        msg1.textContent = "The confirmation link is invalid. Please sign up again.";
		msg2.textContent = "Please sign up again.";
    }

    openModal("emailConfirmationModal");
    disableToggleButton();
}


function goToLoginFromConfirmation() {
    closeModal("emailConfirmationModal");
    showLoginModal();         // Open login modal
    disableToggleButton();    // Keep ☰ button frozen
}


function handleConfirmationAction() {
    const actionButton = document.getElementById("confirmationActionButton");

    if (actionButton && actionButton.dataset.action === "confirm") {
        confirmEmailFromModal();
        return;
    }

    goToLoginFromConfirmation();
}


function confirmEmailFromModal() {
    if (!pendingConfirmationToken) {
        showEmailConfirmationModal("invalid");
        return;
    }

    fetch(`/confirm/${encodeURIComponent(pendingConfirmationToken)}`, {
        method: "POST"
    })
    .then(res => res.json())
    .then(data => {
        pendingConfirmationToken = null;
        showEmailConfirmationModal(data.status || "invalid");
    })
    .catch(() => {
        pendingConfirmationToken = null;
        showEmailConfirmationModal("invalid");
    });
}


function enableToggleButton() {
    const toggleBtn = document.getElementById("menuToggle");  // Use unique ID

    if (toggleBtn) {
        toggleBtn.disabled = false;
        toggleBtn.removeAttribute("disabled");
        toggleBtn.style.pointerEvents = "auto";
        toggleBtn.style.opacity = "1";
        toggleBtn.style.cursor = "pointer";
        toggleBtn.classList.remove("opacity-50", "cursor-not-allowed");
    }
}


function disableToggleButton() {
    const toggleBtn = document.getElementById("menuToggle");  // Use unique ID

    if (toggleBtn) {
        toggleBtn.disabled = true;
        toggleBtn.setAttribute("disabled", "true");
        toggleBtn.style.pointerEvents = "none";
        toggleBtn.style.opacity = "0.5";
        toggleBtn.style.cursor = "not-allowed";
        toggleBtn.classList.add("opacity-50", "cursor-not-allowed");
    }
}


function signUpUser() {
    const name = document.getElementById("name").value;
    const email = document.getElementById("signUpEmail").value;
    const password = document.getElementById("signUpPassword").value;
    const confirmPassword = document.getElementById("confirmPassword").value;
    const organization = document.getElementById("organization").value;
    const affiliation = document.querySelector('input[name="affiliation"]:checked')?.value || '';

    const messageElem = document.getElementById("signUpMessage");
    messageElem.classList.remove("text-green-600");
    messageElem.classList.add("text-red-500");
    messageElem.classList.remove("hidden");

    if (password !== confirmPassword) {
        messageElem.textContent = "Passwords do not match.";
        return;
    }
	
	// === reCAPTCHA: read token from Sign Up widget ===
    let recaptchaToken = "";
	if (window.RECAPTCHA_BYPASS === true || window.RECAPTCHA_BYPASS === 'true') {
		recaptchaToken = "bypass";
	} else {
		recaptchaToken = (typeof grecaptcha !== "undefined" && signupWidgetId !== null)
			? grecaptcha.getResponse(signupWidgetId)
			: "";
		if (!recaptchaToken) {
			messageElem.classList.remove("hidden");
			messageElem.textContent = "Please complete reCAPTCHA.";
			return;
		}
	}

	// ---- SEND FLAT PAYLOAD (no nested user object) ----
    const user = {
        name,
        email,
        password,
        organization,
        affiliation,
		recaptchaToken
    };

    fetch("/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(user),
    })
    .then((res) => res.json())
    .then((data) => {
        if (!data.success) {
            if (data.code === "EMAIL_EXISTS") {
                messageElem.textContent = "Email already registered.";
            } else {
                messageElem.textContent = "Sign up failed. Try again.";
            }
			if (typeof grecaptcha !== "undefined" && signupWidgetId !== null) {
			  grecaptcha.reset(signupWidgetId);
			}
            return;
        }

        // SIGN UP SUCCESSFUL
        messageElem.classList.remove("text-red-500");
        messageElem.classList.add("text-green-600");
        messageElem.textContent = "Sign up successful! Redirecting...";

        setTimeout(() => {
            closeModal("signUpModal");

            // Fetch the confirmation status from the backend and show modal
            fetch(data.redirect)
                .then(res => res.json())
                .then(result => {
                    showEmailConfirmationModal(result.status);  // Show the correct status
                });
        }, 2000); // 2 seconds delay
    })
	.catch((error) => {
        console.error("Sign up error:", error);
        messageElem.textContent = "An error occurred. Please try again.";
	  
	    if (typeof grecaptcha !== "undefined" && signupWidgetId !== null) {
            grecaptcha.reset(signupWidgetId);
        }
    });
}


function loginUser() {
    const email = document.getElementById("loginEmail").value;
    const password = document.getElementById("loginPassword").value;

    const messageElem = document.getElementById("loginMessage");
    messageElem.classList.remove("text-green-600");
    messageElem.classList.add("text-red-500");
    messageElem.classList.remove("hidden");
	
	// === reCAPTCHA: citește token-ul din widget-ul de Login ===
	let recaptchaToken = "";
	if (window.RECAPTCHA_BYPASS === true || window.RECAPTCHA_BYPASS === 'true') {
		recaptchaToken = "bypass";
	} else {
		recaptchaToken = (typeof grecaptcha !== "undefined" && loginWidgetId !== null)
			? grecaptcha.getResponse(loginWidgetId)
			: "";
		if (!recaptchaToken) {
			messageElem.textContent = "Please complete reCAPTCHA.";
			return;
		}
	}

    fetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, recaptchaToken: recaptchaToken }),
    })
    .then((res) => res.json())
    .then((data) => {
        if (!data.success) {
            if (data.code === "INVALID_CREDENTIALS") {
                messageElem.textContent = "Invalid email or password.";
            } else if (data.code === "EMAIL_UNCONFIRMED_RESENT") {
                messageElem.innerHTML = "Email not confirmed.<br>A new confirmation email has been sent.";
            } else {
                messageElem.textContent = "Login failed. Try again.";
            }
			// doar pe eșec, re-afișăm caseta
			if (typeof grecaptcha !== "undefined" && loginWidgetId !== null) {
			  grecaptcha.reset(loginWidgetId);
			}
            return;
        }

        // Success
        messageElem.classList.add("text-green-600");
        messageElem.classList.remove("text-red-500");
        messageElem.textContent = "Login successful!";

        setTimeout(() => {
            closeModal("loginModal");

            setTimeout(() => {
                enableToggleButton();  // Fix: manually enable it now
                window.history.replaceState({}, document.title, window.location.pathname);
                checkLoginStatus();    // Optional if you want to refresh logout button etc.
            }, 200);

        }, 1000);
    })
    .catch((error) => {
        console.error('Login error:', error);
        messageElem.textContent = "An error occurred. Please try again.";
		
		if (typeof grecaptcha !== "undefined" && loginWidgetId !== null) {
            grecaptcha.reset(loginWidgetId);
		}
    });
}


function accessAsGuest() {
    const messageElem = document.getElementById("loginMessage");

    messageElem.classList.remove("text-green-600");
    messageElem.classList.add("text-red-500");
    messageElem.classList.remove("hidden");

    let recaptchaToken = "";
    if (window.RECAPTCHA_BYPASS === true || window.RECAPTCHA_BYPASS === 'true') {
        recaptchaToken = "bypass";
    } else {
        recaptchaToken = (typeof grecaptcha !== "undefined" && loginWidgetId !== null)
            ? grecaptcha.getResponse(loginWidgetId)
            : "";

        if (!recaptchaToken) {
            messageElem.textContent = "Please complete reCAPTCHA.";
            return;
        }
    }

    fetch("/guest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ recaptchaToken: recaptchaToken }),
    })
    .then((res) => res.json())
    .then((data) => {
        if (!data.success) {
            messageElem.textContent = data.message || "Guest access failed. Please try again.";

            if (typeof grecaptcha !== "undefined" && loginWidgetId !== null) {
                grecaptcha.reset(loginWidgetId);
            }
            return;
        }

        messageElem.classList.add("text-green-600");
        messageElem.classList.remove("text-red-500");
        messageElem.textContent = "Guest access granted!";

        setTimeout(() => {
            closeModal("loginModal");

            if (typeof grecaptcha !== "undefined" && loginWidgetId !== null) {
                grecaptcha.reset(loginWidgetId);
            }

            setTimeout(() => {
                enableToggleButton();
                checkLoginStatus();
            }, 200);

        }, 700);
    })
    .catch((error) => {
        console.error("Guest access error:", error);
        messageElem.textContent = "An error occurred. Please try again.";

        if (typeof grecaptcha !== "undefined" && loginWidgetId !== null) {
            grecaptcha.reset(loginWidgetId);
        }
    });
}


function logoutUser() {
    fetch("/logout", {
        method: "POST"
    }).then(() => {
        checkLoginStatus();
		window.location.reload();  // Optional: force full reload if needed
    });
}


function recoverPassword() {
    const email = document.getElementById("recoverEmail").value;
    const message = document.getElementById("forgotPasswordMessage");

    message.classList.remove("hidden");
    message.classList.remove("text-green-600", "text-red-500");
	
	let recaptchaToken = "";
    if (window.RECAPTCHA_BYPASS === true || window.RECAPTCHA_BYPASS === 'true') {
        recaptchaToken = "bypass";
    } else {
        recaptchaToken = (typeof grecaptcha !== "undefined" && forgotWidgetId !== null)
            ? grecaptcha.getResponse(forgotWidgetId)
            : "";

        if (!recaptchaToken) {
            message.classList.add("text-red-500");
            message.textContent = "Please complete reCAPTCHA.";
            return;
        }
    }

    fetch("/forgot_password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, recaptchaToken }),
    })
    .then(res => res.json())
    .then(data => {
        message.classList.add(data.success ? "text-green-600" : "text-red-500");
        message.textContent = data.message || "Something went wrong.";

        if (data.success) {
            setTimeout(() => {
                closeModal("forgotPasswordModal");
                message.classList.add("hidden");
                message.textContent = "";

                if (typeof grecaptcha !== "undefined" && forgotWidgetId !== null) {
                    grecaptcha.reset(forgotWidgetId);
                }
            }, 3000);
        } else {
            if (typeof grecaptcha !== "undefined" && forgotWidgetId !== null) {
                grecaptcha.reset(forgotWidgetId);
            }
        }
    })
    .catch(() => {
        message.classList.add("text-red-500");
        message.textContent = "An error occurred. Please try again.";

        if (typeof grecaptcha !== "undefined" && forgotWidgetId !== null) {
            grecaptcha.reset(forgotWidgetId);
        }
    });
}


function submitNewPassword() {
    const password = document.getElementById("newPassword").value;
    const confirmPassword = document.getElementById("confirmNewPassword").value;
    const message = document.getElementById("resetPasswordMessage");

    message.classList.remove("hidden");
    message.classList.remove("text-green-600", "text-red-500");

    if (password !== confirmPassword) {
        message.classList.add("text-red-500");
        message.textContent = "Passwords do not match.";
        return;
    }

    fetch("/reset_password", {  // Use fixed route
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            message.classList.add("text-green-600");
            message.textContent = "Password updated successfully!";
            setTimeout(() => {
                closeModal("resetPasswordModal");
                message.classList.add("hidden");
                message.textContent = "";
            }, 2000);
        } else {
            message.classList.add("text-red-500");
            message.textContent = data.message || "Failed to reset password.";
        }
    });
}

//  Cod Nou pentru Hystory  //
function toggleUserDropdown(event) {
    if (event) {
        event.stopPropagation();
    }

    const dropdown = document.getElementById("userDropdown");
    if (!dropdown) return;

    dropdown.classList.toggle("hidden");
}


document.addEventListener("click", function (event) {
    const dropdown = document.getElementById("userDropdown");
    const userInfo = document.getElementById("userInfo");

    if (!dropdown || !userInfo) return;

    if (!userInfo.contains(event.target)) {
        dropdown.classList.add("hidden");
    }
});


function openPredictionHistory() {
    const dropdown = document.getElementById("userDropdown");
    if (dropdown) {
        dropdown.classList.add("hidden");
    }

    openModal("historyModal");
    loadPredictionHistory();
}


function loadPredictionHistory() {
  const container = document.getElementById("historyContent");
  if (!container) return;

  container.textContent = "Loading...";

  fetch("/history_data")
    .then((res) => {
      if (!res.ok) {
        throw new Error("Could not load prediction history.");
      }

      return res.json();
    })
    .then((data) => {
      container.innerHTML = "";

      if (!data.success || !Array.isArray(data.items) || data.items.length === 0) {
        const message = document.createElement("p");
        message.className = "text-gray-600";
        message.textContent = "No prediction history available.";
        container.appendChild(message);
        return;
      }

      const table = document.createElement("table");
	  table.className = "border-collapse text-sm";

	  const isMobile = document.documentElement.classList.contains("mobile-mode");

	  if (isMobile) {
		table.style.width = "max-content";
		table.style.minWidth = "100%";
		table.style.whiteSpace = "nowrap";
		container.style.overflowX = "auto";
	  } else {
		table.style.width = "100%";
		table.style.tableLayout = "auto";
		table.style.whiteSpace = "nowrap";
		container.style.overflowX = "hidden";
	  }

      const thead = document.createElement("thead");
      thead.style.position = "sticky";
      thead.style.top = "0";
      thead.style.zIndex = "1";

      const headerRow = document.createElement("tr");
      headerRow.className = "bg-gray-100";

      const headers = [
        "Date",
        "Polymer",
        "Monomer Number",
        "Property",
        "Predicted Value"
      ];

      headers.forEach((headerText) => {
        const th = document.createElement("th");
        th.className = "border px-3 py-2 text-left";
        th.textContent = headerText;
        headerRow.appendChild(th);
      });

      thead.appendChild(headerRow);

      const tbody = document.createElement("tbody");

      data.items.forEach((item) => {
        const row = document.createElement("tr");

        const date = item.created_at
          ? new Date(item.created_at).toLocaleString()
          : "";

        const numericValue = Number(item.predicted_value);
        const predictedUnit = item.property_name === "SASA" ? "Å²" : item.property_name === "Rg" ? "Å" : "";
        const predictedValue = Number.isFinite(numericValue)
          ? `${numericValue.toFixed(3)}${predictedUnit ? ` ${predictedUnit}` : ""}`
          : "";

        const values = [
          date,
          item.polymer_name ?? "",
          item.monomer_number ?? "",
          item.property_name ?? "",
          predictedValue
        ];

        values.forEach((value) => {
          const td = document.createElement("td");
          td.className = "border px-3 py-2";
          td.textContent = String(value);
          row.appendChild(td);
        });

        tbody.appendChild(row);
      });

      table.appendChild(thead);
      table.appendChild(tbody);
      container.appendChild(table);
    })
    .catch((error) => {
      console.error("History error:", error);

      container.innerHTML = "";

      const message = document.createElement("p");
      message.className = "text-red-500";
      message.textContent = "Could not load prediction history.";
      container.appendChild(message);
    });
}


function deletePredictionHistory() {
    const confirmed = confirm("Are you sure you want to delete your entire prediction history? This action cannot be undone.");

    if (!confirmed) {
        return;
    }

    fetch("/delete_history", {
        method: "POST",
        headers: { "Content-Type": "application/json" }
    })
    .then((res) => res.json())
    .then((data) => {
        if (!data.success) {
            alert(data.message || "Could not delete prediction history.");
            return;
        }

        const container = document.getElementById("historyContent");
        if (container) {
            container.innerHTML = "<p class='text-gray-600'>No prediction history available.</p>";
        }
    })
    .catch((error) => {
        console.error("Delete history error:", error);
        alert("An error occurred while deleting prediction history.");
    });
}
//  ......................  //


function checkLoginStatus() {
  fetch("/status")
    .then((res) => res.json())
    .then((data) => {
      const loginBtn = document.getElementById("loginButton");
      const signUpBtn = document.getElementById("signUpButton");
      const authContainer = document.getElementById("authButtonsContainer");
      const authArea = document.getElementById("authArea");
      const content = document.querySelector(".flex-grow");

      const polymerButton   = document.getElementById("btn-polymer");
      const gradiusButton   = document.getElementById("btn-gradius");
      const sasaButton      = document.getElementById("btn-sasa");
      const diffusionButton = document.getElementById("btn-diffusion");

      // device-based: mobil real, nu doar fereastră îngustă
      const isMobile = document.documentElement.classList.contains("mobile-mode");

      // Curățare: scoate ce era de la un status anterior
      document.getElementById("logoutButton")?.remove();
      document.getElementById("userInfo")?.remove();
	  document.getElementById("userDropdownWrapper")?.remove();

      if (data.loggedIn || data.guest) {
        // 🔒 ascunde Login/Sign up
        authContainer.classList.add("hidden");
        loginBtn?.classList.add("hidden");
        signUpBtn?.classList.add("hidden");

        // 👤 adaugă nume utilizator
	  if (data.loggedIn) {
		const wrapper = document.createElement("div");
		wrapper.id = "userDropdownWrapper";
		wrapper.className = "relative mr-2";
		wrapper.style.zIndex = "10000";

		const userInfo = document.createElement("button");
		userInfo.id = "userInfo";
		userInfo.type = "button";
		userInfo.className = "text-white text-sm flex items-center cursor-pointer";

		userInfo.appendChild(
		  document.createTextNode(`👤 ${data.name} `)
		);

		const arrowSpan = document.createElement("span");
		arrowSpan.className = "ml-1 text-xs";
		arrowSpan.textContent = "▼";

		userInfo.appendChild(arrowSpan);
		userInfo.onclick = toggleUserDropdown;

		const dropdown = document.createElement("div");
		dropdown.id = "userDropdown";
		dropdown.className = "hidden absolute right-0 mt-2 w-44 rounded shadow-lg text-sm";
		dropdown.style.zIndex = "10001";
		dropdown.style.backgroundColor = "#1f2937";
		dropdown.style.color = "#e5e7eb";
		dropdown.style.overflow = "hidden";
		dropdown.style.border = "1px solid rgba(255,255,255,0.08)";

		const historyItem = document.createElement("button");
		historyItem.type = "button";
		historyItem.className = "block w-full text-left px-4 py-2";
		historyItem.style.color = "#e5e7eb";
		historyItem.style.backgroundColor = "transparent";
		historyItem.style.borderRadius = "0";
		historyItem.style.transition = "background-color 0.15s ease";
		historyItem.textContent = "Prediction History";

		historyItem.onmouseenter = () => {
		  historyItem.style.backgroundColor = "#374151";
		};

		historyItem.onmouseleave = () => {
		  historyItem.style.backgroundColor = "transparent";
		};

		historyItem.onclick = openPredictionHistory;

		dropdown.appendChild(historyItem);
		wrapper.appendChild(userInfo);
		wrapper.appendChild(dropdown);

		if (isMobile) {
			userInfo.style.maxWidth = "40vw";
			userInfo.style.whiteSpace = "nowrap";
			userInfo.style.overflow = "hidden";
			userInfo.style.textOverflow = "ellipsis";
			userInfo.style.lineHeight = "1";
			userInfo.style.fontSize = "12px";
		}

		authArea.prepend(wrapper);

	  } else if (data.guest) {
		  const userInfo = document.createElement("div");
		  userInfo.id = "userInfo";
		  userInfo.className = "text-white text-sm flex items-center mr-2";
		  userInfo.textContent = "👤 Guest";

		  if (isMobile) {
			  userInfo.style.maxWidth = "40vw";
			  userInfo.style.whiteSpace = "nowrap";
			  userInfo.style.overflow = "hidden";
			  userInfo.style.textOverflow = "ellipsis";
			  userInfo.style.lineHeight = "1";
			  userInfo.style.fontSize = "12px";
		  }

		  authArea.prepend(userInfo);
	  }

        // 🔓 buton Logout
        const logoutBtn = document.createElement("button");
        logoutBtn.id = "logoutButton";
        logoutBtn.className = "button-style ml-2";
        logoutBtn.textContent = "Logout";
        logoutBtn.onclick = logoutUser;
        if (isMobile) {
          logoutBtn.style.padding = "4px 8px";
          logoutBtn.style.fontSize  = "12px";
          logoutBtn.style.borderRadius = "6px";
          logoutBtn.style.whiteSpace = "nowrap";
          logoutBtn.style.minWidth = "0";
        }
        authArea.appendChild(logoutBtn);

        // ✅ deblochează toate butoanele din sidebar
        document.querySelectorAll('#sidebar .menu-item').forEach(btn => {
          btn.disabled = false;
          btn.classList.remove('opacity-50','cursor-not-allowed');
          btn.style.pointerEvents = 'auto';
        });

        // ✅ deblochează toate input-urile din conținut
        const inputs = content.querySelectorAll("button, input, select, textarea");
		inputs.forEach(el => {
		  if (
			el.id === "polymer_type_gradius" || el.id === "polymer_type_sasa" ||
			el.id === "polymer_family_gradius" || el.id === "polymer_family_sasa"
		  ) {
			return;
		  }
		  el.disabled = false;
		  el.classList.remove("opacity-50", "cursor-not-allowed");
		});
		
        enableToggleButton();

      } else {
        // 🔓 arată Login/Sign up
        authContainer.classList.remove("hidden");
        loginBtn?.classList.remove("hidden");
        signUpBtn?.classList.remove("hidden");

        // ✅ menține restul meniului activ (About, Learn More etc.)
        document.querySelectorAll('#sidebar .menu-item').forEach(btn => {
          btn.disabled = false;
          btn.classList.remove('opacity-50','cursor-not-allowed');
          btn.style.pointerEvents = 'auto';
        });

        // 🔒 blochează doar zona de generator (Properties/Gradius/SASA/Diffusion)
        [polymerButton, gradiusButton, sasaButton, diffusionButton].forEach(btn => {
          if (!btn) return;
          btn.disabled = true;
          btn.classList.add('opacity-50','cursor-not-allowed');
          btn.style.pointerEvents = 'none';
        });

        // aici folosim direct isMobile-ul de sus, NU îl mai declarăm încă o dată
        if (isMobile) {
          enableToggleButton();
        } else {
          disableToggleButton();
        }
      }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    // URL parameters: login confirmed, reset password, etc.
    const params = new URLSearchParams(window.location.search);

    if (params.get("confirmed") === "true") {
        fetch("/status")
            .then((res) => res.json())
            .then((data) => {
                if (!data.loggedIn) {
                    openModal("loginModal");
                }
            });
    }

    const emailStatus = params.get("email_status");
	if (emailStatus) {
		pendingConfirmationToken = params.get("confirm_token");

		if (emailStatus === "reset_ready") {
			openModal("resetPasswordModal");
		} else {
			showEmailConfirmationModal(emailStatus);
		}

		window.history.replaceState({}, document.title, window.location.pathname);
	}
	
	checkLoginStatus();
});



// =======  The 4th code block ========  //
// reCAPTCHA explicit render //

// Widget IDs pentru a citi/reset token-urile
let loginWidgetId = null;
let signupWidgetId = null;
let forgotWidgetId = null;

function onloadRecaptcha() {
	// Login
    const loginEl = document.getElementById('recaptcha-login');
	if (loginEl && loginWidgetId === null) {
	  loginWidgetId = grecaptcha.render('recaptcha-login', { 'sitekey': window.RECAPTCHA_SITE_KEY });
	}
    // Sign Up
    const signupEl = document.getElementById('recaptcha-signup');
	if (signupEl && signupWidgetId === null) {
	  signupWidgetId = grecaptcha.render('recaptcha-signup', { 'sitekey': window.RECAPTCHA_SITE_KEY });
	}
	// Forgot Password
    const forgotEl = document.getElementById('recaptcha-forgot');
    if (forgotEl && forgotWidgetId === null) {
      forgotWidgetId = grecaptcha.render('recaptcha-forgot', { 'sitekey': window.RECAPTCHA_SITE_KEY });
    }
}