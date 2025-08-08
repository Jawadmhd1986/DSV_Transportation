from flask import Flask, render_template, request, send_file, jsonify, session
from docx import Document
import os
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")

# -------------------------------
# Helpers for DOCX manipulation
# -------------------------------

def replace_placeholders(doc: Document, mapping: dict):
    """Replace {{PLACEHOLDER}} in both paragraphs and table cells (simple text replace)."""
    # Paragraphs
    for p in doc.paragraphs:
        txt = p.text
        for k, v in mapping.items():
            if k in txt:
                txt = txt.replace(k, v)
        if txt != p.text:
            p.text = txt

    # Tables (all cells)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                txt = cell.text
                for k, v in mapping.items():
                    if k in txt:
                        txt = txt.replace(k, v)
                if txt != cell.text:
                    cell.text = txt

def _remove_paragraph(paragraph):
    """Remove a paragraph from document safely."""
    p = paragraph._element
    parent = p.getparent()
    if parent is not None:
        parent.remove(p)

def delete_block_in_paragraphs(paragraphs, start_tag, end_tag):
    """Remove blocks delimited by start_tag ... end_tag within a list of paragraphs."""
    inside = False
    buffer = []
    for p in paragraphs:
        t = p.text or ""
        if start_tag in t:
            inside = True
            buffer.append(p)
            continue
        if inside:
            buffer.append(p)
            if end_tag in t:
                # remove collected
                for rp in buffer:
                    _remove_paragraph(rp)
                buffer = []
                inside = False
    # If start without end, drop the remainder
    if inside and buffer:
        for rp in buffer:
            _remove_paragraph(rp)

def delete_block(doc: Document, start_tag: str, end_tag: str):
    """Delete blocks marked by tags in both document body and inside table cells."""
    # 1) whole-document paragraphs
    delete_block_in_paragraphs(doc.paragraphs, start_tag, end_tag)

    # 2) paragraphs inside each table cell
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                delete_block_in_paragraphs(cell.paragraphs, start_tag, end_tag)

# -------------------------------
# Routes
# -------------------------------

@app.route("/")
def index():
    return render_template("form.html")

@app.route("/generate", methods=["POST"])
def generate():
    storage_type = request.form.get("storage_type", "")
    volume = float(request.form.get("volume", 0) or 0)
    days = int(request.form.get("days", 0) or 0)
    include_wms = request.form.get("wms", "No") == "Yes"
    email = request.form.get("email", "")
    today_str = datetime.today().strftime("%d %b %Y")

    # Pick template by storage family
    st_lower = storage_type.lower()
    if "chemical" in st_lower:
        template_path = "templates/Chemical VAS.docx"
    elif "open yard" in st_lower or "openyard" in st_lower:
        template_path = "templates/Open Yard VAS.docx"
    else:
        template_path = "templates/Standard VAS.docx"

    doc = Document(template_path)

    # Rates
    unit = "CBM"
    rate_unit = "CBM / DAY"
    rate = 0.0
    storage_fee = 0.0

    if storage_type == "AC":
        rate = 2.5
        storage_fee = volume * days * rate
    elif storage_type == "Non-AC":
        rate = 2.0
        storage_fee = volume * days * rate
    elif storage_type == "Open Shed":
        rate = 1.8
        storage_fee = volume * days * rate
    elif storage_type == "Chemicals AC":
        rate = 3.5
        storage_fee = volume * days * rate
    elif storage_type == "Chemicals Non-AC":
        rate = 2.7
        storage_fee = volume * days * rate
    elif "kizad" in st_lower:
        rate = 125
        unit = "SQM"
        rate_unit = "SQM / YEAR"
        storage_fee = volume * days * (rate / 365.0)
    elif "mussafah" in st_lower:
        rate = 160
        unit = "SQM"
        rate_unit = "SQM / YEAR"
        storage_fee = volume * days * (rate / 365.0)

    storage_fee = round(storage_fee, 2)
    months = max(1, days // 30)  # month rounding
    is_open_yard = ("open yard" in st_lower) or ("openyard" in st_lower)
    wms_fee = 0 if is_open_yard or not include_wms else 1500 * months
    total_fee = round(storage_fee + wms_fee, 2)

    placeholders = {
        "{{STORAGE_TYPE}}": storage_type,
        "{{DAYS}}": str(days),
        "{{VOLUME}}": str(volume),
        "{{UNIT}}": unit,
        "{{WMS_STATUS}}": "" if is_open_yard else ("INCLUDED" if include_wms else "NOT INCLUDED"),
        "{{UNIT_RATE}}": f"{rate:.2f} AED / {rate_unit}",
        "{{STORAGE_FEE}}": f"{storage_fee:,.2f} AED",
        "{{WMS_FEE}}": f"{wms_fee:,.2f} AED",
        "{{TOTAL_FEE}}": f"{total_fee:,.2f} AED",
        "{{TODAY_DATE}}": today_str
    }

    replace_placeholders(doc, placeholders)

    # Remove non-relevant VAS blocks
    if is_open_yard:
        delete_block(doc, "[VAS_STANDARD]", "[/VAS_STANDARD]")
        delete_block(doc, "[VAS_CHEMICAL]", "[/VAS_CHEMICAL]")
    elif "chemical" in st_lower:
        delete_block(doc, "[VAS_STANDARD]", "[/VAS_STANDARD]")
        delete_block(doc, "[VAS_OPENYARD]", "[/VAS_OPENYARD]")
    else:
        delete_block(doc, "[VAS_CHEMICAL]", "[/VAS_CHEMICAL]")
        delete_block(doc, "[VAS_OPENYARD]", "[/VAS_OPENYARD]")

    os.makedirs("generated", exist_ok=True)
    filename_prefix = email.split("@")[0] if email else "quotation"
    filename = f"Quotation_{filename_prefix}.docx"
    output_path = os.path.join("generated", filename)
    doc.save(output_path)
    return send_file(output_path, as_attachment=True)

# -------------------------------
# Chatbot: normalization + routing
# -------------------------------

def normalize(raw: str) -> str:
    """Lowercase, trim, expand common typos/abbreviations, strip non-alnum (keep spaces and periods)."""
    s = (raw or "").strip().lower()

    # quick fixes / slang
    subs = [
        (r"\bu\b", "you"),
        (r"\bur\b", "your"),
        (r"\br\b", "are"),
        (r"\bhru\b", "how are you"),
        (r"\bh\s*r\s*u\b", "how are you"),
        (r"how\s*r\s*u", "how are you"),
        (r"how\s*u\s*doing", "how are you"),
        (r"\bpl[sz]\b", "please"),
        (r"\bthx\b", "thanks"),
        (r"\binfo\b", "information"),
        (r"\bassist\b", "help"),
        (r"\bhw\b", "how"),
        (r"\bwht\b", "what"),
        (r"\bcn\b", "can"),
        (r"\bwhats up\b", "how are you"),
        (r"\bwho r u\b", "who are you"),
        (r"\btyoes\b", "types"),
        (r"\btr+rucks?\b", "trucks"),
        (r"\btr+ailer\b", "trailer"),
        (r"\balmarkaz\b", "al markaz"),
    ]

    # industry abbreviations / spellings
    subs += [
        (r"\bwh\b", "warehouse"),
        (r"\bw\/?h\b", "warehouse"),
        (r"\binv\b", "inventory"),
        (r"\btemp zone\b", "temperature zone"),
        (r"\btemp\b", "temperature"),
        (r"\bwms system\b", "wms"),
        (r"\bwms\b", "warehouse management system"),
        (r"\brak\b", "ras al khaimah"),
        (r"\babudhabi\b", "abu dhabi"),
        (r"\bdxb\b", "dubai"),
        (r"\babu dabi\b", "abu dhabi"),
        (r"\bt&c\b", "terms and conditions"),
        (r"\bt and c\b", "terms and conditions"),
        (r"\bo&g\b", "oil and gas"),
        (r"\bdg\b", "dangerous goods"),
        (r"\bfmcg\b", "fast moving consumer goods"),
        (r"\bvas\b", "value added services"),
        (r"\bqu+?otation\b", "quotation"),
        (r"\btransprt\b|\btrnasport\b", "transport"),
        (r"\bmhe\b", "material handling equipment"),
        (r"\bwharehouse\b", "warehouse"),
        (r"\bwmsytem\b", "wms"),
        (r"\bopen yrd\b", "open yard"),
        (r"\bstorge\b|\bstorag\b", "storage"),
        (r"\bchecmical\b", "chemical"),
        (r"\bstandrad\b", "standard"),
        (r"\blabelling\b", "labeling"),
        (r"\breefer\s+tr+ucks?\b", "reefer trucks"),
        (r"\bchiller\b", "reefer"),
        (r"\brefeer\b", "reefer"),
        (r"\b20ft\b", "20 ft"),
        (r"\b40ft\b", "40 ft"),
    ]

    for pat, repl in subs:
        s = re.sub(pat, repl, s)

    # strip anything weird
    s = re.sub(r"[^a-z0-9\s\.]", "", s).strip()
    return s

def any_match(message: str, patterns):
    return any(re.search(p, message, re.I) for p in patterns)

def reply(text: str):
    return jsonify({"reply": text})

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    raw = data.get("message", "")
    raw = raw if isinstance(raw, str) else str(raw)

    # quick greeting path (first non-empty line)
    first_line = next((ln.strip() for ln in raw.splitlines() if ln.strip()), "")
    if re.match(r"^(hi|hello|hey|good (morning|evening))\b", first_line, re.I) and len(first_line.split()) <= 4:
        return reply("Hello! I'm here to help with DSV logistics, warehousing, transport, and VAS.")

    msg = normalize(raw)

    # --- simple small-talk / how-are-you ---
    if any_match(msg, [r"^how are you$", r"^how are u$", r"^how r you$", r"^how r u$"]):
        return reply("I'm doing great! How can I assist you with DSV services today?")

    # --------------- SPECIFIC BEFORE GENERIC ---------------

    # Cancellation charges (transport)
    if any_match(msg, [r"cancellation.*charge", r"cancel.*transport", r"transport.*cancellation"]):
        return reply(
            "**Cancellation Charges:**\n"
            "- ❌ 50% if cancelled before truck placement\n"
            "- ❌ 100% if cancelled after truck placement\n"
            "- ✅ No charge if cancelled 24 hours in advance."
        )

    # Open yard occupancy / availability
    if any_match(msg, [
        r"open yard.*(occupancy|availability|space|vacancy)",
        r"available space.*open yard",
        r"yard.*(space|available|vacancy)"
    ]):
        return reply("For open yard occupancy, please contact **Antony Jeyaraj** at **antony.jeyaraj@dsv.com**.")

    # Packing material
    if any_match(msg, [r"packing material", r"materials used for packing", r"what packing material"]):
        return reply(
            "DSV uses high-grade packing materials:\n"
            "- Shrink wrap (6 rolls/box; ~20 pallets/roll)\n"
            "- Strapping rolls + buckle kits (~20 pallets/roll)\n"
            "- Bubble wrap, carton boxes, foam sheets\n"
            "- Heavy-duty pallets (wooden/plastic)\n"
            "Used for relocation, storage, and export."
        )

    # FM200 & RFID
    if any_match(msg, [r"\bfm ?200\b", r"what is fm200"]):
        return reply(
            "**FM-200** (heptafluoropropane) is a clean-agent fire suppression gas used in sensitive areas "
            "like document rooms (RMS). It extinguishes fire quickly without damaging documents or equipment."
        )
    if any_match(msg, [r"\brfid\b", r"what is rfid", r"rfid meaning"]):
        return reply(
            "**RFID (Radio-Frequency Identification)** uses tagged labels read by scanners to track assets and inventory "
            "without line-of-sight. DSV supports RFID-based asset labeling and stock control."
        )

    # Distances (Al Markaz / Mussafah)
    if any_match(msg, [r"al markaz.*mussafah", r"mussafah.*al markaz"]):
        return reply("Distance between **Mussafah** and **Al Markaz** is about **60 km** (approx. 45–60 minutes by road).")

    # Double trailer (typo support)
    if any_match(msg, [r"double tail truck", r"double trailer", r"tandem trailer", r"articulated trailer"]):
        return reply(
            "🚚 **Double Trailer**: Articulated truck with two trailers for long-distance, high-volume transport. "
            "Typical combined capacity **50–60 tons**."
        )

    # Fleet / transportation types
    if any_match(msg, [r"transportation types", r"truck types", r"dsv trucks", r"trucking services", r"\bfleet\b"]):
        return reply(
            "DSV provides UAE/GCC transport using:\n"
            "- 🚛 Flatbeds for general cargo\n"
            "- 🏗 Lowbeds for heavy equipment\n"
            "- 🪨 Tippers for construction bulk\n"
            "- 📦 Box trucks for protected goods\n"
            "- ❄️ Reefer trucks (chiller/freezer)\n"
            "- 🚚 Double trailers for long-haul\n"
            "- 🏙 Vans & city trucks for last mile."
        )

    # Reefer trucks
    if any_match(msg, [r"reefer truck", r"chiller truck", r"refrigerated truck", r"cold truck"]):
        return reply(
            "❄️ **Reefer Truck**: Temperature-controlled vehicle for cold chain goods (food, pharma, chemicals). "
            "Operating range typically **+2°C to –22°C**, GPS + real-time temperature tracking."
        )

    # Value Added Services (VAS) — specific first
    if any_match(msg, [r"^all chemical vas$", r"^chemical vas$", r"chemical value added services", r"hazmat vas"]):
        return reply(
            "🧪 **Chemical VAS**:\n"
            "- Handling (Palletized): 20 AED/CBM\n"
            "- Handling (Loose): 25 AED/CBM\n"
            "- Documentation: 150 AED/set\n"
            "- Packing with pallet: 85 AED/CBM\n"
            "- Inventory Count: 3,000 AED/event\n"
            "- Inner Bag Picking: 3.5 AED/bag\n"
            "- Sticker Labeling: 1.5 AED/label\n"
            "- Shrink Wrapping: 6 AED/pallet"
        )

    if any_match(msg, [r"^open yard vas$", r"open yard value added services", r"yard equipment|forklift rate|crane rate|yard charges"]):
        return reply(
            "🏗 **Open Yard VAS**:\n"
            "- Forklift (3T–7T): 90 AED/hr\n"
            "- Forklift (10T): 200 AED/hr\n"
            "- Forklift (15T): 320 AED/hr\n"
            "- Mobile Crane (50T): 250 AED/hr\n"
            "- Mobile Crane (80T): 450 AED/hr\n"
            "- Container Lifting: 250 AED/lift\n"
            "- Container Stripping (20ft): 1,200 AED/hr"
        )

    if any_match(msg, [r"^standard vas$", r"standard value added services", r"normal vas"]):
        return reply(
            "🟦 **Standard VAS**:\n"
            "- In/Out Handling: 20 AED/CBM\n"
            "- Pallet Loading: 12 AED/pallet\n"
            "- Documentation: 125 AED/set\n"
            "- Packing with pallet: 85 AED/CBM\n"
            "- Inventory Count: 3,000 AED/event\n"
            "- Case Picking: 2.5 AED/carton\n"
            "- Sticker Labeling: 1.5 AED/label\n"
            "- Shrink Wrapping: 6 AED/pallet\n"
            "- VNA Usage: 2.5 AED/pallet"
        )

    if any_match(msg, [r"^all vas$", r"full vas list", r"complete vas list", r"list all vas", r"show all vas"]):
        return reply(
            "**📦 Standard VAS:**\n"
            "- In/Out Handling: 20 AED/CBM\n"
            "- Pallet Loading: 12 AED/pallet\n"
            "- Documentation: 125 AED/set\n"
            "- Packing with pallet: 85 AED/CBM\n"
            "- Inventory Count: 3,000 AED/event\n"
            "- Case Picking: 2.5 AED/carton\n"
            "- Sticker Labeling: 1.5 AED/label\n"
            "- Shrink Wrapping: 6 AED/pallet\n"
            "- VNA Usage: 2.5 AED/pallet\n\n"
            "**🧪 Chemical VAS:**\n"
            "- Handling (Palletized): 20 AED/CBM\n"
            "- Handling (Loose): 25 AED/CBM\n"
            "- Documentation: 150 AED/set\n"
            "- Packing with pallet: 85 AED/CBM\n"
            "- Inventory Count: 3,000 AED/event\n"
            "- Inner Bag Picking: 3.5 AED/bag\n"
            "- Sticker Labeling: 1.5 AED/label\n"
            "- Shrink Wrapping: 6 AED/pallet\n\n"
            "**🏗 Open Yard VAS:**\n"
            "- Forklift (3T–7T): 90 AED/hr\n"
            "- Forklift (10T): 200 AED/hr\n"
            "- Forklift (15T): 320 AED/hr\n"
            "- Mobile Crane (50T): 250 AED/hr\n"
            "- Mobile Crane (80T): 450 AED/hr\n"
            "- Container Lifting: 250 AED/lift\n"
            "- Container Stripping (20ft): 1,200 AED/hr"
        )

    if any_match(msg, [r"^vas rates$", r"^value added services$", r"^vas$"]):
        return reply(
            "Which **VAS** do you need?\n"
            "- 🟦 Standard VAS (AC/Non-AC/Open Shed)\n"
            "- 🧪 Chemical VAS\n"
            "- 🏗 Open Yard VAS\n\n"
            "You can also say **all vas** for the full list."
        )

    # SOP / Warehouse activities
    if any_match(msg, [r"^sop$", r"warehouse sop", r"standard operating procedure"]):
        return reply(
            "**Warehouse SOP (high-level):**\n"
            "1) Inbound: receiving, inspection, put-away\n"
            "2) Storage: racked/bulk with WMS control\n"
            "3) Order Processing: picking, packing, labeling\n"
            "4) Outbound: staging, dispatch, transport coordination\n"
            "5) Inventory Control: cycle count, stock checks, returns\n"
            "QHSE, access control, and fire systems apply across all activities."
        )

    if any_match(msg, [r"warehouse activities", r"warehouse process", r"inbound|outbound|putaway|replenishment|dispatch"]):
        return reply(
            "Typical warehouse processes:\n"
            "1) Inbound (receiving, inspection, put-away)\n"
            "2) Storage (racks/bulk)\n"
            "3) Order Processing (picking, packing, labeling)\n"
            "4) Outbound (staging, dispatch)\n"
            "5) Inventory Control (cycle counts, returns)\n"
            "All controlled via INFOR WMS."
        )

    # Transit store
    if any_match(msg, [r"transit store", r"transit storage", r"transit warehouse", r"short term storage"]):
        return reply(
            "DSV offers **transit storage** for short-term holding:\n"
            "- Customs-cleared goods awaiting dispatch\n"
            "- Re-export / cross-docking\n"
            "- Available at Mussafah, KIZAD, and Airport Freezone."
        )

    # Terms & Conditions (warehouse vs transport)
    if any_match(msg, [r"warehouse terms and conditions", r"warehouse t.?&.?c", r"warehouse terms", r"t.?&.?c$"]):
        return reply(
            "DSV quotations include: monthly billing, final settlement before vacating, **15-day validity**, subject to space. "
            "Depot hours Mon–Fri 08:30–17:30. Insurance not included by default. Environmental fee **0.15%** applies. "
            "Non-moving cargo (>3 months) may incur additional storage tariff."
        )

    if any_match(msg, [r"transport(ation)? t.?&.?c", r"transport terms and conditions"]):
        return reply(
            "**📦 Transportation Terms & Conditions:**\n"
            "• Quotation validity **15 days**\n"
            "• FOT-to-FOT basis; per trip per truck; general cargo\n"
            "• Subject to availability; based on standard UAE truck specs\n"
            "• Customer scope: loading/offloading\n"
            "• Sharjah/Ajman need Municipality permissions\n"
            "• Detention: **AED 150/hr** after free time\n"
            "• Backhaul: same-day **+60%** / next-day **100%**\n"
            "• Sun/Holidays: trip rate **+50%**\n"
            "• Force majeure: weather/traffic delays\n"
            "• Additional fees: VAT 5%, Env. fee AED 10/trip; from Jan 2025 env. surcharge **0.15% of invoice**\n"
            "• Exclusions: port/gate/toll/permits/customs/insurance/VGM/washing (at actuals)"
        )

    # Storage rates — ask first, then branch
    if any_match(msg, [
        r"^storage rate(s)?$", r"warehouse rates", r"storage cost", r"how much.*storage", r"pricing of storage",
        r"rate for storage", r"rates$", r"rate$"
    ]) and not any_match(msg, [r"open yard", r"chemical", r"value added", r"vas"]):
        session["awaiting"] = "storage_type"
        return reply("Which storage type do you need: **Standard**, **Chemicals**, or **Open Yard**?")

    # Open yard specific
    if any_match(msg, [r"^open yard$", r"open yard (rate|storage|rates)"]):
        session["awaiting"] = "open_yard_location"
        return reply("Do you need **Open Yard Mussafah** or **Open Yard KIZAD** rates?")
    if any_match(msg, [r"open yard mussafah", r"mussafah open yard"]):
        session.pop("awaiting", None)
        return reply("Open Yard **Mussafah**: **160 AED/SQM/year**. WMS excluded. Contact **antony.jeyaraj@dsv.com** for availability.")
    if any_match(msg, [r"open yard kizad", r"kizad open yard", r"^kizad$"]):
        session.pop("awaiting", None)
        return reply("Open Yard **KIZAD**: **125 AED/SQM/year**. WMS excluded. Contact **antony.jeyaraj@dsv.com** for availability.")
    if any_match(msg, [r"^mussafah$"]):
        if session.get("awaiting") == "open_yard_location":
            session.pop("awaiting", None)
            return reply("Open Yard **Mussafah**: **160 AED/SQM/year**. WMS excluded. Contact **antony.jeyaraj@dsv.com** for availability.")

    # Chemical storage follow-up
    if any_match(msg, [r"^chemical$", r"chemical storage only"]):
        session["awaiting"] = "chemical_variant"
        return reply("Do you need **Chemical AC** or **Chemical Non-AC**?")
    if any_match(msg, [r"chemical ac", r"ac chemical", r"chemical ac storage"]):
        session.pop("awaiting", None)
        return reply("**Chemical AC** storage: **3.5 AED/CBM/day**. Chemical VAS applies.")
    if any_match(msg, [r"chemical non ac", r"non ac chemical", r"chemical non-?ac storage"]):
        session.pop("awaiting", None)
        return reply("**Chemical Non-AC** storage: **2.7 AED/CBM/day**. Chemical VAS applies.")
    # Handle bare "ac"/"non ac" after chemical prompt
    if any_match(msg, [r"^ac$", r"^non ac$"]):
        if session.get("awaiting") == "chemical_variant":
            session.pop("awaiting", None)
            if "ac" == msg.strip():
                return reply("**Chemical AC** storage: **3.5 AED/CBM/day**. Chemical VAS applies.")
            else:
                return reply("**Chemical Non-AC** storage: **2.7 AED/CBM/day**. Chemical VAS applies.")

    # Standard storage split
    if any_match(msg, [r"^standard$", r"standard storage"]):
        return reply("Do you need **Standard AC**, **Standard Non-AC**, or **Open Shed**?")
    if any_match(msg, [r"standard ac", r"ac standard", r"standard ac storage", r"^ac$"]):
        if session.get("awaiting") == "storage_type":
            session.pop("awaiting", None)
        return reply("**Standard AC** storage: **2.5 AED/CBM/day**. Standard VAS applies.")
    if any_match(msg, [r"standard non ac", r"non ac standard", r"standard non ac storage", r"^non ac$"]):
        if session.get("awaiting") == "storage_type":
            session.pop("awaiting", None)
        return reply("**Standard Non-AC** storage: **2.0 AED/CBM/day**. Standard VAS applies.")
    if any_match(msg, [r"^open shed$", r"open shed", r"shed storage"]):
        if session.get("awaiting") == "storage_type":
            session.pop("awaiting", None)
        return reply("**Open Shed** storage: **1.8 AED/CBM/day**. Standard VAS applies.")

    # General 3PL quoting info (SQM→CBM thumb rule)
    if any_match(msg, [
        r"(how|what).*convert.*(sqm|sq\.?m).*cbm",
        r"(convert|calculate|estimate).*cbm.*(from|using).*sqm",
        r"(sqm|sq\.?m).*to.*cbm",
        r"client.*gave.*sqm.*how.*cbm",
        r"how.*cbm.*(if|when).*client.*(gives|provides).*sqm",
        r"i have.*sqm.*need.*cbm"
    ]):
        return reply("If the client doesn’t provide CBM, estimate using **1 SQM ≈ 1.8 CBM** for standard racked storage.")

    # Asset management / RFID labeling
    if any_match(msg, [r"what is asset management", r"asset management$"]):
        return reply(
            "DSV offers **Asset Management**:\n"
            "- Barcode/RFID tracking\n- Asset labeling\n- Storage & life-cycle monitoring\n- Secure location control\n"
            "Ideal for IT equipment, tools, and government assets."
        )
    if any_match(msg, [r"asset labeling|asset labelling|label assets|rfid tagging|barcode tagging"]):
        return reply(
            "DSV provides **Asset Labeling** with RFID or barcodes (unique ID, ownership info, scannable codes) "
            "applied during intake or on-site."
        )

    # FOT to FOT
    if any_match(msg, [r"fot to fot", r"f\.?o\.?t to f\.?o\.?t", r"fot basis", r"what is fot"]):
        return reply(
            "**FOT to FOT** = Free On Truck at both ends:\n"
            "- Pickup **on a truck** at origin\n"
            "- Delivery **on a truck** at destination\n"
            "- Loading/unloading at both ends **excluded**"
        )

    # E-commerce, last mile
    if any_match(msg, [r"last mile", r"final mile", r"city delivery"]):
        return reply("DSV offers last-mile delivery across UAE using vans & small city trucks with WMS tracking.")
    if any_match(msg, [r"e-?commerce|online retail|fulfillment center"]):
        return reply(
            "End-to-end e-commerce logistics: warehousing, pick & pack, returns, last-mile, "
            "and integrations (Shopify/Magento/APIs)."
        )

    # Distances between emirates (quick set)
    if any_match(msg, [r"abu dhabi.*dubai|dubai.*abu dhabi"]):
        return reply("Abu Dhabi ↔ Dubai ~**140 km**, ~**2.5 hours**.")
    if any_match(msg, [r"abu dhabi.*sharjah|sharjah.*abu dhabi"]):
        return reply("Abu Dhabi ↔ Sharjah ~**160 km**, ~**2.5–3 hours**.")
    if any_match(msg, [r"abu dhabi.*ajman|ajman.*abu dhabi"]):
        return reply("Abu Dhabi ↔ Ajman ~**170 km**, ~**2.5–3 hours**.")
    if any_match(msg, [r"abu dhabi.*ras al khaimah|ras al khaimah.*abu dhabi|rak.*abu dhabi|abu dhabi.*rak"]):
        return reply("Abu Dhabi ↔ RAK ~**240 km**, ~**3–3.5 hours**.")
    if any_match(msg, [r"abu dhabi.*fujairah|fujairah.*abu dhabi"]):
        return reply("Abu Dhabi ↔ Fujairah ~**250 km**, ~**3–3.5 hours**.")

    # Default helpful fallback (no “rephrase” nag)
    return reply(
        "I can help with DSV **storage rates**, **VAS**, **transport**, and **warehouse info**.\n"
        "Try one of these:\n"
        "• *all vas*  • *chemical vas*  • *open yard rates*\n"
        "• *warehouse t&c*  • *what is fm200*  • *what is rfid*\n"
        "• *distance from al markaz to mussafah*"
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
