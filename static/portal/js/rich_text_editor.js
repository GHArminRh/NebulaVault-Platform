(() => {
  "use strict";

  const EXCLUDED = [
    "textarea[data-no-rich-editor]", "textarea.no-rich-editor",
    "textarea[name*='json' i]", "textarea[name*='payload' i]",
    "textarea[name*='metadata' i]", "textarea[name*='config' i]",
    "textarea[name*='query' i]", "textarea[name*='code' i]",
    "textarea[name*='sql' i]", "textarea[name*='token' i]",
    "textarea[name*='secret' i]", "textarea[name*='key' i]"
  ].join(",");
  const ELIGIBLE = [
    "textarea[data-rich-editor]", "textarea.rich-text",
    "textarea[name='description']", "textarea[name='release_notes']",
    "textarea[name='content']", "textarea[name='body']",
    "textarea[name='terms']", "textarea[name='policy']"
  ].join(",");
  const ALLOWED_TAGS = new Set(("P BR DIV H1 H2 H3 H4 H5 H6 STRONG B EM I U S STRIKE DEL INS MARK SUB SUP UL OL LI A BLOCKQUOTE PRE CODE HR TABLE CAPTION THEAD TBODY TFOOT TR TH TD SPAN SMALL FIGURE FIGCAPTION IMG IFRAME DL DT DD").split(" "));
  const DROP_CONTENT = new Set(["SCRIPT", "STYLE", "OBJECT", "EMBED", "FORM", "INPUT", "BUTTON", "TEXTAREA", "SVG", "MATH", "VIDEO", "AUDIO", "LINK", "META", "TEMPLATE"]);
  const SAFE_STYLES = new Set([
    "color", "background-color", "font-family", "font-size", "font-weight",
    "font-style", "text-decoration", "text-align", "vertical-align",
    "line-height", "white-space", "width", "height", "max-width",
    "border", "border-color", "border-width", "border-style", "border-collapse",
    "padding", "padding-top", "padding-right", "padding-bottom", "padding-left", "page-break-after",
    "margin", "margin-top", "margin-right", "margin-bottom", "margin-left"
  ]);
  const ICONS = {
    undo:'<path d="M3 7v6h6"/><path d="M3.5 13A8 8 0 1 0 5 6.5L3 9"/>',
    redo:'<path d="M21 7v6h-6"/><path d="M20.5 13A8 8 0 1 1 19 6.5L21 9"/>',
    bold:'<path d="M7 4h6a4 4 0 0 1 0 8H7z"/><path d="M7 12h7a4 4 0 0 1 0 8H7z"/>',
    italic:'<path d="M14 4h6"/><path d="M4 20h6"/><path d="m15 4-6 16"/>',
    underline:'<path d="M6 4v6a6 6 0 0 0 12 0V4"/><path d="M4 20h16"/>',
    strike:'<path d="M4 12h16"/><path d="M7 6a5 5 0 0 1 9-1"/><path d="M17 18a5 5 0 0 1-9 1"/>',
    sub:'<path d="M4 5l8 9"/><path d="M12 5 4 14"/><path d="M15 18c0-2 4-2 4-4a2 2 0 0 0-4 0"/><path d="M14 20h6"/>',
    sup:'<path d="M4 5l8 9"/><path d="M12 5 4 14"/><path d="M16 7c0-2 4-2 4-4a2 2 0 0 0-4 0"/>',
    link:'<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>',
    unlink:'<path d="M10 13a5 5 0 0 0 7.5.5l2-2"/><path d="M14 11a5 5 0 0 0-7.5-.5l-2 2"/><path d="m3 3 18 18"/><path d="m13 5 1.5-1.5a5 5 0 0 1 7 7L20 12"/><path d="m11 19-1.5 1.5a5 5 0 0 1-7-7L4 12"/>',
    image:'<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8.5" cy="9" r="1.5"/><path d="m21 15-5-5L5 20"/>',
    table:'<rect x="3" y="4" width="18" height="16" rx="1"/><path d="M3 10h18M3 15h18M9 4v16M15 4v16"/>',
    quote:'<path d="M3 11h7v7H3zM14 11h7v7h-7z"/><path d="M3 11c0-4 2-6 6-7M14 11c0-4 2-6 6-7"/>',
    code:'<path d="m8 7-5 5 5 5M16 7l5 5-5 5M14 4l-4 16"/>',
    source:'<path d="m8 6-6 6 6 6M16 6l6 6-6 6"/><path d="m14 3-4 18"/>',
    imageUp:'<path d="M12 16V4"/><path d="m7 9 5-5 5 5"/><path d="M4 14v5a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-5"/>',
    alignLeft:'<path d="M4 6h16M4 10h10M4 14h16M4 18h10"/>',
    alignCenter:'<path d="M4 6h16M7 10h10M4 14h16M7 18h10"/>',
    alignRight:'<path d="M4 6h16M10 10h10M4 14h16M10 18h10"/>',
    justify:'<path d="M4 6h16M4 10h16M4 14h16M4 18h16"/>',
    bullet:'<circle cx="5" cy="6" r="1"/><circle cx="5" cy="12" r="1"/><circle cx="5" cy="18" r="1"/><path d="M9 6h11M9 12h11M9 18h11"/>',
    numbered:'<path d="M10 6h10M10 12h10M10 18h10"/><path d="M4 5h1v3M4 11h2l-2 2h2M4 17h2l-2 2h2"/>',
    indent:'<path d="M4 6h16M4 10h9M4 14h9M4 18h16"/><path d="m16 10 3 2-3 2"/>',
    outdent:'<path d="M4 6h16M11 10h9M11 14h9M4 18h16"/><path d="m7 10-3 2 3 2"/>',
    plus:'<path d="M12 5v14M5 12h14"/>',
    minus:'<path d="M5 12h14"/>',
    close:'<path d="m6 6 12 12M18 6 6 18"/>',
    video:'<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m10 9 5 3-5 3z"/>',
    search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
    maximize:'<path d="M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M3 16v3a2 2 0 0 0 2 2h3M21 16v3a2 2 0 0 1-2 2h-3"/>',
    minimize:'<path d="M4 14h6v6M20 10h-6V4M14 10l7-7M3 21l7-7"/>',
    more:'<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
    print:'<path d="M6 9V3h12v6M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><path d="M6 14h12v7H6z"/>',
    check:'<path d="m5 12 4 4L19 6"/>',
    chevron:'<path d="m9 18 6-6-6-6"/>',
    down:'<path d="m6 9 6 6 6-6"/>',
    file:'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h8"/>',
    refresh:'<path d="M20 7v5h-5"/><path d="M4 17v-5h5"/><path d="M5.5 9A7 7 0 0 1 18 6l2 6M4 12l2 6a7 7 0 0 0 12.5-3"/>',
    help:'<circle cx="12" cy="12" r="10"/><path d="M9.5 9a2.6 2.6 0 1 1 4.4 1.9c-1.1.8-1.9 1.3-1.9 2.6M12 17h.01"/>',
    checkList:'<path d="m3 6 2 2 3-4M10 7h11M3 13l2 2 3-4M10 14h11M3 20l2 2 3-4M10 21h11"/>',
    ruler:'<path d="M3 7h18v10H3z"/><path d="M7 7v4M11 7v2M15 7v4M19 7v2"/>',
    special:'<circle cx="12" cy="12" r="9"/><path d="M9 9a3 3 0 1 1 5 2c-1.2.8-2 1.3-2 3M12 17h.01"/>',
    calendar:'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/>'
  };
  const esc = (s) => String(s == null ? "" : s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");
  const icon = (name) => '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">'+(ICONS[name] || ICONS.more)+'</svg>';
  const safeUrl = (value, image) => {
    const u = String(value || "").trim();
    if (!u || /[\u0000-\u001f]/.test(u) || /^javascript:|^data:|^vbscript:/i.test(u)) return "";
    if (/^(https?:|mailto:|tel:|\/|#)/i.test(u)) return image && !/^https?:|^\//i.test(u) ? "" : u;
    if (/^[\w.-]+\.[a-z]{2,}(\/|$)/i.test(u)) return "https://" + u;
    return "";
  };
  function safeEmbedUrl(value) {
    try {
      const u = new URL(String(value || ""), document.baseURI);
      if (u.protocol !== "https:" || u.username || u.password || (u.port && u.port !== "443")) return "";
      const host = u.hostname.toLowerCase();
      if (["youtube.com", "www.youtube.com", "www.youtube-nocookie.com"].includes(host) &&
          /^\/embed\/[A-Za-z0-9_-]{6,20}\/?$/.test(u.pathname)) return u.origin + u.pathname;
      if (host === "player.vimeo.com" && /^\/video\/[0-9]{5,12}\/?$/.test(u.pathname)) return u.origin + u.pathname;
    } catch (_) {}
    return "";
  }
  function clean(html) {
    const doc = new DOMParser().parseFromString(String(html || ""), "text/html");
    const legacySizes = {"1":"10px","2":"13px","3":"16px","4":"18px","5":"24px","6":"32px","7":"48px"};
    doc.querySelectorAll("font").forEach(font => {
      const span = doc.createElement("span");
      const style = [];
      const color = font.getAttribute("color");
      const face = font.getAttribute("face");
      const size = font.getAttribute("size");
      if (color && color.length <= 40 && !/[;{}<>]/.test(color)) style.push("color:" + color);
      if (face && face.length <= 80 && !/[;{}<>]/.test(face)) style.push("font-family:" + face);
      if (size && legacySizes[size]) style.push("font-size:" + legacySizes[size]);
      if (style.length) span.setAttribute("style", style.join(";"));
      span.innerHTML = font.innerHTML;
      font.replaceWith(span);
    });
    doc.querySelectorAll(Array.from(DROP_CONTENT).join(",")).forEach(n => n.remove());
    const walker = doc.createTreeWalker(doc.body, NodeFilter.SHOW_ELEMENT), nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(n => {
      if (!n.parentNode) return;
      if (!ALLOWED_TAGS.has(n.tagName)) { n.replaceWith(...Array.from(n.childNodes)); return; }
      Array.from(n.attributes).forEach(a => {
        const k = a.name.toLowerCase(), v = a.value.trim();
        const allowed = ["href","target","rel","title","src","alt","width","height","colspan","rowspan","scope","start","reversed","dir","style","align","type"];
        if (k.startsWith("on") || !allowed.includes(k)) { n.removeAttribute(a.name); return; }
        if (k === "href") { const u = safeUrl(v,false); if (u) n.setAttribute("href",u); else n.removeAttribute("href"); }
        if (k === "src") { const u = safeUrl(v,true); if (u && (n.tagName !== "IMG" || /^(https?:|\/)/i.test(u))) n.setAttribute("src",u); else n.removeAttribute("src"); }
        if (k === "target" && v !== "_blank" && v !== "_self") n.removeAttribute(k);
        if (k === "style") {
          const declarations = v.split(";").map(x => x.trim()).filter(Boolean).map(x => {
            const i=x.indexOf(":"); if(i<1) return null;
            const key=x.slice(0,i).trim().toLowerCase(), val=x.slice(i+1).trim();
            if(!SAFE_STYLES.has(key) || /url\s*\(|expression\s*\(|javascript:|position\s*:|behavior\s*:|@import/i.test(val) || val.length>120) return null;
            return key+":"+val;
          }).filter(Boolean);
          if(declarations.length) n.setAttribute("style",declarations.join(";")); else n.removeAttribute("style");
        }
      });
      if (n.tagName === "IFRAME") {
        const embed = safeEmbedUrl(n.getAttribute("src") || "");
        if (!embed) { n.remove(); return; }
        n.setAttribute("src", embed);
        n.setAttribute("title", n.getAttribute("title") || "Embedded video");
        n.setAttribute("loading", "lazy");
        n.setAttribute("referrerpolicy", "strict-origin-when-cross-origin");
        n.setAttribute("sandbox", "allow-scripts allow-same-origin allow-presentation");
        n.setAttribute("allow", "autoplay; encrypted-media; fullscreen; picture-in-picture");
        n.setAttribute("allowfullscreen", "allowfullscreen");
      }
      if (n.tagName === "A" && n.target === "_blank") n.rel = "noopener noreferrer";
      if (n.tagName === "IMG") { n.loading = "lazy"; n.decoding = "async"; }
    });
    return doc.body.innerHTML;
  }
  function asHtml(value) {
    if (!value) return "";
    if (/<\/?[a-z][\s\S]*>/i.test(value)) return clean(value);
    return String(value).replace(/\r\n?/g,"\n").split("\n").map(line => "<p>"+(line ? esc(line) : "<br>")+"</p>").join("");
  }
  function textOf(html) {
    const d=document.createElement("div"); d.innerHTML=clean(html); return (d.textContent || "").replace(/\u00a0/g," ").trim();
  }
  function enhance(ta) {
    if (!(ta instanceof HTMLTextAreaElement) || ta.disabled || ta.readOnly || ta.matches(EXCLUDED) || ta.closest("[data-no-rich-editor],[hidden]") || ta.dataset.nvEditorReady) return;
    if (!ta.matches(ELIGIBLE)) return;
    ta.dataset.nvEditorReady = "true";
    const wrap=document.createElement("section");
    wrap.className="nv-cke";
    wrap.setAttribute("data-editor-ready","true");
    wrap.setAttribute("aria-label","Rich text editor");
    const menuBar=document.createElement("div"); menuBar.className="nv-cke-menubar"; menuBar.setAttribute("role","menubar");
    const toolbar=document.createElement("div"); toolbar.className="nv-cke-toolbar"; toolbar.setAttribute("role","toolbar"); toolbar.setAttribute("aria-label","Formatting toolbar");
    const toolbarTop=document.createElement("div"); toolbarTop.className="nv-cke-toolbar-row nv-cke-toolbar-primary";
    const toolbarBottom=document.createElement("div"); toolbarBottom.className="nv-cke-toolbar-row nv-cke-toolbar-secondary";
    const surface=document.createElement("div"); surface.className="nv-cke-editable"; surface.contentEditable="true"; surface.setAttribute("role","textbox"); surface.setAttribute("aria-multiline","true"); surface.setAttribute("aria-label",ta.getAttribute("aria-label")||ta.name||"Rich text content"); surface.spellcheck=true;
    const source=document.createElement("textarea"); source.className="nv-cke-source"; source.setAttribute("aria-label","HTML source"); source.hidden=true; source.spellcheck=false;
    const status=document.createElement("div"); status.className="nv-cke-statusbar";
    const statusPath=document.createElement("div"); statusPath.className="nv-cke-element-path"; statusPath.setAttribute("aria-live","polite");
    const statusCounts=document.createElement("div"); statusCounts.className="nv-cke-counts";
    const saveState=document.createElement("span"); saveState.className="nv-cke-save-state"; saveState.textContent="Unsaved edits";
    const wordCount=document.createElement("span"); const charCount=document.createElement("span");
    statusCounts.append(saveState,wordCount,charCount); status.append(statusPath,statusCounts);
    const floatBar=document.createElement("div"); floatBar.className="nv-cke-balloon"; floatBar.hidden=true;
    const popover=document.createElement("div"); popover.className="nv-cke-popover-root";
    const modalRoot=document.createElement("div"); modalRoot.className="nv-cke-modal-root";
    let html="", sourceMode=false, fullScreen=false, showBlocks=false, savedRange=null, menuPanel=null, colorPanel=null, currentDialog=null;
    const LANG_FA=(document.documentElement.lang||"").toLowerCase().startsWith("fa");
    const tr=(en,fa)=>LANG_FA?(fa||en):en;
    function rememberRange() {
      const sel=window.getSelection();
      if(sel && sel.rangeCount && surface.contains(sel.anchorNode)) savedRange=sel.getRangeAt(0).cloneRange();
    }
    function restoreRange() {
      if(!savedRange) return;
      try { const sel=window.getSelection(); sel.removeAllRanges(); sel.addRange(savedRange); } catch (_) {}
    }
    function sync() {
      html=sourceMode?clean(source.value):clean(surface.innerHTML);
      ta.value=html;
      const txt=textOf(html), words=txt?txt.split(/\s+/).filter(Boolean).length:0;
      wordCount.textContent=tr(words+" words",words+" کلمه");
      charCount.textContent=tr(txt.length+" characters",txt.length+" نویسه");
      saveState.textContent=tr("Edits are not saved until you submit","تغییرات پس از ثبت فرم ذخیره می‌شوند");
    }
    function setSurface(value) { html=clean(value); surface.innerHTML=html; sync(); }
    function closePopover() { popover.replaceChildren(); popover.hidden=true; colorPanel=null; }
    function closeMenu() { if(menuPanel) menuPanel.remove(); menuPanel=null; menuBar.querySelectorAll("[aria-expanded=true]").forEach(b=>b.setAttribute("aria-expanded","false")); }
    function hideDialog() { modalRoot.replaceChildren(); modalRoot.hidden=true; currentDialog=null; }
    function openDialog(title, fields, onApply, description) {
      hideDialog(); closeMenu(); closePopover();
      const shade=document.createElement("div"); shade.className="nv-cke-dialog-shade";
      const box=document.createElement("section"); box.className="nv-cke-dialog"; box.setAttribute("role","dialog"); box.setAttribute("aria-modal","true"); box.setAttribute("aria-label",title);
      const head=document.createElement("header"); head.className="nv-cke-dialog-head";
      const h=document.createElement("h2"); h.textContent=title;
      const x=document.createElement("button"); x.type="button"; x.className="nv-cke-dialog-close"; x.innerHTML=icon("close"); x.setAttribute("aria-label",tr("Close","بستن")); x.addEventListener("click",hideDialog);
      head.append(h,x); box.append(head);
      if(description){const d=document.createElement("p");d.className="nv-cke-dialog-description";d.textContent=description;box.append(d);}
      const form=document.createElement("form"); form.className="nv-cke-dialog-form";
      const controls={};
      fields.forEach(f=>{
        const row=document.createElement("label"); row.className="nv-cke-field"; row.htmlFor="nv-cke-field-"+f.name;
        const titleEl=document.createElement("span"); titleEl.textContent=f.label; row.append(titleEl);
        let input;
        if(f.type==="textarea"){input=document.createElement("textarea");input.rows=f.rows||3;}
        else if(f.type==="select"){input=document.createElement("select");(f.options||[]).forEach(o=>{const opt=document.createElement("option");opt.value=o.value;opt.textContent=o.label;input.append(opt);});}
        else {input=document.createElement("input");input.type=f.type||"text";}
        input.id="nv-cke-field-"+f.name; input.name=f.name;
        if(f.value!=null) {if(f.type==="checkbox")input.checked=!!f.value;else input.value=f.value;}
        if(f.placeholder)input.placeholder=f.placeholder;
        if(f.accept)input.accept=f.accept;
        if(f.required)input.required=true;
        if(f.min!=null)input.min=f.min;
        if(f.max!=null)input.max=f.max;
        if(f.type==="checkbox")row.classList.add("nv-cke-checkbox-field");
        if(f.help){const help=document.createElement("small");help.textContent=f.help;row.append(input,help);}else row.append(input);
        form.append(row);controls[f.name]=input;
      });
      const actions=document.createElement("div");actions.className="nv-cke-dialog-actions";
      const cancel=document.createElement("button");cancel.type="button";cancel.className="nv-cke-btn nv-cke-btn-subtle";cancel.textContent=tr("Cancel","لغو");cancel.addEventListener("click",hideDialog);
      const apply=document.createElement("button");apply.type="submit";apply.className="nv-cke-btn nv-cke-btn-primary";apply.textContent=tr("Insert","درج");
      actions.append(cancel,apply);form.append(actions);box.append(form);shade.append(box);modalRoot.replaceChildren(shade);modalRoot.hidden=false;currentDialog=box;
      shade.addEventListener("mousedown",e=>{if(e.target===shade)hideDialog();});
      form.addEventListener("submit",e=>{e.preventDefault();const values={};fields.forEach(f=>values[f.name]=f.type==="checkbox"?controls[f.name].checked:(f.type==="file"?(controls[f.name].files&&controls[f.name].files[0]||null):controls[f.name].value));if(onApply(values)===false)return;hideDialog();surface.focus();sync();});
      const first=fields.map(f=>controls[f.name]).find(el=>el.type!=="checkbox"); if(first)requestAnimationFrame(()=>first.focus());
      document.addEventListener("keydown",dialogEscape,{once:true});
    }
    function dialogEscape(e){if(e.key==="Escape"&&currentDialog)hideDialog();}
    function insertHtml(markup) { restoreRange(); surface.focus(); document.execCommand("insertHTML",false,markup); afterEdit(); }
    function runCommand(command,value) {
      closePopover(); closeMenu(); restoreRange(); surface.focus();
      if(command==="paragraph") document.execCommand("formatBlock",false,"p");
      else if(/^h[1-6]$/.test(command)) document.execCommand("formatBlock",false,command);
      else if(command==="blockquote") document.execCommand("formatBlock",false,"blockquote");
      else if(command==="pre") document.execCommand("formatBlock",false,"pre");
      else if(command==="code") document.execCommand("insertHTML",false,"<code>"+(window.getSelection()?.toString()?esc(window.getSelection().toString()):"code")+"</code>");
      else if(command==="direction-rtl"||command==="direction-ltr") surface.dir=command.endsWith("rtl")?"rtl":"ltr";
      else if(command==="showBlocks") { showBlocks=!showBlocks; wrap.classList.toggle("nv-cke-show-blocks",showBlocks); }
      else if(command==="fullscreen") toggleFullscreen();
      else if(command==="source") toggleSource();
      else if(command==="find") openFindReplace(false);
      else if(command==="replace") openFindReplace(true);
      else if(command==="insertLink") openLinkDialog();
      else if(command==="insertImage") openImageDialog();
      else if(command==="insertMedia") openMediaDialog();
      else if(command==="insertTable") openTableDialog();
      else if(command==="tableOps") openTableOps();
      else if(command==="special") openSpecialChars();
      else if(command==="download") downloadHtml();
      else if(command==="import") importHtml();
      else if(command==="print") window.print();
      else if(command==="wordCount") openWordCount();
      else if(command==="help") openHelp();
      else if(command==="timestamp") insertHtml("<span>"+esc(new Date().toLocaleString())+"</span>");
      else if(command==="pageBreak") insertHtml('<hr style="page-break-after:always" aria-label="Page break">');
      else if(command==="selectAll") { const r=document.createRange();r.selectNodeContents(surface);const s=window.getSelection();s.removeAllRanges();s.addRange(r);rememberRange(); }
      else if(command==="unlink") document.execCommand("unlink",false,null);
      else if(command==="removeFormat") document.execCommand("removeFormat",false,null);
      else if(command==="hr") document.execCommand("insertHorizontalRule",false,null);
      else if(command==="fontSize") { document.execCommand("fontSize",false,value||null); const sizes={"1":"10px","2":"13px","3":"16px","4":"18px","5":"24px","6":"32px","7":"48px"}; surface.querySelectorAll('font[size]').forEach(f=>{const span=document.createElement("span");span.style.fontSize=sizes[f.getAttribute("size")]||"16px";span.innerHTML=f.innerHTML;f.replaceWith(span);}); }
      else if(command==="fontName") { document.execCommand("fontName",false,value||null); surface.querySelectorAll("font[face]").forEach(f=>{const span=document.createElement("span");span.style.fontFamily=f.getAttribute("face");span.innerHTML=f.innerHTML;f.replaceWith(span);}); }
      else if(command==="undo"||command==="redo") document.execCommand(command,false,null);
      else if(command==="imageFromFile") { const inp=document.createElement("input");inp.type="file";inp.accept="image/png,image/jpeg,image/gif,image/webp";inp.addEventListener("change",()=>{if(inp.files&&inp.files[0])showToast(tr("Image uploads need a server upload adapter; use an image URL for now.","برای بارگذاری تصویر باید سرویس آپلود سرور وصل شود؛ فعلاً از نشانی تصویر استفاده کنید."),"info");});inp.click(); }
      else if(command==="insertBullet"||command==="insertNumber") document.execCommand(command==="insertBullet"?"insertUnorderedList":"insertOrderedList",false,null);
      else document.execCommand(command,false,value||null);
      afterEdit();
    }
    function afterEdit() { if(!sourceMode) html=clean(surface.innerHTML); sync(); updatePath(); updateActiveButtons(); }
    function makeButton(parent,action,label,glyph,options) {
      const b=document.createElement("button");b.type="button";b.className="nv-cke-tool";b.dataset.action=action;b.title=label;b.setAttribute("aria-label",label);
      if(options&&options.text)b.classList.add("nv-cke-tool-text");
      b.innerHTML=(glyph?icon(glyph):"")+(options&&options.text?'<span>'+esc(options.text)+'</span>':"");
      if(options&&options.menu){b.classList.add("nv-cke-has-menu");b.append(document.createTextNode(""));const c=document.createElement("span");c.className="nv-cke-tool-chevron";c.innerHTML=icon("down");b.append(c);}
      b.addEventListener("mousedown",e=>{if(e.button===0)rememberRange();e.preventDefault();});
      b.addEventListener("click",()=>{runCommand(action);});
      parent.append(b);return b;
    }
    function separator(parent) {const s=document.createElement("span");s.className="nv-cke-separator";s.setAttribute("aria-hidden","true");parent.append(s);}
    function makeSelect(parent,label,items,handler,cls) {
      const wrapSel=document.createElement("label");wrapSel.className="nv-cke-select-wrap"+(cls?" "+cls:"");
      const sel=document.createElement("select");sel.setAttribute("aria-label",label);sel.title=label;
      items.forEach(i=>{const o=document.createElement("option");o.value=i.value;o.textContent=i.label;sel.append(o);});
      sel.addEventListener("mousedown",rememberRange);sel.addEventListener("change",()=>{restoreRange();handler(sel.value);surface.focus();afterEdit();});
      wrapSel.append(sel);parent.append(wrapSel);return sel;
    }
    function createColorTool(parent,label,cmd,initialColor) {
      const group=document.createElement("div");group.className="nv-cke-color-group";
      const b=document.createElement("button");b.type="button";b.className="nv-cke-tool nv-cke-color-tool";b.title=label;b.setAttribute("aria-label",label);b.innerHTML='<span class="nv-cke-color-letter">'+(cmd==="foreColor"?"A":"▰")+'</span><span class="nv-cke-color-underline" style="background:'+initialColor+'"></span><span class="nv-cke-tool-chevron">'+icon("down")+'</span>';
      b.addEventListener("mousedown",e=>{rememberRange();e.preventDefault();});
      b.addEventListener("click",()=>openColorPanel(b,cmd,label));group.append(b);parent.append(group);
    }
    function openColorPanel(anchor,cmd,label) {
      closePopover();colorPanel=cmd;
      const panel=document.createElement("div");panel.className="nv-cke-popover nv-cke-color-panel";
      const title=document.createElement("div");title.className="nv-cke-popover-title";title.textContent=label;panel.append(title);
      const palette=["#000000","#434343","#666666","#999999","#b7b7b7","#d9d9d9","#ffffff","#c00000","#ff0000","#ff9900","#ffff00","#92d050","#00b050","#00b0f0","#0070c0","#7030a0","#e6b8af","#f4cccc","#fce5cd","#fff2cc","#d9ead3","#d0e0e3","#cfe2f3","#d9d2e9","#ead1dc","#f6b26b","#ffd966","#a4c2f4","#b4a7d6","#d5a6bd","#6aa84f","#45818e","#3c78d8","#674ea7","#a64d79"];
      const grid=document.createElement("div");grid.className="nv-cke-swatches";
      palette.forEach(color=>{const sw=document.createElement("button");sw.type="button";sw.className="nv-cke-swatch";sw.style.backgroundColor=color;sw.title=color;sw.setAttribute("aria-label",color);sw.addEventListener("mousedown",e=>e.preventDefault());sw.addEventListener("click",()=>{restoreRange();surface.focus();document.execCommand(cmd,false,color);closePopover();afterEdit();});grid.append(sw);});panel.append(grid);
      const custom=document.createElement("label");custom.className="nv-cke-custom-color";custom.textContent=tr("Custom color","رنگ دلخواه");const input=document.createElement("input");input.type="color";input.value=cmd==="foreColor"?"#2f3b52":"#fff09a";input.addEventListener("input",()=>{restoreRange();surface.focus();document.execCommand(cmd,false,input.value);afterEdit();});custom.append(input);panel.append(custom);
      const clear=document.createElement("button");clear.type="button";clear.className="nv-cke-btn nv-cke-btn-subtle nv-cke-color-clear";clear.textContent=tr("Remove color","حذف رنگ");clear.addEventListener("click",()=>{restoreRange();surface.focus();document.execCommand(cmd==="foreColor"?"foreColor":"hiliteColor",false,cmd==="foreColor"?"#202b40":"transparent");closePopover();afterEdit();});panel.append(clear);
      popover.append(panel);popover.hidden=false;const r=anchor.getBoundingClientRect();popover.style.left=Math.max(8,Math.min(window.innerWidth-250,r.left))+"px";popover.style.top=Math.min(window.innerHeight-280,r.bottom+6)+"px";
    }
    function buildMenus() {
      const menus=[
        {name:tr("File","فایل"),items:[["New content","new"],["Import HTML…","import"],["Export HTML…","download"],["Print…","print"],["—","sep"],["Fullscreen","fullscreen"]]},
        {name:tr("Edit","ویرایش"),items:[["Undo","undo"],["Redo","redo"],["—","sep"],["Cut / Copy / Paste","clipboard"],["Select all","selectAll"],["Find…","find"],["Find and replace…","replace"],["Remove formatting","removeFormat"]]},
        {name:tr("View","نما"),items:[["Show block boundaries","showBlocks"],["Right-to-left text","direction-rtl"],["Left-to-right text","direction-ltr"],["Word count…","wordCount"],["Fullscreen","fullscreen"]]},
        {name:tr("Insert","درج"),items:[["Link…","insertLink"],["Image…","insertImage"],["Video/media…","insertMedia"],["Table…","insertTable"],["Code block","pre"],["Block quote","blockquote"],["Horizontal line","hr"],["Page break","pageBreak"],["Special character…","special"],["Date and time","timestamp"]]},
        {name:tr("Format","قالب‌بندی"),items:[["Paragraph","paragraph"],["Heading 1","h1"],["Heading 2","h2"],["Heading 3","h3"],["Heading 4","h4"],["—","sep"],["Bold","bold"],["Italic","italic"],["Underline","underline"],["Strikethrough","strikeThrough"],["Superscript","superscript"],["Subscript","subscript"],["Inline code","code"],["—","sep"],["Align left","justifyLeft"],["Center","justifyCenter"],["Align right","justifyRight"],["Justify","justifyFull"],["Increase indent","indent"],["Decrease indent","outdent"]]},
        {name:tr("Tools","ابزارها"),items:[["Table tools…","tableOps"],["Word count…","wordCount"],["Keyboard shortcuts","help"]]},
        {name:tr("Help","راهنما"),items:[["Keyboard shortcuts","help"],["About Nebula Editor","about"]]}
      ];
      menus.forEach(m=>{
        const host=document.createElement("div");host.className="nv-cke-menu-host";
        const b=document.createElement("button");b.type="button";b.className="nv-cke-menu-trigger";b.textContent=m.name;b.setAttribute("role","menuitem");b.setAttribute("aria-expanded","false");
        b.addEventListener("click",()=>{if(menuPanel&&menuPanel.dataset.menu===m.name){closeMenu();return;}closeMenu();closePopover();const panel=document.createElement("div");panel.className="nv-cke-menu-panel";panel.dataset.menu=m.name;panel.setAttribute("role","menu");m.items.forEach(([label,act])=>{if(act==="sep"){const s=document.createElement("div");s.className="nv-cke-menu-separator";panel.append(s);return;}const item=document.createElement("button");item.type="button";item.className="nv-cke-menu-item";item.setAttribute("role","menuitem");item.textContent=label;item.addEventListener("mousedown",e=>{rememberRange();e.preventDefault();});item.addEventListener("click",()=>{closeMenu();if(act==="new"){setSurface("<p><br></p>");return;}if(act==="clipboard"){showToast(tr("Use the standard browser clipboard shortcuts.","از میان‌برهای استاندارد کلیپ‌بورد مرورگر استفاده کنید."),"info");return;}if(act==="about"){openDialog("Nebula Editor",[ {name:"info",label:"Editor",type:"text",value:"Nebula Editor · Custom rich-text editor"} ],()=>true,"A purpose-built editor for the Nebula Vault portal.");return;}runCommand(act);});panel.append(item);});host.append(panel);menuPanel=panel;b.setAttribute("aria-expanded","true");});host.append(b);menuBar.append(host);
      });
    }
    function updatePath() {
      if(sourceMode){statusPath.textContent="HTML";return;}
      const sel=window.getSelection();let node=sel&&sel.anchorNode;if(node&&node.nodeType===3)node=node.parentElement;
      if(!node||!surface.contains(node)){statusPath.textContent=tr("Document","سند");return;}
      const parts=[];while(node&&node!==surface&&parts.length<4){if(node.nodeType===1){let label=node.tagName.toLowerCase();if(node.tagName==="TD"||node.tagName==="TH")label=node.tagName.toLowerCase();parts.unshift(label);}node=node.parentElement;}
      statusPath.replaceChildren();if(!parts.length)parts.push("document");parts.forEach((part,i)=>{const b=document.createElement("button");b.type="button";b.textContent=part;b.title=tr("Select "+part,"انتخاب "+part);b.addEventListener("click",()=>{const matches=surface.querySelectorAll(part);if(matches.length){const r=document.createRange();r.selectNodeContents(matches[matches.length-1]);const s=window.getSelection();s.removeAllRanges();s.addRange(r);rememberRange();}});statusPath.append(b);if(i<parts.length-1){const sep=document.createElement("span");sep.textContent="›";statusPath.append(sep);}});
    }
    function updateActiveButtons() {
      if(sourceMode)return;
      toolbar.querySelectorAll("[data-command]").forEach(b=>{const c=b.dataset.command;let active=false;try{active=document.queryCommandState(c);}catch(_){}b.classList.toggle("is-active",active);b.setAttribute("aria-pressed",String(active));});
    }
    function addFormattingToolbar(parent) {
      makeButton(parent,"undo",tr("Undo (Ctrl+Z)","واگرد (Ctrl+Z)"),"undo");
      makeButton(parent,"redo",tr("Redo (Ctrl+Y)","ازنو (Ctrl+Y)"),"redo");
      separator(parent);
      makeSelect(parent,tr("Block style","قالب بلوک"),[
        {value:"p",label:tr("Paragraph","پاراگراف")},{value:"h1",label:"Heading 1"},{value:"h2",label:"Heading 2"},{value:"h3",label:"Heading 3"},{value:"h4",label:"Heading 4"},{value:"blockquote",label:tr("Quote","نقل‌قول")},{value:"pre",label:tr("Code block","بلوک کد")}
      ],v=>{restoreRange();surface.focus();document.execCommand("formatBlock",false,v);afterEdit();},"nv-cke-block-select");
      separator(parent);
      [["bold",tr("Bold (Ctrl+B)","ضخیم (Ctrl+B)"),"bold"],["italic",tr("Italic (Ctrl+I)","مورب (Ctrl+I)"),"italic"],["underline",tr("Underline (Ctrl+U)","زیرخط (Ctrl+U)"),"underline"],["strikeThrough",tr("Strikethrough","خط‌خورده"),"strike"],["subscript",tr("Subscript","زیرنویس"),"sub"],["superscript",tr("Superscript","بالانویس"),"sup"]].forEach(([cmd,label,glyph])=>{const b=makeButton(parent,cmd,label,glyph);b.dataset.command=cmd;});
      separator(parent);
      createColorTool(parent,tr("Text color","رنگ متن"),"foreColor","#26354e");
      createColorTool(parent,tr("Highlight","رنگ زمینه متن"),"hiliteColor","#ffe889");
      makeSelect(parent,tr("Font family","نوع قلم"),[
        {value:"",label:tr("Font","قلم")},{value:"Arial",label:"Arial"},{value:"Georgia",label:"Georgia"},{value:"Tahoma",label:"Tahoma"},{value:"Times New Roman",label:"Times New Roman"},{value:"Verdana",label:"Verdana"},{value:"monospace",label:"Monospace"}
      ],v=>{if(v)runCommand("fontName",v);},"nv-cke-font-select");
      makeSelect(parent,tr("Font size","اندازه قلم"),[
        {value:"",label:tr("Size","اندازه")},{value:"1",label:"10 px"},{value:"2",label:"13 px"},{value:"3",label:"16 px"},{value:"4",label:"18 px"},{value:"5",label:"24 px"},{value:"6",label:"32 px"},{value:"7",label:"48 px"}
      ],v=>{if(v)runCommand("fontSize",v);},"nv-cke-size-select");
      separator(parent);
      makeButton(parent,"justifyLeft",tr("Align left","چپ‌چین"),"alignLeft");
      makeButton(parent,"justifyCenter",tr("Align center","وسط‌چین"),"alignCenter");
      makeButton(parent,"justifyRight",tr("Align right","راست‌چین"),"alignRight");
      makeButton(parent,"justifyFull",tr("Justify","تراز دوطرفه"),"justify");
    }
    function addInsertToolbar(parent) {
      makeButton(parent,"insertBullet",tr("Bulleted list","فهرست نشانه‌دار"),"bullet");
      makeButton(parent,"insertNumber",tr("Numbered list","فهرست شماره‌دار"),"numbered");
      makeButton(parent,"outdent",tr("Decrease indent","کاهش تورفتگی"),"outdent");
      makeButton(parent,"indent",tr("Increase indent","افزایش تورفتگی"),"indent");
      separator(parent);
      makeButton(parent,"insertLink",tr("Link (Ctrl+K)","پیوند (Ctrl+K)"),"link");
      makeButton(parent,"unlink",tr("Remove link","حذف پیوند"),"unlink");
      makeButton(parent,"insertImage",tr("Image / upload","تصویر / بارگذاری"),"image");
      makeButton(parent,"insertMedia",tr("Embed video / media","درج ویدئو"),"video");
      makeButton(parent,"insertTable",tr("Insert table","درج جدول"),"table");
      makeButton(parent,"tableOps",tr("Table tools","ابزارهای جدول"),"more");
      separator(parent);
      makeButton(parent,"blockquote",tr("Block quote","نقل‌قول"),"quote");
      makeButton(parent,"pre",tr("Code block","بلوک کد"),"code");
      makeButton(parent,"hr",tr("Horizontal line","خط افقی"),"minus");
      makeButton(parent,"special",tr("Special character","نویسه ویژه"),"special");
      makeButton(parent,"pageBreak",tr("Page break","شکست صفحه"),"file");
    }
    function toggleSource() {
      closePopover();closeMenu();sourceMode=!sourceMode;
      if(sourceMode){source.value=surface.innerHTML;surface.hidden=true;source.hidden=false;wrap.classList.add("nv-cke-source-mode");}
      else{setSurface(source.value);source.hidden=true;surface.hidden=false;wrap.classList.remove("nv-cke-source-mode");}
      toolbar.querySelectorAll("button,select").forEach(el=>{const action=el.dataset.action;el.disabled=sourceMode&&action!=="source"&&action!=="fullscreen";});
      menuBar.querySelectorAll("button").forEach(el=>{el.disabled=sourceMode;});
      sync();updatePath();
    }
    function toggleFullscreen() {
      fullScreen=!fullScreen;wrap.classList.toggle("nv-cke-fullscreen",fullScreen);document.body.classList.toggle("nv-cke-body-fullscreen",fullScreen);
      wrap.querySelector('[data-action="fullscreen"]')?.setAttribute("aria-pressed",String(fullScreen));
      if(fullScreen)wrap.scrollIntoView({block:"nearest"}); else wrap.scrollIntoView({block:"nearest"});
    }
    function showToast(message,type) {
      const old=wrap.querySelector(".nv-cke-toast");if(old)old.remove();
      const toast=document.createElement("div");toast.className="nv-cke-toast nv-cke-toast-"+(type||"info");toast.textContent=message;wrap.append(toast);
      window.setTimeout(()=>toast.remove(),3500);
    }
    function openLinkDialog() {
      rememberRange();const sel=window.getSelection();const selected=sel?sel.toString():"";let existing=null;
      if(sel&&sel.anchorNode){let n=sel.anchorNode.nodeType===1?sel.anchorNode:sel.anchorNode.parentElement;existing=n&&n.closest?n.closest("a"):null;if(existing&&!surface.contains(existing))existing=null;}
      openDialog(existing?tr("Edit link","ویرایش پیوند"):tr("Insert link","درج پیوند"),[
        {name:"url",label:tr("URL or email","نشانی یا ایمیل"),type:"text",value:existing?existing.getAttribute("href"):"",placeholder:"https://example.com",required:true},
        {name:"text",label:tr("Link text","متن پیوند"),type:"text",value:existing?existing.textContent:selected,placeholder:tr("Describe this link","عنوان پیوند")},
        {name:"newTab",label:tr("Open in new tab","باز شدن در زبانه جدید"),type:"checkbox",value:existing?existing.target==="_blank":true}
      ],v=>{
        const url=safeUrl(v.url,false);if(!url){showToast(tr("Enter a safe http(s), mailto, tel, relative or anchor URL.","نشانی معتبر وارد کنید."),"error");return false;}
        restoreRange();surface.focus();
        if(existing&&surface.contains(existing)){existing.setAttribute("href",url);existing.textContent=v.text||url;}
        else if(window.getSelection()&&window.getSelection().toString())document.execCommand("createLink",false,url);
        else insertHtml('<a href="'+esc(url)+'"'+(v.newTab?' target="_blank" rel="noopener noreferrer"':'')+'>'+esc(v.text||url)+'</a>');
        const selNow=window.getSelection();let node=selNow&&selNow.anchorNode;if(node&&node.nodeType===3)node=node.parentElement;const a=node&&node.closest?node.closest("a"):null;
        if(a&&surface.contains(a)&&v.newTab){a.target="_blank";a.rel="noopener noreferrer";}
        afterEdit();
      });
    }
    async function uploadImage(file, alt, caption, width) {
      if (!file) return;
      if (file.size > 5 * 1024 * 1024) { showToast(tr("Images must be 5 MB or smaller.","حجم تصویر باید ۵ مگابایت یا کمتر باشد."),"error"); return; }
      if (!["image/png","image/jpeg","image/webp","image/gif"].includes(file.type)) { showToast(tr("Use a PNG, JPEG, WebP, or GIF image.","فرمت تصویر باید PNG، JPEG، WebP یا GIF باشد."),"error"); return; }
      const formData=new FormData();formData.append("upload",file,file.name);
      const form=ta.form||wrap.closest("form");
      const csrfField=form&&form.querySelector('input[name="csrfmiddlewaretoken"]');
      const cookie=document.cookie.split("; ").find(item=>item.startsWith("csrftoken="));
      const csrf=csrfField?csrfField.value:(cookie?decodeURIComponent(cookie.slice("csrftoken=".length)):"");
      try {
        const response=await fetch("/admin/editor-upload/",{method:"POST",body:formData,credentials:"same-origin",headers:csrf?{"X-CSRFToken":csrf}:{}});
        const data=await response.json().catch(()=>({}));
        if(!response.ok||!data.url)throw new Error(data.error||tr("The image could not be uploaded.","بارگذاری تصویر انجام نشد."));
        const url=safeUrl(data.url,true);if(!url)throw new Error(tr("The server returned an invalid image URL.","نشانی تصویر دریافتی معتبر نیست."));
        const img='<img src="'+esc(url)+'" alt="'+esc(alt)+'"'+(width?' width="'+width+'"':'')+' loading="lazy">';
        insertHtml("<figure>"+img+(caption.trim()?"<figcaption>"+esc(caption.trim())+"</figcaption>":"")+"</figure><p><br></p>");
        showToast(tr("Image uploaded and inserted.","تصویر بارگذاری و درج شد."),"info");
      } catch(error) { showToast(error&&error.message?error.message:tr("The image upload failed.","بارگذاری تصویر ناموفق بود."),"error"); }
    }
    function openImageDialog() {
      rememberRange();
      openDialog(tr("Insert image","درج تصویر"),[
        {name:"url",label:tr("Image URL (optional when uploading)","نشانی تصویر (در صورت بارگذاری اختیاری)"),type:"text",placeholder:"https://example.com/image.webp"},
        {name:"file",label:tr("Upload an image","بارگذاری تصویر"),type:"file",accept:"image/png,image/jpeg,image/webp,image/gif",help:tr("PNG, JPEG, WebP, or GIF · 5 MB maximum","PNG، JPEG، WebP یا GIF · حداکثر ۵ مگابایت")},
        {name:"alt",label:tr("Alternative text (accessibility)","متن جایگزین (دسترس‌پذیری)"),type:"text",placeholder:tr("Describe the image","توضیح تصویر"),required:true},
        {name:"caption",label:tr("Caption","زیرنویس"),type:"text",placeholder:tr("Optional caption","زیرنویس اختیاری")},
        {name:"width",label:tr("Width in pixels (optional)","عرض به پیکسل (اختیاری)"),type:"number",min:50,max:2000,placeholder:"600"}
      ],v=>{
        const width=Number(v.width);if(v.width&&(!Number.isFinite(width)||width<50||width>2000)){showToast(tr("Image width must be from 50 to 2000 pixels.","عرض تصویر باید بین ۵۰ تا ۲۰۰۰ پیکسل باشد."),"error");return false;}
        if(v.file){uploadImage(v.file,v.alt,v.caption||"",v.width?width:0);return true;}
        const url=safeUrl(v.url,true);if(!url){showToast(tr("Enter an image URL or choose a file to upload.","نشانی تصویر را وارد کنید یا فایلی برای بارگذاری انتخاب کنید."),"error");return false;}
        const img='<img src="'+esc(url)+'" alt="'+esc(v.alt)+'"'+(width?' width="'+width+'"':'')+' loading="lazy">';
        insertHtml("<figure>"+img+(v.caption.trim()?"<figcaption>"+esc(v.caption.trim())+"</figcaption>":"")+"</figure><p><br></p>");
      },tr("Uploaded images are decoded and re-encoded on the server before storage.","تصاویر بارگذاری‌شده در سرور رمزگشایی و بازتولید می‌شوند."));
    }
    function normalizeMediaUrl(value) {
      const raw=safeUrl(value,false);if(!raw)return "";
      try {
        const u=new URL(raw,document.baseURI);
        if(u.protocol!=="https:"||u.username||u.password||(u.port&&u.port!=="443"))return "";
        const host=u.hostname.toLowerCase();
        if(["youtu.be","www.youtu.be"].includes(host)) {
          const id=u.pathname.split("/").filter(Boolean)[0]||"";
          return /^[A-Za-z0-9_-]{6,20}$/.test(id)?"https://www.youtube-nocookie.com/embed/"+id:"";
        }
        if(["youtube.com","www.youtube.com","m.youtube.com"].includes(host)) {
          let id="";
          if(u.pathname==="/watch")id=u.searchParams.get("v")||"";
          else if(/^\/shorts\/[A-Za-z0-9_-]{6,20}\/?$/.test(u.pathname))id=u.pathname.split("/")[2];
          else if(/^\/embed\/[A-Za-z0-9_-]{6,20}\/?$/.test(u.pathname))id=u.pathname.split("/")[2];
          return /^[A-Za-z0-9_-]{6,20}$/.test(id)?"https://www.youtube-nocookie.com/embed/"+id:"";
        }
        if(host==="www.youtube-nocookie.com"&&/^\/embed\/[A-Za-z0-9_-]{6,20}\/?$/.test(u.pathname))return u.origin+u.pathname;
        if(host==="vimeo.com"||host==="www.vimeo.com") {
          const id=u.pathname.split("/").filter(Boolean)[0]||"";
          return /^[0-9]{5,12}$/.test(id)?"https://player.vimeo.com/video/"+id:"";
        }
        if(host==="player.vimeo.com"&&/^\/video\/[0-9]{5,12}\/?$/.test(u.pathname))return u.origin+u.pathname;
      } catch (_) {}
      return "";
    }
    function openMediaDialog() {
      rememberRange();
      openDialog(tr("Embed video","درج ویدئو"),[
        {name:"url",label:tr("YouTube or Vimeo URL","نشانی YouTube یا Vimeo"),type:"text",placeholder:"https://www.youtube.com/watch?v=…",required:true},
        {name:"title",label:tr("Accessible title","عنوان قابل دسترس"),type:"text",value:tr("Embedded video","ویدئوی تعبیه‌شده"),required:true},
        {name:"caption",label:tr("Caption (optional)","زیرنویس (اختیاری)"),type:"text",placeholder:tr("Video caption","زیرنویس ویدئو")}
      ],v=>{
        const url=normalizeMediaUrl(v.url);if(!url){showToast(tr("Only supported YouTube and Vimeo video URLs are allowed.","فقط نشانی معتبر و پشتیبانی‌شده YouTube یا Vimeo مجاز است."),"error");return false;}
        insertHtml('<figure><iframe src="'+esc(url)+'" title="'+esc(v.title)+'" width="560" height="315" loading="lazy" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen="allowfullscreen" sandbox="allow-scripts allow-same-origin allow-presentation" allow="autoplay; encrypted-media; fullscreen; picture-in-picture"></iframe>'+(v.caption.trim()?'<figcaption>'+esc(v.caption.trim())+'</figcaption>':'')+'</figure><p><br></p>');
      },tr("Only HTTPS YouTube and Vimeo embeds are accepted; arbitrary iframe sources are blocked.","فقط تعبیه‌سازی HTTPS برای YouTube و Vimeo پذیرفته می‌شود و iframeهای ناشناس مسدود هستند."));
    }
    function openTableDialog() {
      rememberRange();
      openDialog(tr("Insert table","درج جدول"),[
        {name:"rows",label:tr("Rows","ردیف‌ها"),type:"number",value:3,min:1,max:50,required:true},
        {name:"cols",label:tr("Columns","ستون‌ها"),type:"number",value:3,min:1,max:20,required:true},
        {name:"header",label:tr("First row is a header","ردیف اول عنوان ستون‌هاست"),type:"checkbox",value:true},
        {name:"caption",label:tr("Table caption (optional)","عنوان جدول (اختیاری)"),type:"text",placeholder:tr("Table title","عنوان جدول")}
      ],v=>{
        const rows=Number(v.rows),cols=Number(v.cols);if(!Number.isInteger(rows)||!Number.isInteger(cols)||rows<1||rows>50||cols<1||cols>20){showToast(tr("Choose 1–50 rows and 1–20 columns.","تعداد ردیف یا ستون معتبر نیست."),"error");return false;}
        let out="<table>";if(v.caption.trim())out+="<caption>"+esc(v.caption.trim())+"</caption>";out+="<tbody>";
        for(let r=0;r<rows;r++){out+="<tr>";for(let c=0;c<cols;c++){const tag=v.header&&r===0?"th":"td";out+="<"+tag+"><br></"+tag+">";}out+="</tr>";}
        out+="</tbody></table><p><br></p>";insertHtml(out);
      });
    }
    function cellContext() {
      const sel=window.getSelection();let n=sel&&sel.anchorNode;if(n&&n.nodeType===3)n=n.parentElement;
      return n&&n.closest?n.closest("td,th"):null;
    }
    function openTableOps() {
      const cell=cellContext();
      openDialog(tr("Table tools","ابزارهای جدول"),[
        {name:"action",label:tr("Operation","عملیات"),type:"select",value:"rowAfter",options:[
          {value:"rowBefore",label:tr("Insert row above","درج ردیف بالا")},{value:"rowAfter",label:tr("Insert row below","درج ردیف پایین")},{value:"deleteRow",label:tr("Delete current row","حذف ردیف جاری")},{value:"colBefore",label:tr("Insert column left","درج ستون چپ")},{value:"colAfter",label:tr("Insert column right","درج ستون راست")},{value:"deleteCol",label:tr("Delete current column","حذف ستون جاری")},{value:"deleteTable",label:tr("Delete table","حذف جدول")},{value:"mergeNext",label:tr("Merge with next cell","ادغام با خانه بعدی")},{value:"splitCell",label:tr("Split cell into two","تقسیم خانه به دو بخش")}
        ]}
      ],v=>{
        if(v.action!=="deleteTable"&&!cell){showToast(tr("Place the caret inside a table first.","ابتدا داخل جدول کلیک کنید."),"error");return false;}
        const table=cell?cell.closest("table"):null;
        if(v.action==="deleteTable"){const sel=window.getSelection();let n=sel&&sel.anchorNode;if(n&&n.nodeType===3)n=n.parentElement;const t=n&&n.closest?n.closest("table"):null;if(!t){showToast(tr("Place the caret inside a table first.","ابتدا داخل جدول کلیک کنید."),"error");return false;}t.remove();}
        else if(v.action.startsWith("row")){const row=cell.closest("tr"),idx=row.rowIndex; if(v.action==="deleteRow"){if(table.rows.length<=1){table.remove();}else row.remove();}else{const nr=table.insertRow(idx+(v.action==="rowAfter"?1:0));for(let i=0;i<row.cells.length;i++){const c=nr.insertCell();c.innerHTML="<br>";}}}
        else if(v.action.startsWith("col")){const table=cell.closest("table"),idx=cell.cellIndex;Array.from(table.rows).forEach(row=>{if(v.action==="deleteCol"){if(row.cells.length<=1)row.remove();else row.deleteCell(idx);}else{const c=row.insertCell(idx+(v.action==="colAfter"?1:0));c.innerHTML="<br>";}});if(!table.rows.length)table.remove();}
        else if(v.action==="mergeNext"){const next=cell.nextElementSibling;if(next){cell.innerHTML=(cell.innerHTML||"")+" "+(next.innerHTML||"");cell.colSpan=(cell.colSpan||1)+(next.colSpan||1);next.remove();}else showToast(tr("There is no adjacent cell to merge.","خانه مجاور برای ادغام وجود ندارد."),"info");}
        else if(v.action==="splitCell"){const clone=cell.cloneNode(true);clone.innerHTML="<br>";clone.removeAttribute("colspan");if(cell.colSpan>1)cell.colSpan-=1;cell.after(clone);}
        afterEdit();
      },tr("Select a cell first. Table structure changes apply to the current table.","ابتدا داخل خانه جدول کلیک کنید."));
    }
    function openFindReplace(replace) {
      const fields=[{name:"find",label:tr("Find text","عبارت جست‌وجو"),type:"text",required:true,placeholder:tr("Search this document","جست‌وجو در سند")}];
      if(replace)fields.push({name:"replacement",label:tr("Replace with","جایگزینی با"),type:"text",placeholder:tr("Replacement text","متن جایگزین")});
      openDialog(replace?tr("Find and replace","جست‌وجو و جایگزینی"):tr("Find in document","جست‌وجو در سند"),fields,v=>{
        const needle=v.find;if(!needle)return false;
        if(replace){let count=0;const walker=document.createTreeWalker(surface,NodeFilter.SHOW_TEXT);const nodes=[];while(walker.nextNode())nodes.push(walker.currentNode);nodes.forEach(n=>{if(n.parentElement&&n.parentElement.closest("script,style,textarea,code,pre"))return;const old=n.nodeValue;const next=old.split(needle).join(v.replacement||"");if(next!==old){count+=(old.length-next.length)/(needle.length-(v.replacement||"").length||needle.length);n.nodeValue=next;}});showToast(tr("Replacement finished.","جایگزینی انجام شد.")+" ("+Math.max(0,Math.round(count))+")","info");}
        else{const walker=document.createTreeWalker(surface,NodeFilter.SHOW_TEXT);let found=false;while(walker.nextNode()){const n=walker.currentNode,i=n.nodeValue.toLowerCase().indexOf(needle.toLowerCase());if(i>=0){const r=document.createRange();r.setStart(n,i);r.setEnd(n,i+needle.length);const s=window.getSelection();s.removeAllRanges();s.addRange(r);rememberRange();n.parentElement.scrollIntoView({block:"center",behavior:"smooth"});found=true;break;}}if(!found)showToast(tr("No matching text found.","عبارت موردنظر پیدا نشد."),"info");}
        sync();return true;
      });
    }
    function openSpecialChars() {
      const chars=["©","®","™","€","£","¥","¢","±","×","÷","≠","≤","≥","∞","√","∑","∆","π","µ","°","·","•","…","—","–","“","”","‘","’","←","→","↑","↓","✓","★","☆","§","¶","†","‡","∴","∵","↔","⇌","α","β","γ","δ","λ","ω"];
      openDialog(tr("Insert special character","درج نویسه ویژه"),[{name:"char",label:tr("Character","نویسه"),type:"select",value:"©",options:chars.map(c=>({value:c,label:c+"  "+c.codePointAt(0).toString(16).toUpperCase()}))}],v=>{insertHtml(esc(v.char));});
    }
    function openWordCount() {
      const txt=textOf(sourceMode?source.value:surface.innerHTML),words=txt?txt.split(/\s+/).filter(Boolean).length:0,paragraphs=(txt.match(/\n/g)||[]).length+1;
      openDialog(tr("Document statistics","آمار سند"),[
        {name:"words",label:tr("Words","کلمات"),type:"text",value:String(words)},
        {name:"characters",label:tr("Characters (including spaces)","نویسه‌ها با فاصله"),type:"text",value:String(txt.length)},
        {name:"paragraphs",label:tr("Paragraph breaks (approx.)","پاراگراف‌ها (تقریبی)"),type:"text",value:String(paragraphs)}
      ],()=>true);
    }
    function openHelp() {
      openDialog(tr("Keyboard shortcuts","میان‌برهای صفحه‌کلید"),[
        {name:"s1",label:"Bold",type:"text",value:"Ctrl + B"},
        {name:"s2",label:"Italic",type:"text",value:"Ctrl + I"},
        {name:"s3",label:"Underline",type:"text",value:"Ctrl + U"},
        {name:"s4",label:"Insert link",type:"text",value:"Ctrl + K"},
        {name:"s5",label:"Undo / Redo",type:"text",value:"Ctrl + Z / Ctrl + Y"},
        {name:"s6",label:"Select all",type:"text",value:"Ctrl + A"},
        {name:"s7",label:"Editor help",type:"text",value:"Alt + 0"}
      ],()=>true,tr("Shortcuts work while the editing surface has focus.","این میان‌برها هنگام تمرکز روی محیط ویرایش فعال‌اند."));
    }
    function downloadHtml() {
      const blob=new Blob(["<!doctype html><html><head><meta charset=\"utf-8\"><title>Document</title></head><body>",clean(sourceMode?source.value:surface.innerHTML),"</body></html>"],{type:"text/html;charset=utf-8"});
      const url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download="nebula-document.html";a.click();URL.revokeObjectURL(url);
    }
    function importHtml() {
      const input=document.createElement("input");input.type="file";input.accept=".html,.htm,.txt,text/html,text/plain";
      input.addEventListener("change",()=>{const f=input.files&&input.files[0];if(!f)return;if(f.size>2*1024*1024){showToast(tr("Files must be smaller than 2 MB.","حجم فایل باید کمتر از ۲ مگابایت باشد."),"error");return;}const reader=new FileReader();reader.onload=()=>{setSurface(asHtml(String(reader.result||"")));showToast(tr("Content imported. Review it before saving.","محتوا وارد شد؛ پیش از ذخیره آن را بررسی کنید."),"info");};reader.readAsText(f);});input.click();
    }
    function insertHtmlFromMenu(markup) { restoreRange();surface.focus();document.execCommand("insertHTML",false,markup);afterEdit(); }
    function addBalloonToolbar() {
      [["bold","Bold","bold"],["italic","Italic","italic"],["underline","Underline","underline"],["insertLink","Link","link"]].forEach(([a,l,g])=>{
        const b=document.createElement("button");b.type="button";b.className="nv-cke-tool";b.title=l;b.setAttribute("aria-label",l);b.innerHTML=icon(g);b.addEventListener("mousedown",e=>{rememberRange();e.preventDefault();});b.addEventListener("click",()=>runCommand(a));floatBar.append(b);
      });
      wrap.append(floatBar);
    }
    function scan(node) { if(node instanceof HTMLTextAreaElement)enhance(node); if(node.querySelectorAll)node.querySelectorAll("textarea").forEach(enhance); }
    surface.innerHTML=asHtml(ta.value);html=surface.innerHTML;
    buildMenus();addFormattingToolbar(toolbarTop);addInsertToolbar(toolbarBottom);
    makeButton(toolbarBottom,"find",tr("Find","جست‌وجو"),"search");
    makeButton(toolbarBottom,"removeFormat",tr("Clear formatting","پاک‌کردن قالب‌بندی"),"refresh");
    makeButton(toolbarBottom,"source",tr("Edit HTML source","ویرایش کد HTML"),"source");
    makeButton(toolbarBottom,"showBlocks",tr("Show block boundaries","نمایش مرز بلوک‌ها"),"ruler");
    makeButton(toolbarBottom,"fullscreen",tr("Fullscreen","تمام‌صفحه"),"maximize");
    toolbar.append(toolbarTop,toolbarBottom);
    addBalloonToolbar();
    const host=document.createElement("div");host.className="nv-cke-main";host.append(surface,source);
    wrap.append(menuBar,toolbar,host,status,popover,modalRoot);
    ta.insertAdjacentElement("afterend",wrap);ta.classList.add("nv-cke-original");ta.setAttribute("aria-hidden","true");ta.tabIndex=-1;
    const wasRequired=ta.required;ta.required=false;
    const form=ta.form||ta.closest("form");
    if(form) {
      form.addEventListener("submit",e=>{
        sync();
        if(wasRequired&&!textOf(ta.value)){e.preventDefault();surface.hidden=false;source.hidden=true;sourceMode=false;surface.focus();surface.setAttribute("aria-invalid","true");showToast(tr("This field is required.","این فیلد الزامی است."),"error");}
      });
    }
    surface.addEventListener("input",()=>{if(sourceMode)return;afterEdit();surface.removeAttribute("aria-invalid");});
    source.addEventListener("input",sync);
    surface.addEventListener("keyup",()=>{rememberRange();updatePath();updateActiveButtons();});
    surface.addEventListener("mouseup",()=>{rememberRange();updatePath();updateActiveButtons();showBalloonIfNeeded();});
    surface.addEventListener("focus",()=>{rememberRange();updatePath();});
    document.addEventListener("selectionchange",()=>{if(document.activeElement===surface||surface.contains(document.activeElement)){rememberRange();updatePath();updateActiveButtons();}});
    surface.addEventListener("keydown",e=>{
      const mod=e.ctrlKey||e.metaKey;
      if(mod&&e.key.toLowerCase()==="k"){e.preventDefault();rememberRange();openLinkDialog();}
      else if(mod&&e.key.toLowerCase()==="b"){e.preventDefault();runCommand("bold");}
      else if(mod&&e.key.toLowerCase()==="i"){e.preventDefault();runCommand("italic");}
      else if(mod&&e.key.toLowerCase()==="u"){e.preventDefault();runCommand("underline");}
      else if(e.altKey&&e.key==="0"){e.preventDefault();openHelp();}
      else if(e.key==="Tab"&&cellContext()){e.preventDefault();const cell=cellContext(),next=e.shiftKey?cell.previousElementSibling:cell.nextElementSibling;if(next){const r=document.createRange();r.selectNodeContents(next);r.collapse(true);const s=window.getSelection();s.removeAllRanges();s.addRange(r);}else if(!e.shiftKey){const row=cell.parentElement,table=row.closest("table"),newRow=table.insertRow();for(let i=0;i<row.cells.length;i++){const c=newRow.insertCell();c.innerHTML="<br>";}const r=document.createRange();r.selectNodeContents(newRow.cells[0]);r.collapse(true);const s=window.getSelection();s.removeAllRanges();s.addRange(r);}rememberRange();}
    });
    surface.addEventListener("paste",e=>{
      const data=(e.clipboardData||window.clipboardData);if(!data)return;
      const htmlData=data.getData("text/html");if(htmlData){e.preventDefault();insertHtmlFromMenu(clean(htmlData));return;}
      const plain=data.getData("text/plain");if(plain&&plain.indexOf("\n")>=0){e.preventDefault();insertHtmlFromMenu(plain.split(/\r?\n/).map(l=>"<p>"+esc(l||"")+"</p>").join(""));return;}
    });
    surface.addEventListener("dragover",e=>{if(e.dataTransfer&&Array.from(e.dataTransfer.types||[]).includes("Files")){e.preventDefault();wrap.classList.add("nv-cke-dragover");}});
    surface.addEventListener("dragleave",()=>wrap.classList.remove("nv-cke-dragover"));
    surface.addEventListener("drop",e=>{wrap.classList.remove("nv-cke-dragover");if(e.dataTransfer&&Array.from(e.dataTransfer.files||[]).length){e.preventDefault();showToast(tr("Use Insert image to add an image URL; direct uploads need a server adapter.","برای درج تصویر از گزینه تصویر و نشانی آن استفاده کنید."),"info");}});
    document.addEventListener("click",e=>{if(!wrap.contains(e.target)){closePopover();closeMenu();floatBar.hidden=true;}});
    document.addEventListener("keydown",e=>{if(e.key==="Escape"){closePopover();closeMenu();if(currentDialog)hideDialog();}});
    window.addEventListener("resize",()=>{closePopover();});
    function showBalloonIfNeeded() {
      const sel=window.getSelection();if(!sel||sel.isCollapsed||!surface.contains(sel.anchorNode)){floatBar.hidden=true;return;}
      const r=sel.getRangeAt(0).getBoundingClientRect();if(!r.width&&!r.height){floatBar.hidden=true;return;}
      floatBar.hidden=false;floatBar.style.left=Math.max(8,Math.min(wrap.clientWidth-190,r.left-wrap.getBoundingClientRect().left))+"px";floatBar.style.top=Math.max(0,r.top-wrap.getBoundingClientRect().top-42)+"px";
    }
    function updatePathSafe(){updatePath();}
    sync();updatePathSafe();
  }

  function init() {
    const scan = node => {
      if (node instanceof HTMLTextAreaElement) {
        if (node.matches(ELIGIBLE) && !node.matches(EXCLUDED)) enhance(node);
      } else if (node && node.querySelectorAll) {
        node.querySelectorAll(ELIGIBLE).forEach(ta=>{if(!ta.matches(EXCLUDED))enhance(ta);});
      }
    };
    scan(document);
    const observer=new MutationObserver(records=>records.forEach(r=>r.addedNodes.forEach(n=>{if(n.nodeType===1)scan(n);})));
    observer.observe(document.documentElement,{childList:true,subtree:true});
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init,{once:true});else init();
})();