from flask import Flask, render_template, request, send_file, jsonify, session
from docx import Document
import os
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")


# =========================================================
# DOCX helpers (placeholder replacement + block deletion)
# =========================================================
def replace_placeholders(doc: Document, mapping: dict):
    """Replace {{PLACEHOLDER}} text in both paragraphs and table cells."""
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
    """Remove a paragraph from the document safely."""
    p = paragraph._element
    parent = p.getparent()
    if parent is not None:
        parent.remove(p)


def _delete_block_in_paragraphs(paragraphs, start_tag, end_tag):
    """Remove sequential paragraphs between start_tag and end_tag (inclusive)."""
    inside = False
    buffer = []
    for p in paragraphs:
        t = p.text or ""
        if not inside and start_tag in t:
            inside = True
            buffer.append(p)
            continue
        if inside:
            buffer.append(p)
            if end_tag in t:
                for rp in buffer:
                    _remove_paragraph(rp)
                buffer = []
                inside = False
    # If the end tag never appeared, still remove the collected block
    if inside and buffer:
        for rp in buffer:
            _remove_paragraph(rp)


def delete_block(doc: Document, start_tag: str, end_tag: str):
    """Delete blocks delimited by tags in both body and inside table cells."""
    # 1) Body paragraphs
    _delete_block_in_paragraphs(doc.paragraphs, start_tag, end_tag)
    # 2) Paragraphs inside table cells
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                _delete_block_in_paragraphs(cell.paragraphs, start_tag, end_tag)


# =========================================================
# Routes
# =========================================================
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

    st_lower = storage_type.lower()

    # Choose template by family
    if "chemical" in st_lower:
        template_path = "templates/Chemical VAS.docx"
    elif "open yard" in st_lower or "openyard" in st_lower:
        template_path = "templates/Open Yard VAS.docx"
    else:
        template_path = "templates/Standard VAS.docx"

    doc = Document(template_path)

    # Defaults
    unit = "CBM"
    rate_unit = "CBM / DAY"
    rate = 0.0
    storage_fee = 0.0

    # Rates and fee calc
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
    months = max(1, days // 30)
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
        "{{TODAY_DATE}}": today_str,
    }

    replace_placeholders(doc, placeholders)

    # Keep only relevant VAS block
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


# =========================================================
# Chatbot helpers
# =========================================================
def normalize(raw: str) -> str:
    """Lowercase, fix common typos/abbreviations, strip non-alnum (keep spaces & periods)."""
    s = (raw or "").strip().lower()

    subs = [
        # Common chat / slang
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
        (r"\balmarkaz\b", "al markaz"),
        # Logistics / industry short forms
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
        # Vehicles / containers
        (r"\breefer\s+tr+ucks?\b", "reefer trucks"),
        (r"\brefeer\b", "reefer"),
        (r"\bchiller\b", "reefer"),
        (r"\b20ft\b", "20 ft"),
        (r"\b40ft\b", "40 ft"),
    ]

    for pat, repl in subs:
        s = re.sub(pat, repl, s)

    s = re.sub(r"[^a-z0-9\s\.]", "", s).strip()
    return s


def any_match(message: str, patterns):
    return any(re.search(p, message, re.I) for p in patterns)


def reply(text: str):
    return jsonify({"reply": text})


# =========================================================
# Chat route
# =========================================================
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    raw = data.get("message", "")
    raw = raw if isinstance(raw, str) else str(raw)

    # Quick greeting if first non-empty line is short
    first_line = next((ln.strip() for ln in raw.splitlines() if ln.strip()), "")
    if re.match(r"^(hi|hello|hey|good (morning|evening))\b", first_line, re.I) and len(first_line.split()) <= 4:
        return reply("Hello! I'm here to help with DSV logistics, warehousing, transport, and VAS.")

    msg = normalize(raw)

    # --- Small talk ---
    if any_match(msg, [r"^how are you$", r"^how are u$", r"^how r you$", r"^how r u$"]):
        return reply("I'm doing great! How can I assist you with DSV services today?")

    # =====================================================
    # PRIORITY: Specific intents before generic ones
    # =====================================================

    # Cancellation charges (transport)
    if any_match(msg, [r"(any )?cancellation.*(charge|policy)", r"cancel.*transport", r"transport.*cancellation"]):
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

    # FM200 / RFID
    if any_match(msg, [r"\bfm ?200\b", r"what is fm200"]):
        return reply(
            "**FM-200** (heptafluoropropane) is a clean-agent fire suppression gas used in sensitive areas "
            "like document rooms (RMS). It extinguishes fire quickly without damaging documents or equipment."
        )
    if any_match(msg, [r"\brfid\b", r"what is rfid", r"rfid meaning"]):
        return reply(
            "**RFID (Radio-Frequency Identification)** uses small tagged labels read by scanners to track assets/inventory "
            "without line-of-sight. DSV supports RFID-based asset labeling & stock control."
        )

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

    # Distances (Al Markaz <-> Mussafah)
    if any_match(msg, [r"al markaz.*mussafah", r"mussafah.*al markaz", r"distance.*al markaz.*mussafah"]):
        return reply("Distance between **Mussafah** and **Al Markaz** is about **60 km** (~45–60 minutes by road).")

    # Double trailer (and typo support)
    if any_match(msg, [r"double tail truck", r"double trailer", r"tandem trailer", r"articulated trailer"]):
        return reply(
            "🚚 **Double Trailer**: Articulated truck with two trailers for long-distance, high-volume transport. "
            "Typical combined capacity **50–60 tons**."
        )

    # Transportation types / fleet
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
            "Operating range typically **+2°C to –22°C**, with GPS & real-time temp tracking."
        )

    # =====================================================
    # Value Added Services (VAS)
    # =====================================================
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

    if any_match(msg, [r"^chemical vas$", r"chemical value added services", r"hazmat vas", r"all chemical vas"]):
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

    if any_match(msg, [r"^standard vas$", r"standard value added services", r"normal vas", r"value added service$"]):
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

    if any_match(msg, [r"^vas rates$", r"^value added services$", r"^vas$"]):
        return reply(
            "Which **VAS** do you need?\n"
            "- 🟦 Standard VAS (AC/Non-AC/Open Shed)\n"
            "- 🧪 Chemical VAS\n"
            "- 🏗 Open Yard VAS\n\n"
            "You can also say **all vas** for the full list."
        )

    # =====================================================
    # Storage rates (ask → branch)
    # =====================================================
    if any_match(msg, [
        r"^storage rate(s)?$", r"warehouse rates$", r"storage cost", r"how much.*storage",
        r"pricing of storage", r"rate for storage$", r"rates$", r"rate$"
    ]) and not any_match(msg, [r"open yard", r"chemical", r"value added", r"vas"]):
        session["awaiting"] = "storage_type"
        return reply("Which storage type do you need: **Standard**, **Chemicals**, or **Open Yard**?")

    # Open yard rates first (specific before generic)
    if any_match(msg, [r"^open yard$", r"open yard (rate|rates|storage)"]):
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

    # Chemical storage split
    if any_match(msg, [r"^chemical$", r"chemical storage only"]):
        session["awaiting"] = "chemical_variant"
        return reply("Do you need **Chemical AC** or **Chemical Non-AC**?")
    if any_match(msg, [r"chemical ac", r"ac chemical", r"chemical ac storage"]):
        session.pop("awaiting", None)
        return reply("**Chemical AC** storage: **3.5 AED/CBM/day**. Chemical VAS applies.")
    if any_match(msg, [r"chemical non ac", r"non ac chemical", r"chemical non-?ac storage"]):
        session.pop("awaiting", None)
        return reply("**Chemical Non-AC** storage: **2.7 AED/CBM/day**. Chemical VAS applies.")
    if any_match(msg, [r"^ac$", r"^non ac$"]):
        if session.get("awaiting") == "chemical_variant":
            session.pop("awaiting", None)
            if msg.strip() == "ac":
                return reply("**Chemical AC** storage: **3.5 AED/CBM/day**. Chemical VAS applies.")
            else:
                return reply("**Chemical Non-AC** storage: **2.7 AED/CBM/day**. Chemical VAS applies.")

    # Standard storage split
    if any_match(msg, [r"^standard$", r"standard storage"]):
        return reply("Do you need **Standard AC**, **Standard Non-AC**, or **Open Shed**?")
    if any_match(msg, [r"standard ac", r"ac standard", r"standard ac storage"]):
        if session.get("awaiting") == "storage_type":
            session.pop("awaiting", None)
        return reply("**Standard AC** storage: **2.5 AED/CBM/day**. Standard VAS applies.")
    if any_match(msg, [r"standard non ac", r"non ac standard", r"standard non-?ac storage"]):
        if session.get("awaiting") == "storage_type":
            session.pop("awaiting", None)
        return reply("**Standard Non-AC** storage: **2.0 AED/CBM/day**. Standard VAS applies.")
    if any_match(msg, [r"^open shed$", r"open shed", r"shed storage"]):
        if session.get("awaiting") == "storage_type":
            session.pop("awaiting", None)
        return reply("**Open Shed** storage: **1.8 AED/CBM/day**. Standard VAS applies.")

    # SQM -> CBM thumb rule
    if any_match(msg, [
        r"(how|what).*convert.*(sqm|sq\.?m).*cbm",
        r"(convert|calculate|estimate).*cbm.*(from|using).*sqm",
        r"(sqm|sq\.?m).*to.*cbm",
        r"client.*gave.*sqm.*how.*cbm",
        r"how.*cbm.*(if|when).*client.*(gives|provides).*sqm",
        r"i have.*sqm.*need.*cbm"
    ]):
        return reply("If the client doesn’t provide CBM, estimate using **1 SQM ≈ 1.8 CBM** for standard racked storage.")

    # =====================================================
    # Containers (ocean equipment, not VAS 'container lifting')
    # =====================================================
    if any_match(msg, [
        r"\b20\s*(ft|feet|foot)\b", r"\btwenty\s*(ft|feet|foot)?\b",
        r"\b20 ft\b.*", r".*20.*container.*", r"container.*20 ft", r"^20 ft$", r"^20 feet$", r"20ft spec"
    ]):
        return reply(
            "📦 **20ft Container Specs**:\n"
            "- Length: 6.1m\n- Width: 2.44m\n- Height: 2.59m\n"
            "- Capacity: ~33 CBM\n- Max Payload: ~28,000 kg\n\n"
            "Ideal for compact/heavy cargo like pallets or general freight."
        )

    if any_match(msg, [
        r"\b40\s*(ft|feet|foot)\b", r"\bforty\s*(ft|feet|foot)?\b",
        r"\b40 ft\b.*", r".*40.*container.*", r"container.*40 ft", r"^40 ft$", r"^40 feet$", r"40ft spec"
    ]):
        return reply(
            "📦 **40ft Container Specs**:\n"
            "- Length: 12.2m\n- Width: 2.44m\n- Height: 2.59m\n"
            "- Capacity: ~67 CBM\n- Max Payload: ~30,400 kg\n\n"
            "Perfect for palletized or high-volume cargo."
        )

    if any_match(msg, [r"high ?cube", r"40\s*(ft|feet|foot)\s*high cube", r"high cube container", r"40ft.*high cube", r"high cube spec", r"taller container"]):
        return reply(
            "⬆️ **40ft High Cube Container**:\n"
            "- Same length/width as 40ft: 12.2m x 2.44m\n"
            "- **Height: 2.90m** (vs 2.59m standard)\n"
            "- Capacity: ~76 CBM\n"
            "For voluminous/light cargo where height matters."
        )

    if any_match(msg, [r"\breefer\b", r"reefer container", r"refrigerated container", r"chiller container", r"cold storage container", r"reefer.*(20|40)ft", r"reefer specs", r"reefer box"]):
        return reply(
            "❄️ **Reefer (Refrigerated) Containers**:\n"
            "- Sizes: **20ft** and **40ft**\n"
            "- Temperature control: **+2°C to –25°C**\n"
            "- Uses: food, pharma, perishables\n"
            "- Plug-in units (electric/diesel)\n\n"
            "Example 40ft: 12.2m x 2.44m x 2.59m (~67 CBM)."
        )

    if any_match(msg, [r"open top container", r"open top", r"top open", r"open roof", r"no roof container", r"crane loaded container", r"top loading container"]):
        return reply(
            "🏗 **Open Top Container**:\n"
            "- 20ft or 40ft, removable tarpaulin roof\n"
            "- Same base dims as standard box\n"
            "- Top loading via crane/forklift; for tall/oversized cargo."
        )

    if any_match(msg, [r"flat rack", r"no sides container", r"flat rack container"]):
        return reply("🟫 **Flat Rack**: No sides/roof; ideal for oversized equipment, vehicles, and machinery.")

    if any_match(msg, [r"\bcontainers?\b", r"container types", r"types of containers", r"container sizes", r"container overview", r"container specs", r"container info"]):
        return reply("Main types: 20ft, 40ft, 40ft High Cube, Reefer, Flat Rack, Open Top. Tell me which you need details on.")

    # =====================================================
    # Pallets / racking / warehouse info
    # =====================================================
    if any_match(msg, [r"\bpallets\b", r"pallet types", r"types of pallets", r"pallet size", r"pallet sizes", r"pallet dimensions", r"pallet.*per bay"]):
        return reply(
            "DSV uses two main pallets in 21K:\n"
            "🟦 **Standard** 1.2m × 1.0m — **14 per bay**\n"
            "🟨 **Euro** 1.2m × 0.8m — **21 per bay**"
        )

    if any_match(msg, [r"rack height|rack levels|pallets per bay|racking"]):
        return reply("21K racks are **12m** tall with **6 pallet levels**. Each bay: **14 Standard** or **21 Euro** pallets.")

    if any_match(msg, [r"\baisle\b", r"aisle width", r"vna aisle", r"rack aisle width"]):
        return reply(
            "21K aisle widths:\n"
            "- **Selective**: 2.95–3.3 m\n"
            "- **VNA**: 1.95 m\n"
            "- **Drive-in**: 2.0 m"
        )

    if any_match(msg, [r"\b21k\b", r"tell me about 21k", r"21k warehouse", r"mussafah.*21k"]):
        return reply(
            "21K (Mussafah) is **21,000 sqm** (clear height 15m) with 7 chambers. Racking: Selective, VNA, Drive-in.\n"
            "Clients: ADNOC, ZARA, PSN, Civil Defense. Fire systems, access control, and RMS area included."
        )

    if any_match(msg, [r"\brms\b", r"record management system", r"document storage"]):
        return reply(
            "RMS (Record Management System) is inside 21K for storing archives/documents. Equipped with **FM-200** fire suppression."
        )

    # Asset management / labeling
    if any_match(msg, [r"what is asset management", r"asset management$"]):
        return reply(
            "DSV **Asset Management**:\n"
            "- Barcode/RFID tracking, asset labeling\n"
            "- Storage & life-cycle monitoring\n"
            "- Secure location control\n"
            "Ideal for IT equipment, tools, and government assets."
        )

    if any_match(msg, [r"asset labeling|asset labelling|label assets|rfid tagging|barcode tagging|labeling service"]):
        return reply(
            "We provide **Asset Labeling** with RFID/barcodes (unique ID, ownership, scannable codes), "
            "applied at intake or on-site."
        )

    # Warehouse activities / SOP
    if any_match(msg, [r"^sop$", r"warehouse sop", r"standard operating procedure"]):
        return reply(
            "**Warehouse SOP (high-level):**\n"
            "1) Inbound: receiving, inspection, put-away\n"
            "2) Storage: racked/bulk with WMS control\n"
            "3) Order Processing: picking, packing, labeling\n"
            "4) Outbound: staging, dispatch, transport coordination\n"
            "5) Inventory Control: cycle counts, stock checks, returns\n"
            "QHSE, access control, and fire systems apply across all activities."
        )

    if any_match(msg, [r"warehouse activities", r"warehouse process", r"inbound|outbound|putaway|replenishment|dispatch"]):
        return reply(
            "Typical processes:\n"
            "1) Inbound (receiving, inspection, put-away)\n"
            "2) Storage (racks/bulk)\n"
            "3) Order Processing (picking, packing, labeling)\n"
            "4) Outbound (staging, dispatch)\n"
            "5) Inventory Control (cycle counts, returns)\n"
            "All run on **INFOR WMS**."
        )

    # WMS / INFOR
    if any_match(msg, [r"what is wms|wms meaning|warehouse management system"]):
        return reply("**WMS** = Warehouse Management System. DSV uses **INFOR WMS** for inventory, inbound/outbound, and visibility.")
    if any_match(msg, [r"\binventory\b", r"inventory management", r"inventory control", r"stock tracking"]):
        return reply(
            "INFOR WMS provides real-time stock visibility, bin tracking, batch/serial & expiry control, "
            "and ERP integration."
        )
    if any_match(msg, [r"\binfor\b", r"infor wms", r"infor system", r"infor software"]):
        return reply(
            "**INFOR** is the WMS platform used by DSV: real-time inventory, barcode scanning, "
            "inbound/outbound control, and ERP integrations."
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

    # Terms & Conditions (warehouse vs transport)
    if any_match(msg, [r"warehouse terms and conditions", r"warehouse t.?&.?c", r"warehouse terms", r"^t.?&.?c$"]):
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
            "• Subject to availability; standard UAE truck specs\n"
            "• Customer scope: loading/offloading\n"
            "• Sharjah/Ajman need Municipality permissions\n"
            "• Detention: **AED 150/hr** after free time\n"
            "• Backhaul: same-day **+60%** / next-day **100%**\n"
            "• Sun/Holidays: trip rate **+50%**\n"
            "• Force majeure: weather/traffic delays\n"
            "• Additional fees: VAT 5%, Env. fee AED 10/trip; from Jan 2025 env. surcharge **0.15% of invoice**\n"
            "• Exclusions: port/gate/toll/permits/customs/insurance/VGM/washing (at actuals)"
        )

    # Inclusions / Exclusions / Force majeure / Detention
    if any_match(msg, [r"what.*included", r"included.*transport", r"transport.*inclusions"]):
        return reply("✅ **Inclusions:** Fuel (Diesel); DSV equipment & personnel insurance.")
    if any_match(msg, [r"what.*excluded", r"excluded.*transport", r"transport.*exclusions"]):
        return reply("❌ **Exclusions:** Loading/offloading/supervision; port charges, gate passes, tolls, permits; customs, insurance, VGM, washing (at actuals).")
    if any_match(msg, [r"force majeure", r"weather condition", r"sandstorm", r"rain.*delay", r"high wind"]):
        return reply("🌪️ **Force Majeure:** Weather/unforeseen delays count as normal working hours; detention applies beyond free time.")
    if any_match(msg, [r"detention", r"detention charges", r"truck waiting", r"wait time charges"]):
        return reply("🕒 **Detention:** AED 150 per truck per hour after 1 free hour at site.")

    if any_match(msg, [r"environmental fee", r"environment fee", r"0\.15%.*fee", r"green surcharge", r"eco fee"]):
        return reply("🚛 Environmental Fees:\n- AED 10.00 per trip/truck\n- Effective 1 Jan 2025: **0.15%** of invoice value added as environmental surcharge.")

    # E-commerce / Cross-dock / Transit store
    if any_match(msg, [r"e-?commerce|online retail|fulfillment center|shop logistics"]):
        return reply(
            "End-to-end e-commerce: warehousing, pick & pack, returns, last-mile, "
            "with integrations (Shopify/Magento/APIs)."
        )
    if any_match(msg, [r"cross ?dock|cross-docking|crossdock facility"]):
        return reply("We support **cross-docking**: Receive → Sort → Dispatch (no storage). Ideal for FMCG/e-comm.")
    if any_match(msg, [r"transit store", r"transit storage", r"transit warehouse", r"short term storage"]):
        return reply(
            "DSV offers **transit storage** for short-term holding:\n"
            "- Customs-cleared goods awaiting dispatch\n"
            "- Re-export / cross-docking\n"
            "- Available at Mussafah, KIZAD, and Airport Freezone."
        )

    # Who we are / services
    if any_match(msg, [
        r"who are you", r"who r u", r"who.*are.*you", r"what.*can.*you.*do",
        r"what.*can.*you.*help.*with", r"what.*services.*you.*offer", r"^what\s*services\??$", r"^services\??$",
        r"\bwhat\s+services\b", r"what.*do.*you.*do", r"what.*you.*provide"
    ]):
        return reply(
            "I'm the DSV logistics assistant 🤖. I can help with:\n"
            "• 📦 Storage rates (Standard, Chemical, Open Yard)\n"
            "• 🚛 Transport & truck types (flatbeds, reefers, lowbeds...)\n"
            "• 🧾 Value Added Services (VAS)\n"
            "• 🏢 Warehouse info: size, layout, chambers\n"
            "• 🧊 Temperature zones, RMS, training\n"
            "• 📍 UAE routes & distances\n"
            "Ask me anything related to DSV warehousing, logistics, or transport!"
        )

    # Default helpful fallback (no “rephrase” nag)
    return reply(
        "I can help with DSV **storage rates**, **VAS**, **transport**, and **warehouse info**.\n"
        "Try one of these:\n"
        "• *all vas*  • *chemical vas*  • *open yard rates*\n"
        "• *warehouse t&c*  • *what is fm200*  • *what is rfid*\n"
        "• *distance from al markaz to mussafah*"
    )


# =========================================================
# App boot
# =========================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
