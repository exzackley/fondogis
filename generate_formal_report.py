
import json
import os

# ANP Data (Metadata used for narrative generation)
anps = [
    {
        "name": "El Pinacate y Gran Desierto de Altar",
        "state": "Sonora",
        "type": "Desert",
        "area": "7,146",
        "pop": "81",
        "indigenous": "Tohono O'odham",
        "carbon": "6.1",
        "stress": "Extremely High",
        "coords": [31.905, -113.763],
        "desc": "A UNESCO World Heritage site comprising massive craters, dunes, and volcanic shields. It holds immense cultural value for the Tohono O'odham Nation, whose sacred sites are distributed throughout the landscape. The area is characterized by extreme aridity and high temperatures.",
        "risk_narrative": "Primary risks involve the management of scarce water resources and the protection of sacred indigenous sites from unauthorized access or tourism impacts. Climate change exacerbates the already extreme water stress."
    },
    {
        "name": "Marismas Nacionales Nayarit",
        "state": "Nayarit",
        "type": "Wetlands/Mangroves",
        "area": "1,339",
        "pop": "3,241",
        "indigenous": "Mayo and Cora communities nearby",
        "carbon": "9.0",
        "stress": "Extremely High",
        "coords": [22.113, -105.514],
        "desc": "This extensive mangrove system acts as a critical biological corridor and carbon sink. It supports significant local fisheries which are the economic backbone of surrounding communities. The ecosystem is a mosaic of brackish lagoons and tidal channels.",
        "risk_narrative": "The area is vulnerable to upstream water diversion and aquaculture expansion. Social risks are tied to the regulation of fishing activities, which requires careful consultation with local cooperatives to avoid economic displacement."
    },
    {
        "name": "Calakmul",
        "state": "Campeche",
        "type": "Tropical Forest",
        "area": "7,232",
        "pop": "3,110",
        "indigenous": "Maya",
        "carbon": "96.4",
        "stress": "Low",
        "coords": [18.364, -89.651],
        "desc": "As Mexico's largest tropical forest reserve, Calakmul protects a vast tract of the Selva Maya and ancient Maya archaeological sites. It serves as a vital corridor for the jaguar and other endangered fauna. The region is marked by high social marginalization.",
        "risk_narrative": "Agricultural encroachment and illegal logging are persistent threats. Project activities must navigate complex ejido land tenure systems and ensure equitable benefit-sharing with Maya communities to prevent social conflict."
    },
    {
        "name": "Montes Azules",
        "state": "Chiapas",
        "type": "Tropical Rainforest",
        "area": "3,312",
        "pop": "24,520",
        "indigenous": "Lacandón, Tseltal, Chol",
        "carbon": "118.1",
        "stress": "Low",
        "coords": [16.471, -91.139],
        "desc": "Located in the heart of the Lacandon Jungle, this reserve harbors the highest biodiversity per hectare in the country. It is deeply intertwined with the territories of the Lacandón, Tseltal, and Chol peoples.",
        "risk_narrative": "The area has a history of complex agrarian conflicts and overlapping land claims. Any intervention requires rigorous adherence to Free, Prior, and Informed Consent (FPIC) principles and conflict-sensitive management."
    },
    {
        "name": "Sian Ka'an",
        "state": "Quintana Roo",
        "type": "Coastal/Forest",
        "area": "5,280",
        "pop": "993",
        "indigenous": "Maya",
        "carbon": "26.6",
        "stress": "Low-Medium",
        "coords": [19.526, -87.658],
        "desc": "A UNESCO World Heritage site, Sian Ka'an encompasses a complex hydrological system of petenes (tree islands), marshes, and barrier reefs. It is under increasing pressure from the tourism industry of the adjacent Riviera Maya.",
        "risk_narrative": "Managing tourism impacts and ensuring that economic benefits reach local Maya communities rather than external operators is a key challenge. Groundwater contamination from regional development poses a systemic threat."
    },
    {
        "name": "Sierra Gorda",
        "state": "Querétaro",
        "type": "Temperate/Cloud Forest",
        "area": "3,836",
        "pop": "99,987",
        "indigenous": "Otomi, Pame",
        "carbon": "72.0",
        "stress": "Low-Medium",
        "coords": [21.289, -99.478],
        "desc": "This biologically diverse mountain range features a transition from semi-arid scrub to cloud forests. It is home to a significant population living within the reserve, making it a model for participatory conservation management.",
        "risk_narrative": "With a large resident population, the primary risk involves balancing strict conservation measures with the subsistence needs of Otomi and Pame communities. Fire management is also a critical safety concern."
    },
    {
        "name": "El Vizcaíno",
        "state": "Baja California Sur",
        "type": "Desert/Marine",
        "area": "25,468",
        "pop": "54,318",
        "indigenous": "Low presence",
        "carbon": "64.3",
        "stress": "Extremely High",
        "coords": [27.444, -113.616],
        "desc": "Mexico's largest protected area, encompassing vast desert plains and coastal lagoons critical for Gray Whale breeding. The local economy is driven by salt production, fishing, and nature-based tourism.",
        "risk_narrative": "Industrial salt production and tourism require careful regulation to prevent habitat degradation. Water scarcity is a defining constraint for all human and biological systems in the reserve."
    },
    {
        "name": "Los Tuxtlas",
        "state": "Veracruz",
        "type": "Rainforest",
        "area": "1,551",
        "pop": "31,118",
        "indigenous": "Nahua, Popoluca",
        "carbon": "33.0",
        "stress": "Low",
        "coords": [18.465, -94.986],
        "desc": "An isolated volcanic mountain range rising from the Gulf coast, preserving the northernmost neotropical rainforest. The area faces heavy deforestation pressure from cattle ranching but benefits from a strong history of academic research.",
        "risk_narrative": "Conversion of forest to pasture is the main driver of loss. Interventions must focus on sustainable intensification of existing agricultural lands to reduce expansion pressure, working closely with Nahua and Popoluca ejidos."
    },
    {
        "name": "Cuatrociénegas",
        "state": "Coahuila",
        "type": "Desert Wetland",
        "area": "843",
        "pop": "327",
        "indigenous": "Low presence",
        "carbon": "2.5",
        "stress": "Extremely High",
        "coords": [26.898, -102.089],
        "desc": "A unique desert wetland system known as a 'living laboratory' due to its high endemism and stromatolites. It relies on an intricate groundwater system that is under threat from regional agricultural extraction.",
        "risk_narrative": "The critical risk is the depletion of the aquifer by adjacent alfalfa farming. Conservation success depends on water governance and engaging with water users outside the reserve boundaries."
    },
    {
        "name": "Mariposa Monarca",
        "state": "Michoacán/EdoMex",
        "type": "Temperate Forest",
        "area": "563",
        "pop": "35,614",
        "indigenous": "Mazahua, Otomí",
        "carbon": "21.1",
        "stress": "High",
        "coords": [19.551, -100.257],
        "desc": "The overwintering site for the Monarch butterfly, protecting high-altitude oyamel fir forests. The region presents high social complexity with strong community forest management structures but also pressures from illegal logging.",
        "risk_narrative": "Social risks are high due to the economic value of timber and avocado expansion. Security for environmental defenders and equitable distribution of tourism revenues are central concerns."
    },
    {
        "name": "La Encrucijada",
        "state": "Chiapas",
        "type": "Mangroves",
        "area": "1,449",
        "pop": "15,181",
        "indigenous": "Low (migrant labor presence)",
        "carbon": "77.3",
        "stress": "Low",
        "coords": [15.198, -92.852],
        "desc": "This reserve protects the tallest mangroves in the Americas and vast coastal wetlands. It is vital for local fisheries and acts as a buffer against coastal storms.",
        "risk_narrative": "Sedimentation from upstream deforestation and potential pollution from palm oil plantations are key external threats. Management must address the livelihoods of fishing communities to ensure sustainability."
    },
    {
        "name": "Tehuacán-Cuicatlán",
        "state": "Puebla/Oaxaca",
        "type": "Arid/Cactus",
        "area": "4,902",
        "pop": "48,423",
        "indigenous": "Mixtec, Popoloca, Cuicatec",
        "carbon": "124.7",
        "stress": "Low-Medium",
        "coords": [18.047, -97.245],
        "desc": "The center of global agave and cactus diversity with a deep history of human agriculture. It is a cultural landscape inhabited by Mixtec, Popoloca, and Cuicatec peoples maintaining traditional land use practices.",
        "risk_narrative": "Cultural heritage preservation is as important here as biodiversity. Risks involve the loss of traditional ecological knowledge and unsustainable harvesting of endemic plant species."
    }
]

# Map filenames to ANP names
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

# CSS for the formal report
css = """
    <style>
        body { 
            font-family: "Times New Roman", Times, serif; 
            line-height: 1.5; 
            color: #000; 
            max-width: 900px; 
            margin: 0 auto; 
            padding: 40px; 
            background-color: #fff;
        }
        h1, h2, h3, h4 { 
            color: #000; 
            font-family: Arial, sans-serif;
            margin-top: 2em;
            margin-bottom: 1em;
        }
        h1 { font-size: 24pt; text-align: center; margin-bottom: 2em; border: none; }
        h2 { font-size: 16pt; border-bottom: 1px solid #000; padding-bottom: 5px; }
        h3 { font-size: 14pt; margin-top: 30px; font-weight: bold; }
        p { text-align: justify; margin-bottom: 1em; font-size: 11pt; }
        
        table { width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 10pt; page-break-inside: avoid; }
        th, td { padding: 8px 12px; border: 1px solid #000; text-align: left; }
        th { background-color: #f0f0f0; font-weight: bold; }
        
        .map-container { 
            width: 100%; 
            height: 350px; 
            border: 1px solid #999; 
            margin: 20px 0; 
            page-break-inside: avoid; 
        }
        
        .overview-map { height: 600px; }
        
        .document-title { text-align: center; margin-bottom: 50px; }
        .document-meta { text-align: center; font-style: italic; margin-bottom: 50px; }
        
        .references { font-size: 10pt; margin-top: 20px; }
        .references li { margin-bottom: 8px; }
        sup { font-size: 0.8em; }
        
        /* Print adjustments */
        @media print {
            body { padding: 0; max-width: 100%; }
            .section-break { page-break-before: always; }
            h2 { page-break-after: avoid; }
            .anp-section { page-break-inside: avoid; }
        }
        
        .anp-profile { margin-bottom: 40px; border-bottom: 1px solid #eee; padding-bottom: 20px; }
        .figure-caption { text-align: center; font-style: italic; font-size: 0.9em; color: #444; margin-top: 5px; }
    </style>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
"""

# HTML Content Construction
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Annex 6: Environmental and Social Assessment</title>
    {css}
</head>
<body>

    <div class="document-title">
        <h1>FUNDING PROPOSAL<br>ANNEX 6: ENVIRONMENTAL AND SOCIAL ASSESSMENT</h1>
        <div class="document-meta">
            <strong>Project:</strong> Strengthening Resilience in Mexican Natural Protected Areas<br>
            <strong>Date:</strong> January 2026<br>
            <strong>Country:</strong> Mexico
        </div>
    </div>

    <h2>1. Executive Summary</h2>
    <p>
        This Environmental and Social Assessment (ESA) has been prepared for the Green Climate Fund (GCF) funding proposal targeting a portfolio of 12 Natural Protected Areas (ANPs) in Mexico. The project encompasses a total area of approximately 2.64 million hectares, representing diverse ecosystems ranging from the arid deserts of the north to the tropical rainforests and coastal mangroves of the south.
    </p>
    <p>
        The assessment classifies the project as <strong>Category B</strong> (medium risk) under the GCF Environmental and Social Policy. The primary environmental and social risks identified relate to potential restrictions on access to natural resources (Performance Standard 5) and impacts on Indigenous Peoples (Performance Standard 7). Approximately 117,400 indigenous speakers reside within the direct influence zones of these reserves<sup><a href="#ref1">1</a></sup>. The project incorporates an Indigenous Peoples Planning Framework (IPPF) and a Process Framework to ensure that any changes in management regimes are developed through participatory planning and Free, Prior, and Informed Consent (FPIC) where applicable.
    </p>

    <h2>2. Project Description and Scope</h2>
    <p>
        The proposed project aims to enhance climate resilience and conserve carbon stocks across 12 federal ANPs. These areas were selected based on their high mitigation potential, biodiversity value, and vulnerability to climate change impacts such as drought, sea-level rise, and increased fire intensity. The portfolio includes four desert reserves, three tropical forests, three coastal/wetland systems, and two temperate forest reserves.
    </p>
    <p>
        Interventions will focus on ecosystem restoration, strengthening monitoring and enforcement capacities, and supporting sustainable community livelihoods. All activities will be implemented in partnership with the National Commission of Natural Protected Areas (CONANP)<sup><a href="#ref4">4</a></sup> and local community organizations.
    </p>

    <h2>3. Environmental and Social Baseline</h2>
    <p>
        The project area covers a wide range of socio-economic and environmental contexts. The total population living within the municipalities intersecting the 12 ANPs is estimated at 3.65 million, with approximately 308,000 people residing directly within the ANP localities<sup><a href="#ref1">1</a></sup>. Social vulnerability is analyzed using the Social Lag Index<sup><a href="#ref5">5</a></sup>.
    </p>
    
    <h3>3.1 Environmental Profile</h3>
    <p>
        The aggregate carbon stock of the 12 ANPs is estimated at 517 Megatonnes (Mt)<sup><a href="#ref2">2</a></sup>, with the highest densities found in the tropical forests of Montes Azules and the mangrove systems of Marismas Nacionales and La Encrucijada. Conversely, the arid reserves of El Pinacate and Cuatrociénegas serve as critical reservoirs of soil carbon despite lower above-ground biomass.
    </p>
    <p>
        Water stress varies significantly across the portfolio. The northern reserves (El Pinacate, Cuatrociénegas, El Vizcaíno) experience "Extremely High" baseline water stress, with withdrawal rates exceeding 80% of available supply<sup><a href="#ref3">3</a></sup>. In contrast, the southern coastal reserves face risks associated with flooding and hydrometeorological events.
    </p>

    <h3>3.2 Summary Table: Protected Area Characteristics</h3>
    <table>
        <thead>
            <tr>
                <th>Protected Area</th>
                <th>State</th>
                <th>Ecosystem</th>
                <th>Area (km²)</th>
                <th>Est. Carbon (Mt)</th>
                <th>Water Stress</th>
            </tr>
        </thead>
        <tbody>
"""

# Add rows to the table
for anp in anps:
    html += f"""
            <tr>
                <td>{anp['name']}</td>
                <td>{anp['state']}</td>
                <td>{anp['type']}</td>
                <td>{anp['area']}</td>
                <td>{anp['carbon']}</td>
                <td>{anp['stress']}</td>
            </tr>
    """

html += """
        </tbody>
    </table>

    <div class="section-break"></div>
    
    <h2>4. Protected Area Profiles</h2>
    <p>This section provides a detailed profile of each of the 12 Natural Protected Areas included in the project scope, outlining their environmental significance and social context.</p>
"""

# Add Narrative Profiles
for i, anp in enumerate(anps):
    map_id = f"map-{i}"
    html += f"""
    <div class="anp-profile anp-section">
        <h3>4.{i+1} {anp['name']}</h3>
        <p>
            <strong>Location and Scope:</strong> {anp['name']} is located in the state of {anp['state']} and covers a total area of approximately {anp['area']} km². It is classified primarily as a {anp['type']} ecosystem. The area has an estimated resident population of {anp['pop']}<sup><a href="#ref1">1</a></sup>.
        </p>
        <p>
            <strong>Environmental Context:</strong> {anp['desc']} The area faces specific climate vulnerabilities; in particular, its water stress level is categorized as "{anp['stress']}"<sup><a href="#ref3">3</a></sup>. Biodiversity data indicates high significance for conservation<sup><a href="#ref6">6</a></sup>.
        </p>
        <p>
            <strong>Social Context:</strong> The reserve is socially significant, with a presence of {anp['indigenous']}. {anp['risk_narrative']}
        </p>
        <div id="{map_id}" class="map-container"></div>
        <div class="figure-caption">Figure 4.{i+1}: Boundary map of {anp['name']} (Source: CONANP SIMEC)</div>
    </div>
    """

html += """
    <div class="section-break"></div>

    <h2>5. Environmental and Social Risks and Impacts</h2>
    <p>
        <strong>Biodiversity (PS6):</strong> While the project aims to conserve biodiversity, implementation activities such as restoration or infrastructure maintenance could cause temporary disturbances. These risks are mitigated through strict adherence to management plans and the avoidance of breeding seasons during field work.
    </p>
    <p>
        <strong>Indigenous Peoples (PS7):</strong> Ten of the twelve ANPs have indigenous populations living within or near their boundaries. There is a risk that strengthened enforcement of conservation rules could inadvertently restrict access to traditional resources. To address this, the project will implement a Process Framework to ensure that any restriction of access is negotiated and compensated through alternative livelihood measures.
    </p>
    <p>
        <strong>Community Health and Safety (PS4):</strong> Increased patrolling and surveillance activities carry potential risks of conflict between rangers and illegal resource users. The project will provide training on human rights and conflict resolution for all enforcement personnel.
    </p>

    <h2>6. Geographic Scope</h2>
    <p>The following map illustrates the geographic distribution of the 12 Protected Areas across Mexico.</p>
    <div id="overview-map" class="map-container overview-map"></div>
    <div class="figure-caption">Figure 6.1: Overview of Project Sites in Mexico</div>

    <div class="section-break"></div>
    
    <h2>7. References</h2>
    <ol class="references">
        <li id="ref1">Instituto Nacional de Estadística y Geografía (INEGI). (2020). <em>Censo de Población y Vivienda 2020</em>. Mexico.</li>
        <li id="ref2">Dubayah, R., et al. (2022). <em>GEDI L4A Footprint Level Aboveground Biomass Density, Version 2.1</em>. NASA EOSDIS Land Processes DAAC.</li>
        <li id="ref3">Hofste, R., et al. (2019). <em>Aqueduct 3.0: Updated Decision-Relevant Global Water Risk Indicators</em>. World Resources Institute.</li>
        <li id="ref4">Comisión Nacional de Áreas Naturales Protegidas (CONANP). (2024). <em>Sistema de Información, Monitoreo y Evaluación para la Conservación (SIMEC)</em>.</li>
        <li id="ref5">Consejo Nacional de Evaluación de la Política de Desarrollo Social (CONEVAL). (2020). <em>Índice de Rezago Social 2020 a nivel municipal y por localidad</em>.</li>
        <li id="ref6">Global Biodiversity Information Facility (GBIF) & iNaturalist. (2024). <em>Biodiversity Occurrence Data</em>.</li>
    </ol>

    <script>
        const anpGeoJSON = """ + json.dumps(geo_data) + """;
        const anps = """ + json.dumps(anps) + """;

        function getColor(type) {
            if(type.includes("Desert")) return "#d35400"; // Darker orange for print
            if(type.includes("Rainforest") || type.includes("Tropical")) return "#27ae60";
            if(type.includes("Coastal") || type.includes("Mangrove") || type.includes("Wetland")) return "#2980b9";
            return "#8e44ad";
        }

        // Initialize Individual Maps
        anps.forEach((anp, index) => {
            const mapId = 'map-' + index;
            // Delay slightly to ensure render
            setTimeout(() => {
                const map = L.map(mapId, {
                    zoomControl: false,
                    attributionControl: false,
                    dragging: false,
                    scrollWheelZoom: false,
                    doubleClickZoom: false,
                    touchZoom: false
                });
                
                // Simple B&W or muted tiles for professional print look
                L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
                    opacity: 0.6
                }).addTo(map);

                const geojson = anpGeoJSON[anp.name];
                if (geojson) {
                    const layer = L.geoJSON(geojson, {
                        style: {
                            color: "#333",       // Dark border
                            weight: 2,
                            fillColor: getColor(anp.type),
                            fillOpacity: 0.4
                        }
                    }).addTo(map);
                    map.fitBounds(layer.getBounds());
                } else {
                    map.setView(anp.coords, 8);
                }
            }, 100 + (index * 50));
        });

        // Initialize Overview Map
        setTimeout(() => {
            const map = L.map('overview-map', {
                zoomControl: false,
                attributionControl: false,
                dragging: false,
                scrollWheelZoom: false
            }).setView([23.6345, -102.5528], 5);

            L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
                opacity: 1.0
            }).addTo(map);

            const allBounds = [];
            anps.forEach(anp => {
                const geojson = anpGeoJSON[anp.name];
                if (geojson) {
                    const layer = L.geoJSON(geojson, {
                        style: {
                            color: getColor(anp.type),
                            weight: 1,
                            fillOpacity: 0.6
                        }
                    }).addTo(map);
                    allBounds.push(layer.getBounds());
                }
            });

            if (allBounds.length > 0) {
                let overallBounds = allBounds[0];
                for(let i=1; i<allBounds.length; i++) {
                    overallBounds.extend(allBounds[i]);
                }
                map.fitBounds(overallBounds, {padding: [50, 50]});
            }
        }, 1000);

    </script>
</body>
</html>
"""

with open('gcf_esa_appendix_formal.html', 'w') as f:
    f.write(html)

print("Created gcf_esa_appendix_formal.html")
