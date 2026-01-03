
import json
import os

# Map filenames to ANP names as used in the HTML
anp_file_map = {
    "El Pinacate y Gran Desierto de Altar": "el_pinacate_y_gran_desierto_de_altar_boundary.geojson",
    "Marismas Nacionales Nayarit": "marismas_nacionales_nayarit_boundary.geojson",
    "Calakmul": "calakmul_boundary.geojson",
    "Montes Azules": "montes_azules_boundary.geojson",
    "Sian Ka'an": "sian_kaan_boundary.geojson",
    "Sierra Gorda": "sierra_gorda_boundary.geojson",
    "El Vizcaíno": "el_vizcaino_boundary.geojson",
    "Los Tuxtlas": "los_tuxtlas_boundary.geojson",
    "Cuatrociénegas": "cuatrocienegas_boundary.geojson",
    "Mariposa Monarca": "mariposa_monarca_boundary.geojson",
    "La Encrucijada": "la_encrucijada_boundary.geojson",
    "Tehuacán-Cuicatlán": "tehuacan_cuicatlan_boundary.geojson"
}

# Read the existing HTML
with open('gcf_esa_report.html', 'r') as f:
    html_content = f.read()

# Load GeoJSON data
geo_data = {}
for anp_name, filename in anp_file_map.items():
    filepath = os.path.join('anp_data', filename)
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            geo_data[anp_name] = data
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        geo_data[anp_name] = None

# Create the JS data string
js_geo_data = "const anpGeoJSON = " + json.dumps(geo_data) + ";"

# Prepare the new Script content (without <script> tags to make replacement easier if we slice)
new_script_content = f"""
        {js_geo_data}

        // ANP Data Object (Preserved from previous version)
        const anps = [
            {{ name: "El Pinacate y Gran Desierto de Altar", state: "Sonora", type: "Desert", area: "7,146 km²", pop: "81", indigenous: "Tohono O'odham", carbon: "6.1 Mt", stress: "Extremely High", coords: [31.905, -113.763], desc: "A UNESCO World Heritage site featuring massive craters and dunes. Culturally sacred to the Tohono O'odham. Faces extreme heat and water scarcity." }},
            {{ name: "Marismas Nacionales Nayarit", state: "Nayarit", type: "Wetlands/Mangroves", area: "1,339 km²", pop: "3,241", indigenous: "Mayo/Cora nearby", carbon: "9.0 Mt", stress: "Extremely High", coords: [22.113, -105.514], desc: "Massive mangrove system critical for fisheries and carbon storage. Threats include aquaculture expansion and upstream water diversion." }},
            {{ name: "Calakmul", state: "Campeche", type: "Tropical Forest", area: "7,232 km²", pop: "3,110", indigenous: "Maya", carbon: "96.4 Mt", stress: "Low", coords: [18.364, -89.651], desc: "Mexico's largest tropical forest reserve, adjacent to Maya ruins. Critical corridor for jaguar. High social lag in surrounding communities." }},
            {{ name: "Montes Azules", state: "Chiapas", type: "Tropical Rainforest", area: "3,312 km²", pop: "24,520", indigenous: "Lacandón, Tseltal, Chol", carbon: "118.1 Mt", stress: "Low", coords: [16.471, -91.139], desc: "The heart of the Lacandon Jungle. Highest biodiversity per hectare. Complex social context with indigenous land tenure overlaps." }},
            {{ name: "Sian Ka'an", state: "Quintana Roo", type: "Coastal/Forest", area: "5,280 km²", pop: "993", indigenous: "Maya", carbon: "26.6 Mt", stress: "Low-Medium", coords: [19.526, -87.658], desc: "UNESCO site with diverse marine, wetland, and forest ecosystems. Tourism pressure from Riviera Maya is a key management challenge." }},
            {{ name: "Sierra Gorda", state: "Querétaro", type: "Temperate/Cloud Forest", area: "3,836 km²", pop: "99,987", indigenous: "Otomi, Pame", carbon: "72.0 Mt", stress: "Low-Medium", coords: [21.289, -99.478], desc: "Ecologically diverse range with cloud forests. 'Alliance for Sierra Gorda' provides a strong model for participatory conservation." }},
            {{ name: "El Vizcaíno", state: "Baja California Sur", type: "Desert/Marine", area: "25,468 km²", pop: "54,318", indigenous: "Low presence", carbon: "64.3 Mt", stress: "Extremely High", coords: [27.444, -113.616], desc: "Mexico's largest ANP. Critical for Gray Whale breeding. Economy driven by salt production, fishing, and tourism. Very arid." }},
            {{ name: "Los Tuxtlas", state: "Veracruz", type: "Rainforest", area: "1,551 km²", pop: "31,118", indigenous: "Nahua, Popoluca", carbon: "33.0 Mt", stress: "Low", coords: [18.465, -94.986], desc: "Isolated volcanic range with unique rainforest. High deforestation pressure from cattle ranching. Strong academic research history." }},
            {{ name: "Cuatrociénegas", state: "Coahuila", type: "Desert Wetland", area: "843 km²", pop: "327", indigenous: "Low", carbon: "2.5 Mt", stress: "Extremely High", coords: [26.898, -102.089], desc: "A 'living laboratory' with unique aquatic endemism in the desert. Critical threat from groundwater extraction for agriculture." }},
            {{ name: "Mariposa Monarca", state: "Michoacán/EdoMex", type: "Temperate Forest", area: "563 km²", pop: "35,614", indigenous: "Mazahua, Otomí", carbon: "21.1 Mt", stress: "High", coords: [19.551, -100.257], desc: "Overwintering site for the Monarch butterfly. High social complexity, illegal logging risks, and strong community forest management." }},
            {{ name: "La Encrucijada", state: "Chiapas", type: "Mangroves", area: "1,449 km²", pop: "15,181", indigenous: "Low (migrant labor)", carbon: "77.3 Mt", stress: "Low", coords: [15.198, -92.852], desc: "Home to the tallest mangroves in the Americas. Vital for local fisheries. Vulnerable to sedimentation and palm oil expansion nearby." }},
            {{ name: "Tehuacán-Cuicatlán", state: "Puebla/Oaxaca", type: "Arid/Cactus", area: "4,902 km²", pop: "48,423", indigenous: "Mixtec, Popoloca, Cuicatec", carbon: "124.7 Mt", stress: "Low-Medium", coords: [18.047, -97.245], desc: "Center of agave and cactus diversity. Ancient agricultural history. High cultural significance and indigenous population." }}
        ];

        function getColor(type) {{
            if(type.includes("Desert")) return "#e67e22";
            if(type.includes("Rainforest") || type.includes("Tropical")) return "#27ae60";
            if(type.includes("Coastal") || type.includes("Mangrove") || type.includes("Wetland")) return "#2980b9";
            return "#8e44ad";
        }}

        // Generate ANP Cards with individual maps
        const container = document.getElementById('anp-cards-container');
        
        // Main Overview Map
        const map = L.map('map', {{
            zoomControl: false,
            dragging: false,
            scrollWheelZoom: false,
            doubleClickZoom: false,
            touchZoom: false,
            attributionControl: false
        }}).setView([23.6345, -102.5528], 5);
        
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '&copy; OpenStreetMap &copy; CARTO'
        }}).addTo(map);

        // Add all polygons to main map
        const allBounds = [];
        anps.forEach(anp => {{
            const geojson = anpGeoJSON[anp.name];
            if (geojson) {{
                const layer = L.geoJSON(geojson, {{
                    style: {{
                        color: getColor(anp.type),
                        weight: 2,
                        opacity: 1,
                        fillOpacity: 0.5
                    }}
                }}).addTo(map);
                allBounds.push(layer.getBounds());
            }}
        }});
        
        if (allBounds.length > 0) {{
            // Fit bounds to show all Mexico ANPs
             // Calculate overall bounds
             let overallBounds = allBounds[0];
             for(let i=1; i<allBounds.length; i++) {{
                 overallBounds.extend(allBounds[i]);
             }}
             map.fitBounds(overallBounds, {{padding: [20, 20]}});
        }}


        // Generate Individual Cards & Maps
        anps.forEach((anp, index) => {{
            const card = document.createElement('div');
            card.className = 'anp-card';
            // Unique ID for the map div
            const mapId = 'map-' + index;
            
            card.innerHTML = `
                <div class="anp-header">
                    <span class="anp-title">${{anp.name}}</span>
                    <span class="stat-label" style="background:${{getColor(anp.type)}}; color:white; padding:2px 8px; border-radius:4px;">${{anp.type}}</span>
                </div>
                <div style="display:flex; gap:20px; align-items:flex-start;">
                    <div style="flex:1;">
                        <p>${{anp.desc}}</p>
                        <div class="anp-stats">
                            <div class="stat-item"><span class="stat-label">State</span>${{anp.state}}</div>
                            <div class="stat-item"><span class="stat-label">Area</span>${{anp.area}}</div>
                            <div class="stat-item"><span class="stat-label">Est. Pop</span>${{anp.pop}}</div>
                            <div class="stat-item"><span class="stat-label">Indigenous</span>${{anp.indigenous}}</div>
                            <div class="stat-item"><span class="stat-label">Carbon</span>${{anp.carbon}}</div>
                            <div class="stat-item"><span class="stat-label">Water Stress</span>${{anp.stress}}</div>
                        </div>
                    </div>
                    <div id="${{mapId}}" style="width: 300px; height: 200px; border-radius: 4px; border:1px solid #ccc;"></div>
                </div>
            `;
            container.appendChild(card);

            // Initialize individual map
            setTimeout(() => {{
                const miniMap = L.map(mapId, {{
                    zoomControl: false,
                    dragging: false,
                    scrollWheelZoom: false,
                    doubleClickZoom: false,
                    touchZoom: false,
                    attributionControl: false
                }});
                
                L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
                }}).addTo(miniMap);

                const geojson = anpGeoJSON[anp.name];
                if (geojson) {{
                    const layer = L.geoJSON(geojson, {{
                        style: {{
                            color: getColor(anp.type),
                            weight: 2,
                            fillOpacity: 0.6
                        }}
                    }}).addTo(miniMap);
                    miniMap.fitBounds(layer.getBounds());
                }} else {{
                    miniMap.setView(anp.coords, 8);
                }}
            }}, 100);
        }});
"""

start_marker = "<script>"
end_marker = "</script>"

start_idx = html_content.find(start_marker)
end_idx = html_content.find(end_marker, start_idx)

if start_idx != -1 and end_idx != -1:
    new_html = html_content[:start_idx] + "<script>" + new_script_content + html_content[end_idx:]
    with open('gcf_esa_report.html', 'w') as f:
        f.write(new_html)
    print("Updated gcf_esa_report.html with polygon maps.")
else:
    print("Could not find script tags to replace.")
