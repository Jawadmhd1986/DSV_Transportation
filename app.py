import os
import io
from datetime import date
from flask import Flask, render_template, request, send_file
from docxtpl import DocxTemplate

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("transport_form.html")

@app.route("/generate_transport", methods=["POST"])
def generate_transport():
    # 1. Capture form inputs
    origin      = request.form.get("origin", "")
    destination = request.form.get("destination", "")
    trip_type   = request.form.get("trip_type", "")
    truck_type  = request.form.get("truck_type", "")
    cargo_type  = request.form.get("cargo_type", "general")
    cicpa_pass  = request.form.get("cicpa", "No") == "Yes"
    email       = request.form.get("email", "")

    # 2. TODO: Replace with your rate‐calculation logic
    unit_rate = 123.45       # placeholder
    total_fee = unit_rate    # placeholder

    # 3. Render the Word template
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

    # 4. Send the filled document back to the browser
    doc_io = io.BytesIO()
    tpl.save(doc_io)
    doc_io.seek(0)
    return send_file(
        doc_io,
        as_attachment=True,
        download_name="DSV_Transport_Quotation.docx",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

if __name__ == "__main__":
    # Bind to 0.0.0.0 on the port Render provides (or 5000 locally)
    # Use `or 5000` so empty PORT="" still falls back
    port = int(os.environ.get("PORT") or 5000)
    debug_mode = (os.environ.get("FLASK_ENV") == "development")
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
