import os
import json
import ollama
import google.generativeai as genai

from dotenv import load_dotenv
from django.shortcuts import render
from .models import DisasterReport

# 🔑 Load env
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY)


# 🏠 HOME
def index(request):
    result = None

    if request.method == "POST":
        text = request.POST.get("text")
        lat = request.POST.get("latitude")
        lon = request.POST.get("longitude")
        image = request.FILES.get("image")

        prompt = f"""
You are an AI disaster response system.

STRICT RULES:
- Always follow format EXACTLY
- No extra text

FORMAT:

Disaster Type: <Flood / Earthquake / Fire / Cyclone / Landslide / Other>
Severity: <Low / Medium / High>

Immediate Actions:
- action 1
- action 2

Resources Needed:
- resource 1
- resource 2

INPUT:
Location: {lat}, {lon}
Description: {text}
"""

        try:
            raw = ""

            # ==============================
            # ✅ TRY 1: OLLAMA
            # ==============================
            try:
                print("🧠 Using Ollama...")

                # 🔥 IMPORTANT FIX:
                # llama3 → TEXT ONLY
                # llava → IMAGE SUPPORT

                if image:
                    img_path = "temp.jpg"
                    with open(img_path, "wb+") as f:
                        for chunk in image.chunks():
                            f.write(chunk)

                    response = ollama.chat(
                        model='llama3',   # ✅ FIXED
                        messages=[{
                            'role': 'user',
                            'content': prompt,
                            'images': [img_path]
                        }]
                    )

                    os.remove(img_path)

                else:
                    response = ollama.chat(
                        model='llama3',
                        messages=[{
                            'role': 'user',
                            'content': prompt
                        }]
                    )

                raw = response['message']['content']

            except Exception as e:
                print("⚠ Ollama failed:", e)

                # ==============================
                # ✅ TRY 2: GEMINI
                # ==============================
                if API_KEY:
                    print("☁ Using Gemini...")

                    try:
                        model = genai.GenerativeModel("gemini-1.5-flash")
                        gemini_response = model.generate_content(prompt)
                        raw = gemini_response.text

                    except Exception as g:
                        raw = f"AI Error (Gemini): {str(g)}"
                else:
                    raw = "No AI available"

            # ==============================
            # 🧠 CLEAN RAW OUTPUT
            # ==============================
            raw = raw.replace("[img-0]", "").strip()

            print("\n🔥 RAW AI RESPONSE:\n", raw)

            # ==============================
            # 🔥 PARSING (ROBUST)
            # ==============================
            disaster_type = "Unknown"
            severity = "Unknown"
            actions = []
            resources = []

            section = None

            for line in raw.split("\n"):
                line = line.strip()

                # --- HEADERS ---
                if "disaster type" in line.lower():
                    disaster_type = line.split(":", 1)[-1].strip()

                elif "severity" in line.lower():
                    severity = line.split(":", 1)[-1].strip()

                elif "immediate actions" in line.lower():
                    section = "actions"

                elif "resources needed" in line.lower():
                    section = "resources"

                # --- BULLETS ---
                elif line.startswith(("-", "•", "–")):
                    item = line.replace("-", "").replace("•", "").replace("–", "").strip()

                    if section == "actions":
                        actions.append(item)

                    elif section == "resources":
                        resources.append(item)

            # ==============================
            # 🛠 FALLBACK (SMART)
            # ==============================
            text_lower = raw.lower()

            if disaster_type == "Unknown":
                if "flood" in text_lower:
                    disaster_type = "Flood"
                elif "earthquake" in text_lower:
                    disaster_type = "Earthquake"
                elif "fire" in text_lower:
                    disaster_type = "Fire"

            if severity == "Unknown":
                if "high" in text_lower:
                    severity = "High"
                elif "medium" in text_lower:
                    severity = "Medium"
                elif "low" in text_lower:
                    severity = "Low"

            # ==============================
            # 💾 SAVE
            # ==============================
            DisasterReport.objects.create(
                disaster_type=disaster_type,
                severity=severity,
                description=text,
                latitude=lat,
                longitude=lon
            )

            # ==============================
            # 🎨 UI OUTPUT
            # ==============================
            severity_class = (
                "high" if severity.lower() == "high"
                else "medium" if severity.lower() == "medium"
                else "low"
            )

            formatted = f"""
            <h3>🚨 Disaster Type</h3>
            <p><b>{disaster_type}</b></p>

            <h3>⚠ Severity</h3>
            <span class="badge {severity_class}">{severity}</span>

            <h3>🛠 Immediate Actions</h3>
            <ul>
            {''.join([f'<li>{a}</li>' for a in actions]) if actions else '<li>No data</li>'}
            </ul>

            <h3>📦 Resources Needed</h3>
            <ul>
            {''.join([f'<li>{r}</li>' for r in resources]) if resources else '<li>No data</li>'}
            </ul>
            """

            result = formatted

        except Exception as e:
            result = f"<p style='color:red;'>Error: {str(e)}</p>"

    return render(request, 'index.html', {'result': result})


# 📊 DASHBOARD
def dashboard(request):
    reports = DisasterReport.objects.all()

    total = reports.count()
    high = reports.filter(severity__iexact="High").count()
    medium = reports.filter(severity__iexact="Medium").count()
    low = reports.filter(severity__iexact="Low").count()

    # 🔥 ADD THIS BLOCK HERE
    locations = [
        {
            "lat": float(r.latitude) if r.latitude else 0,
            "lon": float(r.longitude) if r.longitude else 0,
            "type": r.disaster_type,
            "severity": r.severity
        }
        for r in reports
    ]

    # 🔥 ADD locations HERE
    return render(request, 'dashboard.html', {
        'total': total,
        'high': high,
        'medium': medium,
        'low': low,
        'locations': json.dumps(locations)
    })


# 🗂 HISTORY
def history(request):
    reports = DisasterReport.objects.all().order_by('-id')

    locations = [
        {
            "lat": float(r.latitude) if r.latitude else 0,
            "lon": float(r.longitude) if r.longitude else 0,
            "type": r.disaster_type,
            "severity": r.severity
        }
        for r in reports
    ]

    return render(request, 'history.html', {
        'reports': reports,
        'locations': json.dumps(locations)
    })