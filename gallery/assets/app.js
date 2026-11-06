/* Editing Recipes gallery.
   Each card draws its effect live from a still frame of the source footage,
   so every option changes the demo at once. Demo clips are optional:
   add a file to CLIPS and that frame plays as video on hover. */

const F = "assets/frames/";

// Free to try.
// The five free recipes.
const STARTER = new Set([]);
const FREE = new Set(["titlestack", "slideup", "midcaptions", "bigwords", "clipsonwhite"]);
const tierOf = (slug) => (FREE.has(slug) ? "Free" : STARTER.has(slug) ? "Starter" : "Pro");
const JOIN_URL = "#pricing"; // placeholder: the pricing section. No payment links yet.
const REPO_URL = "https://github.com/naomimetzger/cookbook";
const installPrompt = (slug) => `Install the /${slug} recipe from ${REPO_URL} (folder recipes/${slug}) into my Claude Code skills.`;

// The settings Naomi used in her own videos, tagged on each card so people can copy her look.
const PICKS = {
  titlestack: { under: "clip", behind: "cream paper", colour: "deep red", font: "pixel" },
  slideup: { captions: "middle captions" },
  midcaptions: { words: "1 or 2" },
  clipsonwhite: { count: "3", page: "cream" },
  bigwords: { font: "Bootzy", layout: "fill the frame", colour: "white" },
};

const LOCK_SVG = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>';
function lockIcon() { const s = document.createElement("span"); s.className = "lock-ico"; s.innerHTML = LOCK_SVG; return s; }

// Plain source clips (no effect baked in), about 3 seconds each.
// Leave empty until the clips are rendered; the page then uses the stills.
const CLIPS = {
  bigwordsbootzy: "../recipes/bigwords/demo/reference.mp4",
  clipsoncream: "../recipes/clipsonwhite/demo/reference.mp4",
  midcaptions: "../recipes/midcaptions/demo/reference.mp4",
  titlestack_card: "../recipes/titlestack/demo/reference.mp4",
  slideupplain: "../recipes/slideup/demo/reference.mp4",
  slideupmid: "../recipes/slideup/demo/reference_midcaptions.mp4",
  slideuprise: "../recipes/slideup/demo/reference_bigrise.mp4",
};

// Where each hover demo starts: half a second before its effect begins, so nobody waits
// through the lead-in. It loops back to this point, not to the very start. (Seconds into the clip.)
const CLIP_START = {
  slideupplain: 1.0,
  slideupmid: 1.0,
  slideuprise: 1.0,
};

// Where a hover demo stops and loops back (seconds into the clip). Naomi: "stop type intro at places".
const CLIP_END = { bigwordsbootzy: 4.5 };

const SRC = {
  bigwordsbootzy: F + "bigwords_wide_bootzy_poster_v1.jpg",
  clipsoncream: F + "clipsoncream_poster_v1.jpg",
  a: F + "frame_a_v2.jpg",
  titlestack_card: F + "titlestack_vertical_poster_v1.jpg",
  slideupplain: F + "slideup_plain_poster_v1.jpg",
  midcaptions: F + "midcaptions_poster_v1.jpg",
  slideupmid: F + "slideup_mid_poster_v1.jpg",
  slideuprise: F + "slideup_rise_poster_v1.jpg",
};

const BG = [
  { id: "black", hex: "#000000", say: "black" },
  { id: "cream", hex: "#F4EFE6", say: "#F4EFE6" },
  { id: "navy", hex: "#1F2A44", say: "#1F2A44" },
  { id: "white", hex: "#FFFFFF", say: "white" },
];

const EDGES = { crisp: 0, soft: 0.01, "very soft": 0.02 };
const SHADOW = { none: 0, gentle: 0.35, strong: 0.6 };

/* ---------- recipes ---------- */

const RECIPES = [
  {
    slug: "bigwords",
    category: "Text",
    title: "Big words",
    moreLabel: "Case",
    moreNote: "The preview shows Naomi's look: Bootzy, white, up to 3 huge words filling the frame. Your choices go into the prompt.",
    fonts: { Bootzy: "Bootzy (my own copy of the font file: [FONT FILE NAME])", "helvetica condensed": "helvetica", impact: "impact", "my font file": "my font file: [FONT FILE NAME]" },
    colours: [
      { id: "white", hex: "#FFFFFF", say: "white" },
      { id: "black", hex: "#000000", say: "black" },
      { id: "cream", hex: "#F4EFE6", say: "#F4EFE6" },
      { id: "yellow", hex: "#F2C94C", say: "#F2C94C" },
    ],
    state: { font: "Bootzy", colour: "white", layout: "fill the frame", case: "capitals" },
    aspect() { return 16 / 9; },
    rows() {
      return {
        main: [
          { key: "font", label: "Font", choices: Object.keys(this.fonts) },
          { key: "layout", label: "Layout", choices: ["fill the frame", "one word at the top"] },
          { key: "colour", label: "Colour", choices: this.colours.map((c) => c.id) },
        ],
        more: [{ key: "case", label: "Case", choices: [["capitals", "CAPITALS"], ["as said", "As typed"]] }],
      };
    },
    build(s, W, H) {
      return { bg: "#000", intro: "none", full: "a",
        items: [{ key: "bigwordsbootzy", x: 0, y: 0, w: W, h: H, r: 0, soft: 0, sh: 0 }] };
    },
    prompt(s) {
      const col = this.colours.find((c) => c.id === s.colour).say;
      const layout = s.layout === "one word at the top"
        ? "one word at a time along the top, every word the same size, keeping my face clear (--max-words 1 --same-size --top 0.07)"
        : "no more than 3 on screen, filling the frame with equal spacing";
      return `/bigwords

Add giant words to my video [FILE NAME], each appearing exactly when I say it: ${layout}.
Font: ${this.fonts[s.font]}
Colour: ${col}
Case: ${s.case === "capitals" ? "all capitals" : "as typed"}
Show me a still and the word list first. Don't render anything until I say yes.`;
    },
  },
  {
    slug: "clipsonwhite",
    category: "Layouts",
    title: "Clips on cream",
    moreNote: "The preview shows three phone clips on a cream page. Every gap and margin is exactly the same. Your choices go into the prompt.",
    state: { count: "3", timing: "normal", page: "cream" },
    aspect() { return 16 / 9; },
    rows() { return { main: [
          { key: "count", label: "Clips", choices: ["1", "2", "3", "4"] },
          { key: "timing", label: "Timing", choices: ["quick", "normal", "slow"] },
          { key: "page", label: "Page", choices: ["cream", "white", "paper"] },
        ], more: [] }; },
    build(s, W, H) {
      return { bg: "#000", intro: "none", full: "a",
        items: [{ key: "clipsoncream", x: 0, y: 0, w: W, h: H, r: 0, soft: 0, sh: 0 }] };
    },
    prompt(s) {
      const page = s.page === "cream" ? "a cream page (#F6F0E3)" : s.page === "white" ? "a white page" : "an off-white paper page";
      return `/clipsonwhite

Put these phone clips in a row on ${page}, appearing one at a time: ${Array.from({ length: Number(s.count) }, (_, i) => `[CLIP ${i + 1}]`).join(", ")}.
Make every gap and every margin exactly equal (--equal). Timing: ${s.timing}.
Show me a still first. Don't render anything until I say yes.`;
    },
  },
  {
    slug: "titlestack",
    category: "Text",
    tall: true,
    title: "Title stack",
    moreLabel: "Background, colour and font",
    moreNote: "The preview shows deep red pixel lettering with a clip underneath. Your words and choices go into the prompt.",
    colours: ["deep red", "blue", "black"],
    state: { w1: "the", w2: "AI EDITING", w3: "method", under: "clip", behind: "cream paper", colour: "deep red", font: "pixel" },
    aspect() { return 9 / 16; },
    rows() {
      return {
        main: [
          { key: "w1", label: "Small word (top)", type: "text" },
          { key: "w2", label: "Big word", type: "text" },
          { key: "w3", label: "Small word (bottom)", type: "text" },
          { key: "under", label: "Underneath", choices: [["nothing", "Nothing"], ["clip", "My clip or photo"]] },
        ],
        more: [
          { key: "behind", label: "Behind it", choices: ["cream paper", "a colour", "my clip"] },
          { key: "colour", label: "Big word colour", choices: this.colours },
          { key: "font", label: "Font", choices: ["pixel", "hand-drawn", "bold"] },
        ],
      };
    },
    build(s, W, H) {
      return { bg: "#000", intro: "none", full: "a",
        items: [{ key: "titlestack_card", x: 0, y: 0, w: W, h: H, r: 0, soft: 0, sh: 0 }] };
    },
    prompt(s) {
      const behind = s.behind === "a colour" ? "colour: [COLOUR]" : s.behind === "my clip" ? "my clip: [FILE NAME]" : "cream paper";
      const under = s.under === "clip" ? "my clip or photo in a rounded card (a tall 9:16 card if it is a vertical clip): [FILE NAME]" : "nothing";
      return `/titlestack

Make an intro title: "${s.w1}" / "${s.w2}" / "${s.w3}", appearing one line at a time.
Behind it: ${behind}. Big word colour: ${s.colour}. Font: ${s.font}
Underneath: ${under}
Show me a still first. Don't render anything until I say yes.`;
    },
  },
  {
    slug: "slideup",
    slash: "/slideup",
    category: "Vertical",
    title: "Slide up",
    moreNote: "The preview shows the phone version. Your words and choices go into the prompt.",
    state: { word: "teach", captions: "none" },
    aspect() { return 9 / 16; },
    rows() {
      return {
        main: [
          { key: "word", label: "Slide up when I say", type: "text" },
          { key: "captions", label: "Captions", choices: ["none", "middle captions", "big rise words"] },
        ],
        more: [],
      };
    },
    build(s, W, H) {
      const key = s.captions === "middle captions" ? "slideupmid" : s.captions === "big rise words" ? "slideuprise" : "slideupplain";
      return { bg: "#000", intro: "none", full: "a",
        items: [{ key, x: 0, y: 0, w: W, h: H, r: 0, soft: 0, sh: 0 }] };
    },
    prompt(s) {
      const base = `On [VIDEO FILE NAME], when I say "${s.word}", slide me up into the top half and slide up [IMAGE FILE NAMES] to fill the bottom, cutting to the next photos as I talk. Shape: phone 9:16.`;
      if (s.captions === "middle captions") return `/slideup then /midcaptions

${base}
Then add small bold captions just under the join, up to 4 words at a time, in the Satoshi font (free from fontshare.com).
Show me a still first. Don't render anything until I say yes.`;
      if (s.captions === "big rise words") return `/slideup then /risecaptions

${base}
Then add big lowercase words in the Satoshi font (free from fontshare.com), rising in one at a time as I say them, max 3 on screen.
Show me a still first. Don't render anything until I say yes.`;
      return `/slideup

${base}
Show me a still first. Don't render anything until I say yes.`;
    },
  },
  {
    slug: "midcaptions",
    slash: "/midcaptions",
    category: "Text",
    tall: true,
    title: "Middle captions",
    moreNote: "The preview shows the phone version. Your choices go into the prompt.",
    state: { words: "1 or 2" },
    aspect() { return 9 / 16; },
    rows() {
      return {
        main: [
          { key: "words", label: "Words at a time", choices: ["1 or 2", "up to 4"] },
          { type: "link", text: "Uses the free Satoshi font. Get it from", href: "https://www.fontshare.com/fonts/satoshi", linkText: "Fontshare" },
        ],
        more: [],
      };
    },
    build(s, W, H) {
      return { bg: "#000", intro: "none", full: "a",
        items: [{ key: "midcaptions", x: 0, y: 0, w: W, h: H, r: 0, soft: 0, sh: 0 }] };
    },
    prompt(s) {
      return `/midcaptions

Add small bold white capitals to my video [VIDEO FILE NAME], ${s.words} words at a time, in the middle at chest height with a soft shadow, timed to my voice, in the Satoshi font.
Show me a still first. Don't render anything until I say yes.`;
    },
  },
];

function lookRows(corners) {
  return [
    { key: "corners", label: "Corners", choices: Object.keys(corners) },
    { key: "edges", label: "Edges", choices: Object.keys(EDGES) },
    { key: "shadow", label: "Shadow", choices: Object.keys(SHADOW) },
  ];
}
function lookLine(s) {
  return `Corners: ${s.corners}. Edges: ${s.edges}. Shadow: ${s.shadow}`;
}
function bgWords(s) {
  return s.bgImage ? `image: ${s.bgImage.name}` : s.bg.say;
}
function ratio(str) {
  const [a, b] = str.split(":").map(Number);
  return a / b;
}

/* ---------- helpers ---------- */

const touch = window.matchMedia("(hover: none)").matches;
let current = null; // the card that is playing

function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) if (kid != null) el.append(kid);
  return el;
}

function softMask(w, h, r, s) {
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 ${w.toFixed(1)} ${h.toFixed(1)}' preserveAspectRatio='none'>` +
    `<filter id='f' x='-10%' y='-10%' width='120%' height='120%'><feGaussianBlur stdDeviation='${(s / 2).toFixed(2)}'/></filter>` +
    `<rect x='${s.toFixed(2)}' y='${s.toFixed(2)}' width='${(w - 2 * s).toFixed(1)}' height='${(h - 2 * s).toFixed(1)}' rx='${Math.max(r - s / 2, 0).toFixed(1)}' fill='white' filter='url(#f)'/></svg>`;
  return `url("data:image/svg+xml,${encodeURIComponent(svg)}")`;
}

function mediaFor(key) {
  const box = h("div", { class: "media" }, h("img", { src: SRC[key] || key, alt: "", draggable: "false" }));
  if (CLIPS[key]) {
    const v = h("video", { muted: true, playsinline: true, preload: "none", "data-src": CLIPS[key], "data-start": CLIP_START[key] || 0, "data-end": CLIP_END[key] || "",
      controlslist: "nodownload noplaybackrate noremoteplayback", disablepictureinpicture: true, disableremoteplayback: true, draggable: "false" });
    v.muted = true; // the attribute alone doesn't mute a video made in script
    v.addEventListener("ended", () => { v.currentTime = Number(v.dataset.start) || 0; v.play().catch(() => {}); });
    if (v.dataset.end) {
      const end = Number(v.dataset.end);
      const watch = () => {
        if (!v.paused && v.currentTime >= end) v.currentTime = Number(v.dataset.start) || 0;
        if (!v.paused) requestAnimationFrame(watch);
      };
      v.addEventListener("playing", () => requestAnimationFrame(watch));
    }
    box.append(v);
  }
  return box;
}

/* ---------- card ---------- */

class Card {
  constructor(recipe) {
    this.r = recipe;
    this.s = { ...recipe.state };
    this.timers = [];
    this.playing = false;

    this.stage = h("div", { class: "stage" });
    this.bgimg = h("img", { class: "bgimg", alt: "" });
    this.base = h("div", { class: "full base" });
    this.full = h("div", { class: "full intro-layer" });
    this.layer = h("div", { class: "layer" });
    this.stage.append(this.bgimg, this.base, this.layer, this.full);

    this.view = h("div", {
      class: "view", tabindex: "0", role: "button",
      "aria-label": `Play the ${recipe.title} demo`,
    }, h("span", { class: "cat" }, recipe.category),
      FREE.has(recipe.slug) ? h("span", { class: "badge free" }, "Free") : h("span", { class: `badge members tier-${tierOf(recipe.slug).toLowerCase()}` }, lockIcon(), tierOf(recipe.slug)),
      this.stage, h("span", { class: "hint" }, h("span", { class: "t-hover" }, "Hover to play · Click to customise"), h("span", { class: "t-touch" }, "Tap to play and customise")));

    this.view.addEventListener("pointerenter", (e) => { if (e.pointerType === "mouse") this.play(); });
    this.view.addEventListener("pointerleave", (e) => { if (e.pointerType === "mouse") this.stop(); });
    this.view.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); this.isOpen ? this.toggle() : this.open(); }
    });

    this.opts = h("div", { class: "opts" });
    this.moreOpts = h("div", { class: "opts" });
    this.pre = h("pre");
    this.copyBtn = h("button", { class: "textlink copy-link", type: "button", onclick: () => this.copy() }, "Copy prompt");
    this.installBtn = h("button", { class: "copy", type: "button", onclick: () => this.install() }, "Install");

    this.el = h("article", { class: recipe.category === "Vertical" || recipe.tall ? "card tall" : "card", id: recipe.slug, "data-cat": recipe.category },
      this.view,
      h("div", { class: "body" },
        h("div", { class: "head" },
          h("h2", { class: "name" }, recipe.title),
          h("span", { class: "slash" }, recipe.slash || "/" + recipe.slug),
          h("button", { type: "button", class: "textlink close", onclick: (e) => { e.stopPropagation(); this.close(); } }, "Close")),
        h("div", { class: "panel" },
          this.opts,
          h("details", { class: "more" }, h("summary", {}, recipe.moreLabel || "Corners, edges, shadow"),
            recipe.moreNote ? h("p", { class: "note" }, recipe.moreNote) : null, this.moreOpts),
          FREE.has(recipe.slug)
            ? h("div", { class: "actions" },
                this.installBtn,
                this.copyBtn,
                h("details", { class: "peek" }, h("summary", {}, "See the prompt"), this.pre),
                h("p", { class: "note install-note" }, "Install copies one line. Paste it into Claude Code and it sets the recipe up for you. Then copy the prompt, or just type /" + (recipe.installSlug || recipe.slug) + " and answer a few questions."))
            : h("div", { class: "actions locked" },
                h("p", { class: "lock-note" }, lockIcon(), tierOf(recipe.slug) === "Starter" ? "Unlocks with Starter or Pro." : "Unlocks with Pro."),
                h("a", { class: "copy", href: JOIN_URL }, "See pricing"))),
      ));

    // options stay hidden until the card is clicked
    this.isOpen = false;
    this.el.addEventListener("click", (e) => {
      if (e.target.closest(".panel, .close")) return;
      const onView = e.target.closest(".view");
      const tap = e.pointerType && e.pointerType !== "mouse";
      if (!this.isOpen) { this.open(); if (onView && tap) this.play(); return; }
      if (onView && tap) this.toggle();
    });

    new ResizeObserver(() => this.layout()).observe(this.view);
    this.renderOptions();
  }

  frameSize() {
    const vw = this.view.clientWidth, vh = this.view.clientHeight;
    const ar = this.r.aspect ? this.r.aspect(this.s) : ratio(this.s.frame);
    let W = Math.min(vw * 0.86, vh * 0.74 * ar);
    return [W, W / ar];
  }

  layout(animate = false) {
    const [W, H] = this.frameSize();
    if (!W) return;
    this.stage.style.width = W + "px";
    this.stage.style.height = H + "px";
    const out = this.r.build(this.s, W, H);
    this.out = out;
    this.stage.style.background = out.bg;

    if (out.bgImage) { this.bgimg.src = out.bgImage.url; this.bgimg.style.display = "block"; }
    else this.bgimg.style.display = "none";

    this.base.replaceChildren(...(out.base ? [mediaFor(out.base)] : []));
    this.base.style.display = out.base ? "block" : "none";
    const fullKey = out.full || (out.items[0] && out.items[0].key);
    if (this.full.dataset.key !== fullKey) {
      this.full.replaceChildren(mediaFor(fullKey));
      this.full.dataset.key = fullKey;
    }

    // reuse elements when the count is the same, so transitions stay smooth
    const keySig = out.items.map((i) => i.key).join(",");
    if (this.layer.dataset.sig !== keySig) {
      this.layer.replaceChildren(...out.items.map((it) => h("div", { class: "el" }, mediaFor(it.key))));
      this.layer.dataset.sig = keySig;
    }
    const fullRect = { x: 0, y: 0, w: W, h: H };
    out.items.forEach((it, i) => this.place(this.layer.children[i], it, animate, out.from === "full" ? fullRect : null));
    this.stage.style.setProperty("--flick", out.flicker || 0);
    if (this.playing) this.startVideos();
  }

  // animate: false, true (0.7s smooth) or { ms, ease }
  place(el, it, animate, fullRect) {
    const m = el.firstChild;
    const ms = animate ? animate.ms || 700 : 0;
    const ease = (animate && animate.ease) || "cubic-bezier(.2,.7,.2,1)";
    el.style.transition = animate
      ? ["left", "top", "width", "height"].map((p) => `${p} ${ms}ms ${ease}`).join(", ")
      : "none";
    m.style.transition = animate ? `border-radius ${ms}ms ${ease}` : "none";
    const R = fullRect || it;
    Object.assign(el.style, { left: R.x + "px", top: R.y + "px", width: R.w + "px", height: R.h + "px" });
    if (fullRect) {
      m.style.borderRadius = "0px";
      m.style.webkitMaskImage = m.style.maskImage = "none";
      el.style.filter = "none";
      return;
    }
    const rad = it.r * it.w, soft = it.soft * it.w;
    const z = it.zoom || 1;
    m.querySelectorAll("img, video").forEach((e) => {
      e.style.transform = z !== 1 ? `scale(${z})` : "";
      e.style.transformOrigin = z !== 1 ? it.origin || "50% 50%" : "";
    });
    const c = it.corners || "all";
    m.style.borderRadius = c === "all" ? rad + "px" : c === "top" ? `${rad}px ${rad}px 0 0` : c === "bottom" ? `0 0 ${rad}px ${rad}px` : "0";
    const applyLook = () => {
      const mask = soft > 0 ? softMask(it.w, it.h, rad, soft) : "none";
      m.style.webkitMaskImage = m.style.maskImage = mask;
      el.style.filter = it.sh > 0
        ? `drop-shadow(0 ${(it.w * 0.015).toFixed(1)}px ${(it.w * 0.04).toFixed(1)}px rgba(0,0,0,${it.sh}))`
        : "none";
    };
    if (animate) this.later(applyLook, ms); else applyLook();
  }

  later(fn, ms) { this.timers.push(setTimeout(fn, ms)); }

  play() {
    if (!this.out) this.layout();
    if (!this.out) return; // card not drawn yet (no width), nothing to play
    if (current && current !== this) current.stop();
    current = this;
    this.playing = true;
    this.view.classList.add("playing");
    this.view.setAttribute("aria-label", `Stop the ${this.r.title} demo`);
    this.startVideos();

    const out = this.out;
    const [W, H] = this.frameSize();
    if (out.intro === "grow") {
      // starts as the plain clip, then a straight cut to the rounded card (no motion; that is /smoothzoom)
      const el = this.layer.children[0];
      this.place(el, out.items[0], false, { x: 0, y: 0, w: W, h: H });
      this.later(() => this.place(el, out.items[0], false), 600);
    } else if (out.intro === "zoom") {
      // smooth zoom: one eased move between full frame and the card
      const el = this.layer.children[0];
      const full = { x: 0, y: 0, w: W, h: H };
      const anim = { ms: out.ms, ease: out.ease };
      this.later(() => out.from === "full"
        ? this.place(el, out.items[0], anim)
        : this.place(el, out.items[0], anim, full), 450);
    } else if (out.intro === "push") {
      // the whole page pushes in slowly
      this.layer.style.setProperty("--push", out.push || 1.04);
      this.view.classList.add("push");
    } else if (out.intro === "fade") {
      // plain picture, then the effect fades in (and flickers)
      this.view.classList.add("intro");
      void this.view.offsetWidth;
      this.view.classList.add("fade");
      this.later(() => this.view.classList.remove("intro"), 450);
      if (out.flicker) this.view.classList.add("flicker");
    } else if (out.intro === "cut") {
      // one plain clip, then a straight cut to the grid
      this.view.classList.add("intro");
      this.later(() => this.view.classList.remove("intro"), 650);
    } else if (out.intro === "overlay") {
      // main video alone, then the overlay cuts in
      this.layer.style.visibility = "hidden";
      this.later(() => { this.layer.style.visibility = ""; }, 700);
    }
  }

  stop() {
    this.timers.forEach(clearTimeout);
    this.timers = [];
    this.playing = false;
    if (current === this) current = null;
    this.view.classList.remove("playing", "intro", "fade", "flicker", "push");
    this.view.setAttribute("aria-label", `Play the ${this.r.title} demo`);
    this.layer.style.visibility = "";
    this.stage.querySelectorAll("video").forEach((v) => { v.pause(); v.closest(".el")?.classList.remove("has-video"); });
    this.layout();
  }

  toggle() { this.playing ? this.stop() : this.play(); }

  open() {
    cards.forEach((c) => { if (c !== this && c.isOpen) c.close(); });
    this.isOpen = true;
    this.el.classList.add("open");
    requestAnimationFrame(() => {
      this.layout();
      this.el.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  }

  close() {
    this.isOpen = false;
    this.el.classList.remove("open");
    requestAnimationFrame(() => this.layout());
  }

  startVideos() {
    this.stage.querySelectorAll("video").forEach((v) => {
      if (!v.src) v.src = v.dataset.src;
      const st = Number(v.dataset.start) || 0;
      if (v.readyState >= 1) v.currentTime = st;
      else v.addEventListener("loadedmetadata", () => { v.currentTime = st; }, { once: true });
      v.play().then(() => v.closest(".el")?.classList.add("has-video")).catch(() => {});
    });
  }

  set(key, value) {
    this.s[key] = value;
    if (this.r.onChange) this.r.onChange(this.s, key);
    this.renderOptions();
    if (this.playing) this.stop();
  }

  renderOptions() {
    const { main, more } = this.r.rows(this.s);
    this.opts.replaceChildren(...main.map((row) => this.row(row)));
    this.moreOpts.replaceChildren(...more.map((row) => this.row(row)));
    const moreBox = this.moreOpts.closest("details");
    if (moreBox) moreBox.hidden = more.length === 0;
    if (more.length === 0 && this.r.moreNote) this.opts.append(h("p", { class: "note" }, this.r.moreNote));
    this.layout();
    this.pre.textContent = this.r.prompt(this.s);
  }

  row(row) {
    const id = `${this.r.slug}-${row.key}`;
    let control;
    if (row.type === "link") {
      return h("p", { class: "note linknote" }, row.text + " ",
        h("a", { href: row.href, target: "_blank", rel: "noopener" }, row.linkText));
    }
    if (row.type === "bg") control = this.bgControl(id);
    else if (row.type === "text") {
      control = h("input", {
        type: "text", class: "field", value: this.s[row.key], "aria-labelledby": id, spellcheck: "false",
        oninput: (e) => { this.s[row.key] = e.target.value; this.pre.textContent = this.r.prompt(this.s); },
      });
    }
    else {
      control = h("div", { class: "seg", role: "group", "aria-labelledby": id },
        row.choices.map((c) => {
          const [val, label] = Array.isArray(c) ? c : [c, c];
          const pick = (PICKS[this.r.slug] || {})[row.key] === val;
          return h("button", {
            type: "button", "aria-pressed": String(this.s[row.key] === val), title: pick ? "Naomi's pick: the setting she used in her own video" : null,
            onclick: () => this.set(row.key, val),
          }, label, pick ? h("span", { class: "pick" }, "Naomi's pick") : null);
        }));
    }
    return h("div", { class: "row" }, h("span", { class: "lab", id }, row.label), control);
  }

  bgControl(id) {
    const s = this.s;
    const swatches = BG.map((b) => h("button", {
      type: "button", class: "swatch", title: b.id, "aria-label": b.id,
      style: `background:${b.hex}; border-color:${b.id === "white" || b.id === "cream" ? "#d6cebf" : b.hex}`,
      "aria-pressed": String(!s.bgImage && s.bg.id === b.id),
      onclick: () => { s.bgImage = null; this.set("bg", b); },
    }));
    const custom = !s.bgImage && s.bg.id === "custom";
    const picker = h("input", {
      type: "color", value: custom ? s.bg.hex : "#c9b79c", "aria-label": "Pick any colour",
      onchange: (e) => { s.bgImage = null; const hex = e.target.value.toUpperCase(); this.set("bg", { id: "custom", hex, say: hex }); },
    });
    const pick = h("label", {
      class: "swatch pick", title: "Any colour", "aria-pressed": String(custom),
      style: custom ? `background:${s.bg.hex}` : "background:conic-gradient(#e7b8a3,#e9d9a8,#b9d3b0,#a9c2d8,#c8b3d6,#e7b8a3)",
    }, picker);
    const file = h("input", {
      type: "file", accept: "image/*", hidden: true,
      onchange: (e) => {
        const f = e.target.files[0];
        if (!f) return;
        s.bgImage = { url: URL.createObjectURL(f), name: f.name };
        this.set("bgImage", s.bgImage);
      },
    });
    const imgBtn = h("button", {
      type: "button", class: "textlink", "aria-pressed": String(!!s.bgImage),
      onclick: () => file.click(),
    }, s.bgImage ? "My image ✓" : "Use my image");
    return h("div", { class: "swatches", role: "group", "aria-labelledby": id }, swatches, pick, imgBtn, file);
  }

  async copyText(text) {
    try { await navigator.clipboard.writeText(text); return true; } catch (_) {
      const ta = h("textarea", { style: "position:fixed;opacity:0" });
      ta.value = text;
      document.body.append(ta);
      ta.select();
      let ok = false;
      try { ok = document.execCommand("copy"); } catch (_) {}
      ta.remove();
      return ok;
    }
  }

  flash(btn, label, done) {
    btn.textContent = done;
    clearTimeout(btn._t);
    btn._t = setTimeout(() => { btn.textContent = label; }, 1800);
  }

  async copy() {
    const ok = await this.copyText(this.r.prompt(this.s));
    if (!ok) this.pre.closest("details").open = true;
    this.flash(this.copyBtn, "Copy prompt", ok ? "Copied" : "Select the prompt below to copy");
  }

  async install() {
    const text = installPrompt(this.r.installSlug || this.r.slug);
    const ok = await this.copyText(text);
    if (!ok) window.prompt("Copy this line into Claude Code:", text);
    this.flash(this.installBtn, "Install", ok ? "Copied: paste into Claude Code" : "Install");
  }
}

// For now the public page shows only the effects Naomi loves (5 Nov). The rest are hidden, not deleted,
// and still show in review mode (?review).
const LOVED = new Set(["smoothzoom", "roundcorner", "bigwords", "fourcorners", "titlestack", "reactionsplit", "podcastsplit",
  "statcard", "guestcard", "nametag", "oldfilm", "gridmat", "risecaptions", "punchin", "herotitle", "screenframe",
  "wordcard", "matchcut", "typeintro", "topcaptions", "slideupmid", "risebig"]); // slideuprise hidden 5 Nov (Naomi)
const REVIEWING = new URLSearchParams(location.search).has("review");
// Vertical (9:16) favourites go first so they're easy to find (Naomi, 5 Nov).
// Front-page order (Naomi, 5 Nov): Title stack takes Big rise words' spot; Old film and Grid mat 3 and 4;
// Type intro next to Smooth zoom; Big rise words moves just after. Everything else follows.
const PINNED = ["titlestack", "slideup", "midcaptions", "bigwords", "clipsonwhite"];
const ordered = [
  ...PINNED.map((slug) => RECIPES.find((r) => r.slug === slug)).filter(Boolean),
  ...RECIPES.filter((r) => !PINNED.includes(r.slug)),
];
const cards = ordered.filter((r) => FREE.has(r.slug)).map((r) => new Card(r));
document.getElementById("cards").append(...cards.map((c) => c.el));

// category filter
const cats = ["All", ...new Set(cards.map((c) => c.r.category))];
const filters = document.getElementById("filters");
let activeCat = "All";
function renderFilters() {
  filters.replaceChildren(...cats.map((cat) => {
    const n = cat === "All" ? cards.length : cards.filter((c) => c.r.category === cat).length;
    return h("button", {
      type: "button", "aria-pressed": String(cat === activeCat),
      onclick: () => { activeCat = cat; page = 0; renderFilters(); show(); },
    }, cat, h("span", { class: "count" }, String(n)));
  }));
}

// paging: 6 cards per page, page numbers only appear when there are more
let perPage = 6;
let page = 0;
let showAll = false;
const pager = document.getElementById("pager");
function show(scroll) {
  const list = cards.filter((c) => activeCat === "All" || c.r.category === activeCat);
  const pages = showAll ? 1 : Math.max(1, Math.ceil(list.length / perPage));
  page = Math.min(page, pages - 1);
  cards.forEach((c) => {
    const i = list.indexOf(c);
    const visible = i >= 0 && (showAll || (i >= page * perPage && i < (page + 1) * perPage));
    if (!visible && c.isOpen) c.close();
    if (!visible && c.playing) c.stop();
    c.el.hidden = !visible;
  });
  const many = list.length > perPage;
  pager.hidden = !many;
  const allBtn = h("button", { type: "button", class: "step all", onclick: () => { showAll = !showAll; page = 0; show(true); } },
    showAll ? "Show 6 per page" : `Show all ${list.length}`);
  if (showAll) { pager.replaceChildren(allBtn); cards.forEach((c) => c.layout()); if (scroll) filters.scrollIntoView({ behavior: "smooth", block: "start" }); return; }
  pager.replaceChildren(
    h("button", { type: "button", class: "step", disabled: page === 0, onclick: () => { page--; show(true); } }, "Previous"),
    ...Array.from({ length: pages }, (_, i) => h("button", {
      type: "button", "aria-current": i === page ? "page" : false, "aria-label": `Page ${i + 1}`,
      onclick: () => { page = i; show(true); },
    }, String(i + 1))),
    h("button", { type: "button", class: "step", disabled: page === pages - 1, onclick: () => { page++; show(true); } }, "Next"),
    allBtn);
  cards.forEach((c) => c.layout());
  if (scroll) filters.scrollIntoView({ behavior: "smooth", block: "start" });
}
renderFilters();
show();
window.gallery = { setPerPage(n) { perPage = n; page = 0; show(); } }; // for testing

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") cards.forEach((c) => c.isOpen && c.close());
});

// No right-click "Save video / Save image" on the demos, and no dragging them out.
// This stops casual saving only: anyone determined can still find the files.
document.addEventListener("contextmenu", (e) => { if (e.target.closest(".view")) e.preventDefault(); });
document.addEventListener("dragstart", (e) => { if (e.target.closest(".view")) e.preventDefault(); });

// ---------- private review mode (open the page with ?review) ----------
// Naomi marks each effect Love / Keep / Cut. Saved only in this browser. Not shown on the public page.
if (new URLSearchParams(location.search).has("review")) {
  const KEY = "editing-recipes-review";
  let marks = {};
  try { marks = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (_) {}
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(marks)); } catch (_) {} };
  const CHOICES = [["love", "Love"], ["keep", "Keep"], ["cut", "Cut"]];
  document.body.classList.add("reviewing");

  const bar = h("div", { class: "review-bar" });
  const summary = h("p", { class: "review-sum" });
  const copyBtn = h("button", { type: "button", class: "copy", onclick: async () => {
    const lines = CHOICES.map(([k, label]) => `${label}: ` + (cards.filter((c) => marks[c.r.slug] === k).map((c) => c.r.title).join(", ") || "none"));
    const un = cards.filter((c) => !marks[c.r.slug]).map((c) => c.r.title);
    lines.push("Not marked yet: " + (un.join(", ") || "none"));
    const text = lines.join("\n");
    let ok = false;
    try { await navigator.clipboard.writeText(text); ok = true; } catch (_) { window.prompt("Copy your list:", text); }
    copyBtn.textContent = ok ? "Copied" : "Copy my list";
    setTimeout(() => { copyBtn.textContent = "Copy my list"; }, 1800);
  } }, "Copy my list");
  bar.append(h("strong", {}, "Review mode"), summary, copyBtn);
  document.body.prepend(bar);

  const refresh = () => {
    const n = (k) => cards.filter((c) => marks[c.r.slug] === k).length;
    summary.textContent = `Love ${n("love")} · Keep ${n("keep")} · Cut ${n("cut")} · Not marked ${cards.length - n("love") - n("keep") - n("cut")}`;
    cards.forEach((c) => {
      c.el.dataset.mark = marks[c.r.slug] || "";
      c.el.querySelectorAll(".mark-btns button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.k === marks[c.r.slug])));
    });
  };
  cards.forEach((c) => {
    const btns = h("div", { class: "mark-btns", role: "group", "aria-label": "Mark this effect" },
      CHOICES.map(([k, label]) => h("button", { type: "button", "data-k": k, onclick: (e) => {
        e.stopPropagation();
        if (marks[c.r.slug] === k) delete marks[c.r.slug]; else marks[c.r.slug] = k;
        save(); refresh();
      } }, label)));
    c.el.querySelector(".body").prepend(btns);
  });
  refresh();
  // see every effect at once while reviewing
  const all = [...document.querySelectorAll("#pager button")].find((b) => b.textContent.startsWith("Show all"));
  if (all) all.click();
}
