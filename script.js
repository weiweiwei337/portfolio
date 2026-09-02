const data = window.PORTFOLIO_DATA || [];
const bySlug = Object.fromEntries(data.map((section) => [section.slug, section]));
const allItems = data.flatMap((section) => section.items.map((item) => ({ ...item, section: section.title })));

const impactStats = [
  { value: "3.21M", label: "FFF Campaign Exposure", type: "Campaign-level" },
  { value: "1.58M", label: "IFK Göteborg Exposure", type: "Campaign-level" },
  { value: "513K+", label: "Philadelphia Phillies KV Exposure", type: "Visual-linked" },
  { value: "179K", label: "FCK Campaign Exposure", type: "Campaign-level" },
  { value: "20+", label: "Static Visuals", type: "Output" },
  { value: "7-8", label: "Content Waves", type: "Output" },
  { value: "5", label: "KOL Activation", type: "Blue Garden" },
];

const heroPick =
  bySlug.france?.items.find((item) => item.title.includes("2026 kv")) ||
  bySlug.usa?.items.find((item) => item.title.includes("横版")) ||
  allItems.find((item) => item.media !== "video");

document.getElementById("heroImage").src = heroPick.src;
document.getElementById("heroImage").alt = heroPick.title;

const nav = document.getElementById("nav");
nav.innerHTML = data.map((section) => `<a href="#${section.slug}">${section.title}</a>`).join("");

document.getElementById("impactGrid").innerHTML = impactStats
  .map(
    (stat) => `
      <div class="impact-card">
        <strong>${stat.value}</strong>
        <span>${stat.label}</span>
        <small>${stat.type}</small>
      </div>
    `,
  )
  .join("");

function mediaCard(item) {
  if (item.media === "video") {
    return `
      <article class="media-card video-card">
        <video src="${item.src}" muted loop playsinline preload="none" controls></video>
        <div class="media-caption">
          <strong>${item.title}</strong>
          <span>Motion social content</span>
        </div>
      </article>
    `;
  }

  return `
    <button class="media-card image-card" data-src="${item.src}" data-title="${item.title}" data-section="${item.section || ""}">
      <img src="${item.src}" alt="${item.title}" loading="lazy">
      <span class="caption">${item.title}</span>
    </button>
  `;
}

function metricCards(section) {
  if (!section.metrics?.length) return "";
  return `
    <div class="metric-strip">
      ${section.metrics
        .map(
          (metric) => `
            <div class="metric-card">
              <small>${metric.type}</small>
              <strong>${metric.value}</strong>
              <span>${metric.label}</span>
              <em>${metric.note}</em>
            </div>
          `,
        )
        .join("")}
    </div>
  `;
}

function folderLabel(folder, section) {
  if (!folder) return section.slug === "social" ? "Motion Works" : "Key Visuals";
  const lower = folder.toLowerCase();
  if (folder.includes("蓝军广告")) return "Blue Garden Ads";
  if (folder.includes("进店线下应用")) return "Retail Applications";
  if (folder.includes("社媒视频")) return "Motion Works";
  if (lower.includes("logo")) return "Logo Assets";
  return folder.split("/").pop();
}

function groupedGallery(section) {
  const groups = new Map();
  section.items.forEach((item) => {
    const key = item.folder || "";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(item);
  });

  return [...groups.entries()]
    .map(([folder, items]) => {
      const cards = items.map((item) => mediaCard({ ...item, section: section.title })).join("");
      return `
        <div class="media-group">
          <h3>${folderLabel(folder, section)}</h3>
          <div class="gallery">${cards}</div>
        </div>
      `;
    })
    .join("");
}

function renderSpotlight() {
  const france = bySlug.france?.items.find((item) => item.title.includes("2027 kv赞助")) || bySlug.france?.items[0];
  const usa = bySlug.usa?.items.find((item) => item.title.includes("横版")) || bySlug.usa?.items[0];
  const sweden = bySlug.sweden?.items[0];

  document.getElementById("spotlight").innerHTML = `
    <div class="spotlight-equal">
      ${[france, usa, sweden]
        .filter(Boolean)
        .map(
          (item) => `
            <button class="spotlight-card image-card" data-src="${item.src}" data-title="${item.title}" data-section="${item.section || ""}">
              <img src="${item.src}" alt="${item.title}">
              <span>${item.title}</span>
            </button>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderSections() {
  document.getElementById("sections").innerHTML = data
    .map((section) => {
      return `
        <section class="portfolio-section" id="${section.slug}">
          <div class="section-inner">
            <div class="section-head">
              <div>
                <p class="section-label">${section.eyebrow}</p>
                <h2>${section.title}</h2>
                <div class="countline">${section.count} media items</div>
              </div>
              <p>${section.summary}</p>
            </div>
            ${metricCards(section)}
            ${groupedGallery(section)}
          </div>
        </section>
      `;
    })
    .join("");
}

renderSpotlight();
renderSections();

const lightbox = document.getElementById("lightbox");
const lightboxImage = document.getElementById("lightboxImage");
const lightboxCaption = document.getElementById("lightboxCaption");

function openLightbox(button) {
  lightboxImage.src = button.dataset.src;
  lightboxImage.alt = button.dataset.title;
  lightboxCaption.textContent = [button.dataset.section, button.dataset.title].filter(Boolean).join(" / ");
  lightbox.setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
}

function closeLightbox() {
  lightbox.setAttribute("aria-hidden", "true");
  document.body.style.overflow = "";
  lightboxImage.removeAttribute("src");
}

document.addEventListener("click", (event) => {
  const card = event.target.closest(".image-card");
  if (card) openLightbox(card);
  if (event.target.matches(".lightbox-close") || event.target === lightbox) closeLightbox();
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeLightbox();
});
