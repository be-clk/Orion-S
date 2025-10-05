import math
import requests
from flask import Flask, jsonify, request, render_template, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import random


app = Flask(__name__,
            template_folder='web',
            static_folder='web')
            
CORS(app)

# LÜTFEN KENDİ NASA API ANAHTARINIZI BURAYA EKLEYİN. (Demo anahtarı genelde çalışmaz.)
NASA_API_KEY = "q5o8yUe0pSXXt4obA7gVawqboJnVaRcNyamZAyBW"

# NASA NeoWs API Base URL
NASA_NEO_API = "https://api.nasa.gov/neo/rest/v1"

@app.route('/')
def index():
    """Ana harita sayfası"""
    return send_from_directory('web', 'index.html')

@app.route('/simulation')
def simulation():
    """3D simülasyon sayfası"""
    return send_from_directory('web', 'simulation.html')

@app.route('/web/<path:filename>')
def serve_static(filename):
    """Web dosyalarını serve et"""
    return send_from_directory('web', filename)

@app.route('/test')
def test_route():
    return jsonify({
        "status": "success",
        "message": "Meteor Madness Backend Çalışıyor! 🚀",
        "nasa_api": "✅ Set" if NASA_API_KEY != "BURAYA_API_ANAHTARINIZI_YAZIN" else "❌ NOT SET"
    })

# --- METEOR VERİLERİ ---

# Yerel CSV'den gelen meteorlar
LOCAL_METEORS = [
    {"name":"Abee","mass":107000,"latitude":54.21667,"longitude":-113.0,"year":1952,"type":"local"},
    {"name":"Acapulco","mass":1914,"latitude":16.88333,"longitude":-99.9,"year":1976,"type":"local"},
    {"name":"Adhi Kot","mass":4239,"latitude":32.1,"longitude":71.8,"year":1919,"type":"local"},
    {"name":"Adzhi-Bogdo","mass":910,"latitude":44.83333,"longitude":95.16667,"year":1949,"type":"local"},
    {"name":"Akyumak","mass":50000,"latitude":39.91667,"longitude":42.81667,"year":1981,"type":"local"},
    {"name":"Albareto","mass":2000,"latitude":44.53333,"longitude":9.95,"year":1766,"type":"local"},
    {"name":"Allegan","mass":34500,"latitude":42.53333,"longitude":-85.8,"year":1899,"type":"local"},
    {"name":"Almahata Sitta","mass":3950,"latitude":20.71667,"longitude":32.51667,"year":2008,"type":"local"},
    {"name":"Alta'ameem","mass":1620,"latitude":35.16667,"longitude":43.3,"year":1977,"type":"local"}
]

@app.route('/api/meteors/all', methods=['GET'])
def get_all_meteors():
    """Hem yerel hem NASA meteorlarını döndür"""
    try:
        all_meteors = LOCAL_METEORS.copy()
        
        # NASA verilerini ekliyoruz
        try:
            nasa_meteors = fetch_nasa_meteors()
            all_meteors.extend(nasa_meteors)
        except Exception as e:
            print(f"NASA verileri alınamadı: {e}")
        
        return jsonify({
            "success": True,
            "count": len(all_meteors),
            "meteors": all_meteors
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

def fetch_nasa_meteors():
    """NASA API'den yaklaşan asteroidleri çek"""
    try:
        start_date = datetime.now().strftime('%Y-%m-%d')
        end_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        url = f"{NASA_NEO_API}/feed"
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "api_key": NASA_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            nasa_meteors = []
            
            for date, neo_list in data.get("near_earth_objects", {}).items():
                for neo in neo_list[:5]:  # Her günden 5 tane al
                    # Rastgele koordinatlar (gerçek projede yörünge hesabı gerekir)
                    # Harita üzerinde göstermek için rastgele enlem ve boylam
                    # hash() kullanımı aynı ID için aynı konumu sağlar, bu bir simülasyon kolaylığıdır.
                    lat = (hash(neo['id']) % 180) - 90
                    lng = (hash(neo['id'] + 'lng') % 360) - 180
                    
                    diameter = neo.get("estimated_diameter", {}).get("meters", {}).get("estimated_diameter_max", 100)
                    velocity = float(neo.get("close_approach_data", [{}])[0].get("relative_velocity", {}).get("kilometers_per_second", 20))
                    
                    # Kütleyi çaptan tahmin et (küre formülü, yoğunluk ~3000 kg/m³)
                    radius = diameter / 2
                    mass = (4/3) * math.pi * (radius ** 3) * 3000 * 1000  # gram
                    
                    nasa_meteors.append({
                        "name": neo.get("name"),
                        "id": neo.get("id"),
                        "mass": mass,
                        "diameter": diameter,
                        "velocity": velocity,
                        "latitude": lat,
                        "longitude": lng,
                        "date": neo.get("close_approach_data", [{}])[0].get("close_approach_date", date),
                        "miss_distance_km": float(neo.get("close_approach_data", [{}])[0].get("miss_distance", {}).get("kilometers", 1000000)),
                        "is_hazardous": neo.get("is_potentially_hazardous_asteroid", False),
                        "type": "nasa"
                    })
            
            return nasa_meteors
        else:
            # --- HATA AYIKLAMA EKLEMESİ ---
            print("="*50)
            print(f"!!! NASA API HATASI !!!")
            print(f"HTTP Durumu: {response.status_code}")
            print(f"Hata Mesajı (NASA): {response.text}")
            print("Büyük ihtimalle API anahtarınız hız limitine takıldı (429) veya geçersiz (403).")
            print("="*50)
            # ---
            return []
    except Exception as e:
        print(f"NASA API bağlantı hatası (ağ sorunu): {e}")
        return []

@app.route('/api/meteor/<string:meteor_id>', methods=['GET'])
def get_meteor_details(meteor_id):
    """Belirli bir meteorun detaylarını getir"""
    try:
        # Önce yerel verilerden ara
        for meteor in LOCAL_METEORS:
            if meteor['name'] == meteor_id:
                return jsonify({
                    "success": True,
                    "meteor": meteor
                })
        
        # NASA'dan ara
        url = f"{NASA_NEO_API}/neo/{meteor_id}"
        params = {"api_key": NASA_API_KEY}
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return jsonify({
                "success": True,
                "meteor": format_nasa_meteor(data)
            })
        else:
            return jsonify({
                "success": False,
                "error": "Meteor bulunamadı veya API hatası oluştu"
            }), 404
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

def format_nasa_meteor(neo):
    """NASA verisini formatla"""
    diameter = neo.get("estimated_diameter", {}).get("meters", {}).get("estimated_diameter_max", 100)
    return {
        "id": neo.get("id"),
        "name": neo.get("name"),
        "diameter": diameter,
        "absolute_magnitude": neo.get("absolute_magnitude_h"),
        "is_hazardous": neo.get("is_potentially_hazardous_asteroid"),
        "nasa_jpl_url": neo.get("nasa_jpl_url")
    }

@app.route('/api/simulate-impact', methods=['POST'])
def simulate_impact():
    """Çarpma simülasyonu - Fizik hesaplamaları"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Veri gönderilmedi"}), 400
        
        # Parametreler
        diameter = float(data.get('diameter', 100))  # metre
        velocity = float(data.get('velocity', 20))   # km/s
        density = float(data.get('density', 3000))   # kg/m³
        angle = float(data.get('angle', 45))         # derece
        delta_v = float(data.get('delta_v', 0))      # km/s (saptırma)
        
        # Validasyon
        if diameter <= 0 or velocity <= 0:
            return jsonify({"error": "Geçersiz parametreler"}), 400
        
        # Saptırma sonrası hız
        impact_velocity = max(velocity - delta_v, 0.1)
        
        # Kütle: m = (4/3) * π * r³ * ρ
        radius = diameter / 2
        mass = (4/3) * math.pi * (radius ** 3) * density
        
        # Kinetik enerji: KE = 0.5 * m * v²
        v_ms = impact_velocity * 1000  # m/s
        kinetic_energy = 0.5 * mass * v_ms ** 2
        
        # Açı faktörü
        angle_factor = math.sin(math.radians(angle))
        effective_energy = kinetic_energy * angle_factor
        
        # TNT eşdeğeri (1 ton TNT = 4.184e9 J)
        tnt_equiv = effective_energy / 4.184e9
        
        # Krater çapı: D = k * (E/10⁹)^0.25
        crater_diameter = 1.8 * (effective_energy / 1e9) ** 0.25
        
        # Deprem büyüklüğü: Mw = (2/3) * log10(E) - 3.2
        if effective_energy > 0:
            seismic_mw = (2/3) * math.log10(effective_energy) - 3.2
        else:
            seismic_mw = 0
        
        # Etki yarıçapı (km)
        blast_radius = (tnt_equiv / 1000) ** 0.33 if tnt_equiv > 0 else 0
        
        # Kategori
        category = categorize_impact(tnt_equiv)
        
        # Saptırma başarısı
        deflection_success = delta_v > 0 and delta_v >= (velocity * 0.05)  # %5 hız değişimi yeterli
        
        return jsonify({
            "success": True,
            "input": {
                "diameter_m": diameter,
                "velocity_kms": velocity,
                "density_kgm3": density,
                "angle_deg": angle,
                "delta_v_kms": delta_v
            },
            "results": {
                "mass_kg": mass,
                "kinetic_energy_j": kinetic_energy,
                "effective_energy_j": effective_energy,
                "tnt_equivalent_tons": tnt_equiv,
                "tnt_equivalent_megatons": tnt_equiv / 1e6,
                "crater_diameter_m": crater_diameter,
                "seismic_magnitude_mw": seismic_mw,
                "blast_radius_km": blast_radius,
                "impact_category": category,
                "deflection_applied": delta_v > 0,
                "deflection_success": deflection_success,
                "survival_chance": calculate_survival_chance(tnt_equiv, blast_radius)
            }
        })
        
    except ValueError as e:
        return jsonify({"error": f"Geçersiz girdi: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"Simülasyon hatası: {str(e)}"}), 500

def categorize_impact(tnt_tons):
    """Çarpma kategorisi"""
    if tnt_tons < 1000:
        return "Minimal - Yerel hasar"
    elif tnt_tons < 1_000_000:
        return "Orta - Şehir seviyesi tehdit"
    elif tnt_tons < 1_000_000_000:
        return "Şiddetli - Bölgesel felaket"
    else:
        return "Kıyamet - Küresel felaket"

def calculate_survival_chance(tnt_tons, blast_radius):
    """Hayatta kalma şansı (basitleştirilmiş)"""
    if tnt_tons < 1000:
        return {"percentage": 95, "description": "Çok yüksek"}
    elif tnt_tons < 100_000:
        return {"percentage": 70, "description": "Yüksek"}
    elif tnt_tons < 10_000_000:
        return {"percentage": 40, "description": "Orta"}
    elif tnt_tons < 1_000_000_000:
        return {"percentage": 10, "description": "Düşük"}
    else:
        return {"percentage": 0.1, "description": "Neredeyse imkansız"}

@app.route('/api/early-warning', methods=['POST'])
def early_warning_system():
    """Erken uyarı sistemi"""
    try:
        data = request.get_json()
        
        meteor_name = data.get('meteor_name', 'Bilinmeyen')
        impact_location = data.get('location', {'lat': 0, 'lng': 0})
        impact_time = data.get('impact_time', 'Bilinmiyor')
        simulation_results = data.get('simulation_results', {})
        
        # Uyarı seviyesi belirle
        tnt = simulation_results.get('tnt_equivalent_tons', 0)
        
        if tnt > 100_000_000:
            alert_level = "KIRMIZI - KÜRESEL ACİL DURUM"
            evacuation_radius = simulation_results.get('blast_radius_km', 0) * 3
        elif tnt > 1_000_000:
            alert_level = "TURUNCU - BÖLGESEL TAHLIYE"
            evacuation_radius = simulation_results.get('blast_radius_km', 0) * 2
        elif tnt > 10_000:
            alert_level = "SARI - YEREL UYARI"
            evacuation_radius = simulation_results.get('blast_radius_km', 0) * 1.5
        else:
            alert_level = "YEŞİL - BİLGİLENDİRME"
            evacuation_radius = simulation_results.get('blast_radius_km', 0)
        
        warning_message = {
            "success": True,
            "alert_level": alert_level,
            "meteor_name": meteor_name,
            "impact_location": impact_location,
            "impact_time": impact_time,
            "evacuation_radius_km": evacuation_radius,
            "estimated_casualties": estimate_casualties(tnt, evacuation_radius),
            "recommended_actions": get_recommended_actions(alert_level),
            "emergency_contacts": [
                "AFAD: 122",
                "Polis: 155",
                "İtfaiye: 110",
                "Sağlık: 112"
            ],
            "simulation_data": simulation_results
        }
        
        return jsonify(warning_message)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

def estimate_casualties(tnt_tons, radius_km):
    """Tahmini kayıplar (basitleştirilmiş)"""
    # Ortalama nüfus yoğunluğu: 100 kişi/km²
    affected_area = math.pi * (radius_km ** 2)
    potential_affected = int(affected_area * 100)
    
    if tnt_tons < 10_000:
        fatality_rate = 0.01
    elif tnt_tons < 1_000_000:
        fatality_rate = 0.1
    elif tnt_tons < 100_000_000:
        fatality_rate = 0.5
    else:
        fatality_rate = 0.9
    
    return {
        "affected_population": potential_affected,
        "estimated_fatalities": int(potential_affected * fatality_rate),
        "estimated_injuries": int(potential_affected * (1 - fatality_rate) * 0.7)
    }

def get_recommended_actions(alert_level):
    """Önerilen aksiyonlar"""
    actions = {
        "KIRMIZI - KÜRESEL ACİL DURUM": [
            "Derhal en yakın sığınağa gidin",
            "Tüm ulaşım sistemlerini durdurun",
            "Acil durum çantanızı hazırlayın",
            "Su ve gıda stoklayın (minimum 1 hafta)",
            "Tüm iletişim kanallarını açık tutun"
        ],
        "TURUNCU - BÖLGESEL TAHLIYE": [
            "Bölgeden tahliye planlarını takip edin",
            "Acil çıkış yollarını öğrenin",
            "Önemli eşyalarınızı toplayın",
            "Yakınlarınızı bilgilendirin",
            "Yerel yetkililerin talimatlarını izleyin"
        ],
        "SARI - YEREL UYARI": [
            "Haberleri takip edin",
            "Pencerelerden uzak durun",
            "Acil durum planınızı gözden geçirin",
            "İletişim kanallarını açık tutun"
        ],
        "YEŞİL - BİLGİLENDİRME": [
            "Durumu izlemeye devam edin",
            "Güncel bilgileri takip edin"
        ]
    }
    return actions.get(alert_level, [])

@app.route('/api/status', methods=['GET'])
def api_status():
    """API durumunu kontrol et"""
    nasa_connected = False
    try:
        url = f"{NASA_NEO_API}/feed"
        params = {
            "start_date": datetime.now().strftime('%Y-%m-%d'),
            "end_date": datetime.now().strftime('%Y-%m-%d'),
            "api_key": NASA_API_KEY
        }
        response = requests.get(url, params=params, timeout=5)
        nasa_connected = response.status_code == 200
    except:
        pass
    
    return jsonify({
        "status": "online",
        "nasa_api_connected": nasa_connected,
        "api_key_configured": NASA_API_KEY != "BURAYA_API_ANAHTARINIZI_YAZIN",
        "endpoints": {
            "meteors": "/api/meteors/all",
            "simulate": "/api/simulate-impact",
            "warning": "/api/early-warning",
            "meteor_detail": "/api/meteor/<id>"
        }
    })

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 METEOR MADNESS - Backend Starting...")
    print("=" * 60)
    print(f"📡 NASA API Key: {'✅ Configured' if NASA_API_KEY != 'BURAYA_API_ANAHTARINIZI_YAZIN' else '❌ NOT SET'}")
    print(f"🌍 Frontend: http://127.0.0.1:5001/")
    print(f"📊 API Status: http://127.0.0.1:5001/api/status")
    print(f"🎯 Meteors: http://127.0.0.1:5001/api/meteors/all")
    print("=" * 60)
    app.run(debug=True, port=5001)