import os
import io
import re
from datetime import date
from flask import Flask, render_template, request, send_file, jsonify
from docxtpl import DocxTemplate

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("transport_form.html")


@app.route("/generate_transport", methods=["POST"])
def generate_transport():
    origin      = request.form.get("origin", "")
    destination = request.form.get("destination", "")
    trip_type   = request.form.get("trip_type", "")
    truck_type  = request.form.get("truck_type", "")
    cargo_type  = request.form.get("cargo_type", "general")
    cicpa_pass  = request.form.get("cicpa", "No") == "Yes"

    # TODO: replace with your actual rate‐calculation logic
    unit_rate = 123.45
    total_fee = unit_rate

    tpl = DocxTemplate("templates/TransportQuotation.docx")
    context = {
        "TODAY_DATE":    date.today().strftime("%d %B %Y"),
        "ORIGIN":        origin,
        "DESTINATION":   destination,
        "TRIP_TYPE":     trip_type.replace("_", " ").title(),
        "TRUCK_TYPE":    truck_type.replace("_", " ").title(),
        "CARGO_TYPE":    "Chemical Load" if cargo_type == "chemical" else "General Cargo",
        "CICPA_PASS":    "Yes" if cicpa_pass else "No",
        "UNIT_RATE":     f"{unit_rate:.2f} AED",
        "TOTAL_FEE":     f"{total_fee:.2f} AED"
    }
    tpl.render(context)

    doc_io = io.BytesIO()
    tpl.save(doc_io)
    doc_io.seek(0)
    return send_file(
        doc_io,
        as_attachment=True,
        download_name="DSV_Transport_Quotation.docx",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").lower().strip()

    def normalize(text):
        text = text.lower().strip()
        text = re.sub(r"\bu\b", "you", text)
        text = re.sub(r"\bur\b", "your", text)
        text = re.sub(r"\br\b", "are", text)
        text = re.sub(r"\bpls\b", "please", text)
        text = re.sub(r"\bthx\b", "thanks", text)
        text = re.sub(r"\binfo\b", "information", text)
        text = re.sub(r"\bwh\b", "warehouse", text)
        text = re.sub(r"\bw\/h\b", "warehouse", text)
        text = re.sub(r"\binv\b", "inventory", text)
        text = re.sub(r"\btemp zone\b", "temperature zone", text)
        text = re.sub(r"\bwms system\b", "wms", text)
        text = re.sub(r"\brak\b", "ras al khaimah", text)
        text = re.sub(r"\bdxb\b", "dubai", text)
        text = re.sub(r"\bo&g\b", "oil and gas", text)
        text = re.sub(r"\bdg\b", "dangerous goods", text)
        text = re.sub(r"\bfmcg\b", "fast moving consumer goods", text)
        text = re.sub(r"\bdoc(s)?\b", "documentation", text)
        text = re.sub(r"\bmsds\b", "material safety data sheet", text)
        text = re.sub(r"\bvas\b", "value added services", text)
        return text

    msg = normalize(message)

    def match(patterns):
        return any(re.search(p, msg) for p in patterns)

    # --- Original chat patterns ---

    # Greetings
    if match([r"\bhello\b", r"\bhi\b", r"\bhey\b"]):
        return jsonify({"reply": "Hello! How can I help with DSV transport quotes today?"})
    if match([r"how.?are.?you", r"what.?up"]):
        return jsonify({"reply": "I'm doing great! Ready to help."})
    if match([r"\bthank(s| you)?\b", r"\bthx\b"]):
        return jsonify({"reply": "You're welcome!"})

    # Chamber mapping (21K clients)
    if match([r"who is in ch(\d+)", r"21k clients", r"client in ch\d+"]):
        ch = re.search(r"ch(\d+)", msg)
        num = int(ch.group(1)) if ch else None
        clients = {
            1: "Khalifa University",
            2: "PSN",
            3: "Food clients & fast-moving items",
            4: "MCC, TR, and ADNOC",
            5: "PSN",
            6: "ZARA & TR",
            7: "Civil Defense and the RMS"
        }
        name = clients.get(num, "unknown")
        return jsonify({"reply": f"Chamber {num} is occupied by {name}."})

    # Value-Added Services
    if match([r"kitting", r"assembly", r"value added kitting"]):
        return jsonify({
            "reply": "DSV provides **kitting and assembly** as a Value Added Service:\n"
                     "- Combine multiple SKUs into kits\n"
                     "- Light assembly of components\n"
                     "- Repacking and labeling\n"
                     "- Ideal for retail, pharma, and project logistics"
        })
    if match([r"packing material", r"materials used for packing"]):
        return jsonify({
            "reply": "We use high-grade packing materials:\n"
                     "- Shrink wrap (6 rolls per box – 1 roll = 20 pallets)\n"
                     "- Strapping rolls + buckle kits\n"
                     "- Bubble wrap, carton boxes, foam sheets\n"
                     "- Heavy-duty pallets (wooden/plastic)"
        })
    if match([r"\brelocation\b", r"move warehouse", r"site relocation"]):
        return jsonify({
            "reply": "Yes, we offer **relocation services**:\n"
                     "- Machinery shifting\n"
                     "- Office & warehouse moves\n"
                     "- Packing, transport, offloading\n"
                     "- Insurance and dismantling available"
        })

    # Machinery / Equipment
    if match([r"machinery|equipment used|forklift|crane"]):
        return jsonify({
            "reply": "We deploy forklifts (3–15T), VNA/reach trucks, pallet jacks, cranes, and container lifters."
        })

    # Pallet bays
    if match([r"pallet.*bay", r"euro pallet"]):
        return jsonify({
            "reply": "Each bay in 21K holds 14 Standard pallets or 21 Euro pallets for maximum efficiency."
        })

    # E-commerce & WMS
    if match([r"ecom(merce)?|online retail"]):
        return jsonify({
            "reply": "DSV offers end-to-end e-commerce logistics: warehousing, pick & pack, returns, last-mile, and WMS integration."
        })
    if match([r"insurance|cargo insurance"]):
        return jsonify({
            "reply": "Insurance is optional and can be arranged upon request, subject to cargo value and terms."
        })
    if match([r"\bwms\b|what wms system"]):
        return jsonify({
            "reply": "We use the **INFOR WMS** for real-time inventory, inbound/outbound flows, and order tracking."
        })

    # QHSE & Training
    if match([r"training|fire drill|manual handling|toolbox talk"]):
        return jsonify({
            "reply": "All staff undergo regular QHSE training: fire safety, first aid, manual handling, and site induction."
        })

    # DSV & ADNOC
    if match([r"adnoc|oil and gas project"]):
        return jsonify({
            "reply": "DSV has a strong partnership with ADNOC, providing logistics for their oil & gas projects under strict QHSE standards."
        })

    # Summer / Heat ban
    if match([r"summer break|midday break|heat ban"]):
        return jsonify({
            "reply": "From June 15 to Sep 15, outdoor work pauses daily between 12:30-3:30 PM for staff safety per MOHRE guidelines."
        })

    # Warehouse layout & capacity
    if match([r"chambers|warehouse layout|how many chambers"]):
        return jsonify({
            "reply": "21K warehouse has 7 chambers, each sized 1,000–5,000 sqm, totalling 35,000 cbm of racked storage."
        })
    if match([r"warehouse.*space.*available|availability"]):
        return jsonify({
            "reply": "For warehouse availability, please contact Biju Krishnan at biju.krishnan@dsv.com."
        })
    if match([r"open yard.*space|yard capacity"]):
        return jsonify({
            "reply": "For open yard availability, please contact Antony Jeyaraj at antony.jeyaraj@dsv.com."
        })

    # Temperature zones
    if match([r"temperature zone|cold room|freezer"]):
        return jsonify({
            "reply": "We offer Ambient (+18–25°C), Cold Room (+2–8°C), and Freezer (–22°C) storage, all 24/7 monitored."
        })

    # TAPA certification
    if match([r"tapa|transported asset protection"]):
        return jsonify({
            "reply": "TAPA is a global security standard; DSV aligns with TAPA practices for secure warehousing and transport."
        })

    # Freezone facility
    if match([r"freezone|abu dhabi airport freezone"]):
        return jsonify({
            "reply": "Our Abu Dhabi Airport Freezone facility is GDP-compliant for pharma: temperature control, customs-cleared, and WMS-tracked."
        })

    # Retail & Fashion industry
    if match([r"\bretail\b|fashion logistics"]):
        return jsonify({
            "reply": "DSV supports retail & fashion with racked ambient, VNA, pick & pack, VAS (labeling, tagging), and last-mile delivery."
        })

    # Oil & Gas & Breakbulk
    if match([r"oil and gas|breakbulk|heavy cargo"]):
        return jsonify({
            "reply": "Our oil & gas and breakbulk services include chemical storage, heavy haul, lowbed, crane support, and project logistics."
        })

    # Last-mile & City delivery
    if match([r"last mile|city delivery"]):
        return jsonify({
            "reply": "We provide last-mile delivery across the UAE with small city trucks and vans, fully WMS-tracked."
        })

    # Inventory & WMS details
    if match([r"inventory management|stock tracking"]):
        return jsonify({
            "reply": "All inventory is managed by INFOR WMS with real-time dashboards, barcode scanning, and ERP integration."
        })

    # Air & Sea freight
    if match([r"air freight|sea freight|air & sea"]):
        return jsonify({
            "reply": "DSV offers global Air & Sea forwarding: FCL/LCL, express, charter, customs clearance, and warehouse integration."
        })

    # Chemical quotation requirements
    if match([r"chemical.*quote|chemical.*quotation"]):
        return jsonify({
            "reply": "For a chemical quote we need: Product name & hazard class, volume (CBM/SQM), duration, MSDS, and special handling needs."
        })

    # Fallback
    return jsonify({"reply": "Sorry, I didn't catch that. Could you please rephrase?"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = (os.environ.get("FLASK_ENV") == "development")
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
