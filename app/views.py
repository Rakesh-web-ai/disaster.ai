import os
import json
import ollama
import google.generativeai as genai

from django.shortcuts import render
from .models import DisasterReport


# 🔑 Configure Gemini (put your real API key here)
genai.configure(api_key="YOUR_API_KEY")


# 🏠 HOME PAGE
def index(request):
    result = None

    if request.method == "POST":
        text = request.POST.get("text")
        lat = request.POST.get("latitude")
        lon = request.POST.get("longitude")
        image = request.FILES.get("image")

        prompt = f"""
        You are an AI disaster response system.

        Location: {lat}, {lon}
        Description: {text}

        Give output EXACTLY:

        Disaster Type: <type>
        Severity: <Low/Medium/High>

        Immediate Actions:
        - action 1
        - action 2

        Resources Needed:
        - resource 1
        - resource 2
        """

        try:
            raw = ""

            # ✅ TRY 1: LOCAL AI (OLLAMA)
            try:
                if image:
                    img_path = "temp.jpg"
                    with open(img_path, "wb+") as f:
                        for chunk in image.chunks():
                            f.write(chunk)

                    response = ollama.chat(
                        model='llava:7b',
                        messages=[{
                            'role': 'user',
                            'content': prompt,
                            'images': [img_path]
                        }]
                    )
                else:
                    response = ollama.chat(
                        model='llava:7b',
                        messages=[{
                            'role': 'user',
                            'content': prompt
                        }]
                    )

                raw = response['message']['content']

            except Exception as local_error:
                print("⚠ Ollama failed → switching to Gemini")

                # ✅ TRY 2: GEMINI (CLOUD AI)
                model = genai.GenerativeModel("gemini-pro")
                gemini_response = model.generate_content(prompt)
                raw = gemini_response.text

            # 🔥 PARSE OUTPUT
            disaster_type = "Unknown"
            severity = "Unknown"

            lines = raw.split("\n")
            for line in lines:
                if "Disaster Type:" in line:
                    disaster_type = line.split(":")[1].strip()

                if "Severity:" in line:
                    severity = line.split(":")[1].strip()

            # 💾 SAVE TO DATABASE
            DisasterReport.objects.create(
                disaster_type=disaster_type,
                severity=severity,
                description=text,
                latitude=lat,
                longitude=lon
            )

            # 🎨 FORMAT RESULT (PREMIUM UI)
            formatted = f"""
            <h3>🚨 Disaster Type:</h3>
            <p><b>{disaster_type}</b></p>

            <h3>⚠ Severity:</h3>
            <p class="badge {'high' if severity.lower()=='high' else 'medium' if severity.lower()=='medium' else 'low'}">
            {severity}
            </p>

            <h3>🛠 Immediate Actions:</h3>
            <ul>
            """

            # extract actions
            if "Immediate Actions:" in raw:
                actions = raw.split("Immediate Actions:")[1].split("Resources Needed:")[0].strip().split("\n")
                for a in actions:
                    if a.strip():
                        formatted += f"<li>{a.replace('-', '').strip()}</li>"

            formatted += "</ul><h3>📦 Resources Needed:</h3><ul>"

            # extract resources
            if "Resources Needed:" in raw:
                resources = raw.split("Resources Needed:")[1].strip().split("\n")
                for r in resources:
                    if r.strip():
                        formatted += f"<li>{r.replace('-', '').strip()}</li>"

            formatted += "</ul>"

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

    return render(request, 'dashboard.html', {
        'total': total,
        'high': high,
        'medium': medium,
        'low': low
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