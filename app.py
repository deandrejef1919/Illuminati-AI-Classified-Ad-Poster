import streamlit as st
import pandas as pd
import textwrap
import re
from typing import List, Dict, Any
import datetime
import json

# ---------- App Config ----------
st.set_page_config(
    page_title="Illuminati AI — Free Classified Ad Poster",
    page_icon="🔺",
    layout="wide"
)

# ---------- Session Defaults ----------
if "sites" not in st.session_state:
    st.session_state["sites"] = []  # will be populated by upload or code
if "history" not in st.session_state:
    st.session_state["history"] = []  # log of postings
if "variants" not in st.session_state:
    st.session_state["variants"] = []
if "ad_saved" not in st.session_state:
    st.session_state["ad_saved"] = None
if "campaign" not in st.session_state:
    st.session_state["campaign"] = []
if "zap_url" not in st.session_state:
    st.session_state["zap_url"] = ""
if "admin_authenticated" not in st.session_state:
    st.session_state["admin_authenticated"] = False

# ---------- Default Sites (if none loaded) ----------
PRIMARY_SITES: List[Dict[str, Any]] = [
    {"name":"Craigslist","region":"Global/US","category":"General","needs_account":True,"url":"https://www.craigslist.org","notes":"Local posting; manual; strict rules."},
    {"name":"Facebook Marketplace","region":"Global","category":"General","needs_account":True,"url":"https://www.facebook.com/marketplace","notes":"High reach; FB account required."},
    {"name":"Locanto","region":"Global","category":"General","needs_account":True,"url":"https://www.locanto.com","notes":"Many city-based pages; text + images."},
    {"name":"ClassifiedAds","region":"US","category":"General","needs_account":True,"url":"https://www.classifiedads.com","notes":"Free general classifieds."},
    {"name":"OfferUp","region":"US","category":"Local Apps","needs_account":True,"url":"https://offerup.com","notes":"Mobile-first local marketplace."},
]

if not st.session_state["sites"]:
    st.session_state["sites"] = PRIMARY_SITES.copy()

# ---------- Styles ----------
st.markdown("""
<style>
body, .stApp { background: #050506; color: #f2f2f2; }

/* Sidebar / logo area */
.sidebar-title {
  text-align:center;
  color:#f5d76e;
  margin: .4rem 0 1rem;
  letter-spacing:.2em;
  text-transform:uppercase;
  font-weight:800;
}
.sidebar-subtle-glow {
  padding: 0.4rem 0.2rem 0.6rem 0.2rem;
  border-radius: 18px;
  background: radial-gradient(circle at top, rgba(245,215,110,0.18), rgba(5,5,6,0.6));
  box-shadow: 0 0 20px rgba(245,215,110,0.25), 0 0 40px rgba(10,0,0,0.45);
}

/* Cards / main titles */
.ill-card {
  border:1px solid rgba(245,215,110,.25);
  border-radius:12px;
  padding:14px;
  background: radial-gradient(circle at top, #121212, #060606);
  box-shadow: 0 0 10px rgba(245,215,110,.12);
}
.ill-title {
  font-size:1.8rem;
  text-align:center;
  color:#f5d76e;
  text-shadow: 0 0 6px rgba(245,215,110,.55), 0 0 12px rgba(155,17,30,.45);
  font-weight:800;
  letter-spacing:.16em;
  text-transform:uppercase;
}
.war-red {
  color:#e50914;
  text-shadow: 0 0 8px rgba(229,9,20,.6);
}
.center { text-align:center; }

hr {
  border: none;
  border-top: 1px solid rgba(245,215,110,.22);
  margin: 0.75rem 0 1rem;
}

/* Buttons */
div.stButton > button {
  border-radius:999px;
  border:1px solid #f5d76e;
  background:linear-gradient(135deg,#9b111e,#5c020b);
  color:#fff;
  font-weight:700;
  box-shadow:0 0 14px rgba(155,17,30,.6);
}
div.stDownloadButton > button {
  border-radius:999px;
  border:1px solid #f5d76e;
  background:linear-gradient(135deg,#4e3d0f,#251f09);
  color:#fff;
  font-weight:700;
}

/* Footer */
.footer {
  text-align:center;
  color:#aaa;
  opacity:.9;
  margin-top:1.5rem;
  padding-top:.7rem;
  border-top:1px solid rgba(245,215,110,.2);
  font-size:.85rem;
}
.small-note { color:#bbb; font-size:.9rem; }
</style>
""", unsafe_allow_html=True)

# ---------- Copy Helpers ----------
EMO_TRIGGERS = ["secret","finally","new","weird","shocking","hidden","proven","guarantee","instantly","limited","exclusive","today","now","fast","breakthrough","odd"]
CTA_PHRASES = ["click here","tap here","join now","buy now","order now","get started","sign up","enroll now","start now","act now","claim","grab"]

MASTER_STYLES = {
    "Gary Halbert": "raw, emotional hooks (greed/fear/curiosity), short punchy lines, story lead-ins",
    "David Ogilvy": "benefit-first, specific proof, facts, and strong subheads",
    "Dan Kennedy": "no-BS direct response, deadlines, risk reversal, clear offer",
    "Claude Hopkins": "self-interest, testable claims, unique mechanism/USP",
    "Joe Sugarman": "slippery-slide curiosity, sensory detail, axioms of trust",
    "Eugene Schwartz": "awareness stages aligned to market desire, breakthrough promise",
    "John Carlton": "killer hooks, urgency, vivid storytelling, exclusivity",
    "Robert Bly": "4 U's (Urgent, Unique, Useful, Ultra-specific), long-form structure",
    "Neville Medhora": "simple, scannable, problem→solution→proof",
    "Joanna Wiebe": "voice-of-customer, message mining, test-ready copy",
    "Hybrid Mix": "blend of the above tuned to conversion",
}

def analyze_copy_score(text: str) -> Dict[str, float]:
    if not text.strip():
        return {"Score": 0, "Length": 0, "Emotion": 0, "Structure": 0, "CTA": 0, "Specificity": 0}
    t = text.lower()
    words = re.findall(r"\w+", text)
    n = len(words)
    length = 20 if n < 80 else 60 if n <= 1500 else 50
    emotion = min(sum(1 for k in EMO_TRIGGERS if k in t)/10,1)*100
    structure = min(sum(1 for k in ["attention","interest","desire","action","problem","agitate","solution","guarantee","bonus"] if k in t)/6,1)*100
    cta = min(sum(1 for k in CTA_PHRASES if k in t)/3,1)*100
    specificity = min(
        sum(bool(re.search(r"\d|\$|\d+%", text)))
        + sum(1 for k in ["day","days","week","weeks","month","months"] if k in t),
        5
    )/5*100
    score = round(0.2*length + 0.25*emotion + 0.2*structure + 0.15*cta + 0.2*specificity,1)
    return {
        "Score":score,
        "Length":float(length),
        "Emotion":round(emotion,1),
        "Structure":round(structure,1),
        "CTA":round(cta,1),
        "Specificity":round(specificity,1)
    }

def make_variants(product: str, benefit: str, audience: str, master: str) -> List[Dict[str, str]]:
    a = audience.strip() or "someone who needs this"
    b = benefit.strip() or "get real results without the struggle"
    short_b = b.split("(")[0].strip()
    h = []
    h.append(f"Finally: {product} That Helps You {short_b.capitalize()} — Without The Struggle")
    h.append(f"How {a.capitalize()} Can {short_b} with {product}")
    h.append(f"{product}: The “{short_b}” Shortcut You Can Start Using Today")
    h.append(f"Do You Make These Mistakes When Trying to {short_b}?")
    h.append(f"The Hidden Shortcut to {short_b} No One Told You About")
    body = textwrap.dedent(f"""
    [{master}-inspired tone – {MASTER_STYLES.get(master,'conversion-focused')}]

    ATTENTION
    If you're {a}, you're not alone. Most attempts to {short_b.lower()} fail because of confusing advice and copy that doesn't speak to what you actually want.

    INTEREST
    **{product}** is built to change that. It leads with the one thing you care about: {short_b.lower()} (backed by a clear, simple path).

    DESIRE
    • {short_b}
    • Save time and guesswork
    • See real progress you can feel

    ACTION
    Click to get started now. Limited attention = limited action. Act while it’s top of mind.
    """).strip()
    return [{"headline": x, "body": body} for x in h]

def export_ads(ads: List[Dict[str,str]], fmt: str="csv") -> bytes:
    df = pd.DataFrame(ads)
    if fmt=="csv":
        return df.to_csv(index=False).encode("utf-8")
    if fmt=="md":
        md = ["# Classified Ads", ""]
        for i,row in df.iterrows():
            md += [
                f"## Ad {i+1}",
                f"**Headline:** {row.get('headline','')}",
                "",
                row.get("body",""),
                ""
            ]
        return "\n".join(md).encode("utf-8")
    html = ["<html><body><h1>Classified Ads</h1>"]
    for i,row in df.iterrows():
        html += [
            f"<h2>Ad {i+1}</h2>",
            f"<p><strong>Headline:</strong> {row.get('headline','')}</p>",
            f"<pre>{row.get('body','')}</pre>",
            "<hr/>"
        ]
    html.append("</body></html>")
    return "\n".join(html).encode("utf-8")

def render_footer():
    st.markdown(
        """
        <div class="footer">
        © 2025 <strong>DeAndre Jefferson</strong><br/>
        Strategic Copy, AI, and Influence Engineering.<br/>
        Built with Python + Streamlit + OpenAI + Gemini + Claude (Anthropic).
        </div>
        """,
        unsafe_allow_html=True
    )

# ---------- Admin Login Page ----------
def admin_login_page():
    st.markdown('<div class="ill-card">', unsafe_allow_html=True)
    st.markdown('<div class="ill-title">ADMIN <span class="war-red">ACCESS</span></div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.write("")
    st.write("This control panel is reserved for the Illuminati AI Classified Ad **War Room** administrator.")

    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        with st.form("admin_login_form"):
            username = st.text_input("Username", "")
            password = st.text_input("Password", "", type="password")
            submit = st.form_submit_button("🔐 Enter War Room")

        if submit:
            # Recommended: set ADMIN_PASSWORD in Streamlit Secrets.
            secret_pwd = st.secrets.get("ADMIN_PASSWORD", "IlluminatiWarRoom!")
            valid_user = username.strip().lower() in {"deandre", "deandre jefferson"}
            valid_pass = password == secret_pwd
            if valid_user and valid_pass:
                st.session_state["admin_authenticated"] = True
                st.success("Access granted. Loading your War Room...")
                st.rerun()
            else:
                st.error("Access denied. Check your credentials.")

    render_footer()

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown('<div class="sidebar-subtle-glow">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-title">🔺 ILLUMINATI AI</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if not st.session_state["admin_authenticated"]:
        st.caption("Admin login required to access the Classified Ad War Room.")
        page = None
    else:
        st.markdown("**Free Classified Ad Poster**")
        st.caption("Compose once → post everywhere (safely).")

        page = st.radio(
            "Navigation",
            [
                "Compose & Variants",
                "Sites & Posting",
                "Campaign Tracker",
                "Exports",
                "Add/Manage Sites",
                "Settings",
            ],
            index=0
        )

        if st.button("🔓 Log out"):
            st.session_state["admin_authenticated"] = False
            st.rerun()

# ---------- If Not Logged In: Show Admin Login ----------
if not st.session_state["admin_authenticated"]:
    admin_login_page()
    st.stop()

# ---------- Pages (only when authenticated) ----------

if page == "Compose & Variants":
    st.markdown('<div class="ill-card">', unsafe_allow_html=True)
    st.markdown('<div class="ill-title">CLASSIFIED AD <span class="war-red">WAR ROOM</span></div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.write("")

    col1, col2 = st.columns([1.2,1])
    with col1:
        st.subheader("Ad Brief")
        product = st.text_input("Offer / Product Name", "")
        audience = st.text_input("Audience (e.g., busy parents who want natural solutions)", "")
        benefit = st.text_input("Single Biggest Benefit", "")
        cta = st.text_input("CTA (e.g., Click here to get started)", "Click here to get started")
        master = st.selectbox("Master Style", list(MASTER_STYLES.keys()), index=0)
        body_extra = st.text_area("Short Description / Support (optional)", "")

        if st.button("⚡ Generate Variants"):
            if not product or not benefit:
                st.error("Please add at least product and benefit.")
            else:
                variants = make_variants(product, benefit, audience, master)
                if body_extra.strip():
                    for v in variants:
                        v["body"] += "\n\n" + body_extra.strip()
                st.session_state["variants"] = variants
                st.session_state["ad_saved"] = {
                    "product": product,
                    "audience": audience,
                    "benefit": benefit,
                    "cta": cta,
                    "master": master,
                    "body_extra": body_extra,
                    "variants": variants,
                }
                st.success(f"Generated {len(variants)} variants.")

    with col2:
        st.subheader("Quality Heuristic")
        sample = st.text_area("Paste ad to analyze (optional)", height=220)
        if st.button("🔍 Analyze"):
            sc = analyze_copy_score(sample or "")
            st.metric("Overall Score", f"{sc['Score']} / 100")
            st.write(
                f"Length: {sc['Length']:.1f} | Emotion: {sc['Emotion']:.1f} | "
                f"Structure: {sc['Structure']:.1f} | CTA: {sc['CTA']:.1f} | "
                f"Specificity: {sc['Specificity']:.1f}"
            )
        st.caption("Tip: Mention specific numbers, timeframes, and add a clear CTA link for better scores.")

    st.markdown("---")
    st.subheader("Your Variants")
    if not st.session_state["variants"]:
        st.info("Generate variants above. They’ll appear here.")
    else:
        for i, v in enumerate(st.session_state["variants"], start=1):
            with st.expander(f"Variant {i}: {v['headline'][:80]}"):
                st.markdown(f"**Headline:** {v['headline']}")
                st.text(v["body"])

    render_footer()

elif page == "Sites & Posting":
    st.markdown('<div class="ill-title center">POSTING HUB</div>', unsafe_allow_html=True)
    st.write("Choose a site, open the posting page, and paste a variant. Track your post status below.")
    st.caption("Note: Most sites require a login and block automation. This flow keeps you compliant and fast.")

    colf1, colf2, colf3 = st.columns(3)
    with colf1:
        region = st.selectbox(
            "Filter by Region",
            ["All"] + sorted({s.get("region","") for s in st.session_state["sites"] if s.get("region")})
        )
    with colf2:
        category = st.selectbox(
            "Filter by Category",
            ["All"] + sorted({s.get("category","") for s in st.session_state["sites"] if s.get("category")})
        )
    with colf3:
        search = st.text_input("Search by name", "")

    rows = st.session_state["sites"]
    if region != "All":
        rows = [r for r in rows if r.get("region") == region]
    if category != "All":
        rows = [r for r in rows if r.get("category") == category]
    if search.strip():
        term = search.lower().strip()
        rows = [r for r in rows if term in r.get("name","").lower()]

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df[["name","region","category","needs_account","url","notes"]], use_container_width=True)
    else:
        st.info("No sites match your filters.")

    st.markdown("---")
    st.subheader("Quick Post & Log")
    colp1, colp2 = st.columns([1,1])
    with colp1:
        site_name = st.selectbox("Site", [r["name"] for r in rows]) if rows else None
        open_url = None
        if rows and site_name:
            for r in rows:
                if r["name"] == site_name:
                    open_url = r["url"]
                    break
        if open_url:
            st.link_button("🔗 Open Posting Site", open_url, help="Opens the site in a new tab")
        note = st.text_input("Note (e.g., city/section used)", "")
        posted_link = st.text_input("Live Ad Link (after posting)", "")
        if st.button("✅ Log Posting"):
            if site_name:
                st.session_state["history"].append({
                    "time": datetime.datetime.utcnow().isoformat()[:19],
                    "site": site_name,
                    "note": note,
                    "link": posted_link
                })
                st.success("Logged.")
            else:
                st.error("Select a site first.")

    with colp2:
        st.write("Paste your chosen variant for quick copy:")
        if st.session_state.get("variants"):
            sel = st.selectbox(
                "Choose Variant",
                [f"Variant {i+1}" for i in range(len(st.session_state['variants']))]
            )
            idx = int(sel.split()[-1]) - 1
            v = st.session_state["variants"][idx]
            pre = f"HEADLINE:\n{v['headline']}\n\nBODY:\n{v['body']}"
            st.text_area("Copy Block", value=pre, height=240)
        else:
            st.info("No variants yet. Go to Compose & Variants.")

    st.markdown("---")
    st.subheader("Posting History (session)")
    if st.session_state["history"]:
        st.dataframe(pd.DataFrame(st.session_state["history"]), use_container_width=True)
    else:
        st.info("Nothing logged yet.")

    render_footer()

elif page == "Campaign Tracker":
    st.markdown('<div class="ill-title center">CAMPAIGN TRACKER</div>', unsafe_allow_html=True)
    st.caption("Lightweight analytics: track impressions, clicks, leads/sales, revenue by site.")

    with st.form("track_form"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            site = st.selectbox("Site", [s["name"] for s in st.session_state["sites"]])
        with col2:
            impressions = st.number_input("Impressions", min_value=0, step=1, value=0)
            clicks = st.number_input("Clicks", min_value=0, step=1, value=0)
        with col3:
            leads = st.number_input("Leads", min_value=0, step=1, value=0)
            sales = st.number_input("Sales", min_value=0, step=1, value=0)
        with col4:
            revenue = st.number_input("Revenue ($)", min_value=0.0, step=1.0, value=0.0)
        submitted = st.form_submit_button("➕ Add Snapshot")

    if submitted:
        epc = (revenue / clicks) if clicks > 0 else 0.0
        conv_rate = (sales / clicks * 100) if clicks > 0 else 0.0
        st.session_state["campaign"].append({
            "time": datetime.datetime.utcnow().isoformat()[:19],
            "site": site,
            "impressions": impressions,
            "clicks": clicks,
            "leads": leads,
            "sales": sales,
            "revenue": revenue,
            "EPC": round(epc,2),
            "Conv%": round(conv_rate,2)
        })
        st.success("Snapshot added.")

    if st.session_state["campaign"]:
        st.dataframe(pd.DataFrame(st.session_state["campaign"]), use_container_width=True)
    else:
        st.info("No snapshots yet.")

    render_footer()

elif page == "Exports":
    st.markdown('<div class="ill-title center">EXPORTS</div>', unsafe_allow_html=True)
    st.caption("Download your variants and/or posting history for records or 3rd-party tools.")

    if not st.session_state["variants"]:
        st.info("No variants yet. Generate some first.")
    else:
        ads = st.session_state["variants"]
        csv_bytes = export_ads(ads, "csv")
        md_bytes = export_ads(ads, "md")
        html_bytes = export_ads(ads, "html")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button("⬇️ Variants (CSV)", csv_bytes, "classified_variants.csv", "text/csv")
        with col2:
            st.download_button("⬇️ Variants (Markdown)", md_bytes, "classified_variants.md", "text/markdown")
        with col3:
            st.download_button("⬇️ Variants (HTML)", html_bytes, "classified_variants.html", "text/html")

    st.markdown("---")
    st.subheader("Posting History Export")
    if st.session_state["history"]:
        hist_df = pd.DataFrame(st.session_state["history"])
        st.download_button(
            "⬇️ History (CSV)",
            hist_df.to_csv(index=False).encode("utf-8"),
            "posting_history.csv",
            "text/csv"
        )
    else:
        st.info("No posting history yet.")

    render_footer()

elif page == "Add/Manage Sites":
    st.markdown('<div class="ill-title center">SITES DIRECTORY</div>', unsafe_allow_html=True)
    st.caption("Add your own sites or load the 100+ site JSON you created for full firepower.")

    st.markdown("### Current Sites")
    if st.session_state["sites"]:
        st.dataframe(pd.DataFrame(st.session_state["sites"]), use_container_width=True)
    else:
        st.info("No sites loaded yet.")

    st.markdown("---")
    st.subheader("Add a Site (session only)")
    with st.form("add_site"):
        name = st.text_input("Site Name", "")
        region = st.text_input("Region (e.g., US, LATAM, SE Asia, Europe)", "")
        category = st.selectbox("Category", ["General","Local Apps","Services","Real Estate","Pets","Jobs"])
        needs_account = st.checkbox("Needs account/login", value=True)
        url = st.text_input("Posting or Home URL", "")
        notes = st.text_input("Notes", "")
        if st.form_submit_button("➕ Add"):
            if not name or not url:
                st.error("Name and URL required.")
            else:
                st.session_state["sites"].append({
                    "name": name,
                    "region": region or "Global",
                    "category": category,
                    "needs_account": needs_account,
                    "url": url,
                    "notes": notes
                })
                st.success("Added.")

    st.markdown("---")
    st.subheader("Save/Load Sites (JSON)")
    colx, coly = st.columns(2)
    with colx:
        sites_bytes = json.dumps(st.session_state["sites"], indent=2).encode("utf-8")
        st.download_button(
            "💾 Download sites.json",
            data=sites_bytes,
            file_name="sites.json",
            mime="application/json"
        )
    with coly:
        up = st.file_uploader("Upload sites.json", type=["json"])
        if up is not None:
            try:
                st.session_state["sites"] = json.loads(up.read().decode("utf-8"))
                st.success("Sites loaded.")
            except Exception as e:
                st.error(f"Invalid JSON: {e}")

    render_footer()

elif page == "Settings":
    st.markdown('<div class="ill-title center">SETTINGS</div>', unsafe_allow_html=True)
    st.caption("Webhooks let you push your ad data into Zapier/Make/IFTTT for further automation.")

    zap_url = st.text_input("Zapier/Make Webhook URL", st.session_state.get("zap_url",""))
    st.session_state["zap_url"] = zap_url

    st.write("Payload example (sent when you click Test):")
    payload = {
        "source": "Illuminati Ad Poster",
        "ad": st.session_state.get("ad_saved") or {},
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    st.code(json.dumps(payload, indent=2), language="json")

    if st.button("🛰️ Send Test Webhook"):
        if not zap_url:
            st.error("Add a webhook URL first.")
        else:
            try:
                import requests
                r = requests.post(zap_url, json=payload, timeout=10)
                st.success(f"Sent. Status: {r.status_code}")
            except Exception as e:
                st.error(f"Webhook error: {e}")

    st.markdown("---")
    st.markdown("Most free classified sites do not provide public APIs and block automation.")
    st.markdown("Use webhooks to trigger **your own** flows/tools (e.g., log to Sheets, notify VA, queue tasks).")

    render_footer()



