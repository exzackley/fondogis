-- FondoGIS Database Schema
-- PostgreSQL 13+ (PostGIS optional)
-- Run this after creating the fondogis database

-- Note: PostGIS is optional. If available, uncomment the next line:
-- CREATE EXTENSION IF NOT EXISTS postgis;

-- Core ANP table with queryable columns
CREATE TABLE IF NOT EXISTS anps (
    id TEXT PRIMARY KEY,                    -- "calakmul", "sierra_gorda"
    name TEXT NOT NULL,                     -- "Calakmul"
    designation TEXT,                       -- "Reserva de la Biósfera"
    designation_type TEXT,                  -- "RB", "PN", "APFF", "Sant", "APRN", "MN"
    area_km2 NUMERIC,
    area_terrestrial_ha NUMERIC,
    area_marine_ha NUMERIC,
    wdpa_id INTEGER,
    conanp_id TEXT,
    estados TEXT[],                         -- {"Campeche", "Quintana Roo"}
    region TEXT,
    iucn_category TEXT,
    governance TEXT,
    management_authority TEXT,
    primer_decreto DATE,                    -- First decree date

    -- Computed/derived fields
    is_marine BOOLEAN DEFAULT FALSE,
    is_coastal BOOLEAN DEFAULT FALSE,

    -- Geometry stored as JSONB (can convert to PostGIS later if needed)
    centroid JSONB,                         -- [lon, lat]
    bounds JSONB,                           -- [[lon, lat], ...]

    -- Full metadata as JSONB for anything else
    metadata JSONB,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Dataset storage with JSONB
-- Each ANP can have multiple dataset types (population, forest, climate, etc.)
CREATE TABLE IF NOT EXISTS anp_datasets (
    id SERIAL PRIMARY KEY,
    anp_id TEXT NOT NULL REFERENCES anps(id) ON DELETE CASCADE,
    dataset_type TEXT NOT NULL,             -- "population", "forest", "climate_projections", etc.
    data JSONB NOT NULL,                    -- Full nested structure for this dataset
    source TEXT,                            -- "gee", "gbif", "inaturalist", "simec", "inegi", etc.
    extracted_at TIMESTAMPTZ,

    UNIQUE(anp_id, dataset_type)
);

-- Boundary geometries (separate table due to size - some are 5+ MB)
CREATE TABLE IF NOT EXISTS anp_boundaries (
    anp_id TEXT PRIMARY KEY REFERENCES anps(id) ON DELETE CASCADE,
    geojson JSONB NOT NULL,                 -- Full GeoJSON for export and rendering
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Extraction audit log
CREATE TABLE IF NOT EXISTS extraction_log (
    id SERIAL PRIMARY KEY,
    anp_id TEXT REFERENCES anps(id) ON DELETE SET NULL,
    dataset_type TEXT,
    script_name TEXT NOT NULL,
    status TEXT NOT NULL,                   -- "success", "error", "skipped"
    error_message TEXT,
    rows_affected INTEGER,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_anps_designation ON anps(designation_type);
CREATE INDEX IF NOT EXISTS idx_anps_estados ON anps USING GIN(estados);
CREATE INDEX IF NOT EXISTS idx_anps_name ON anps(name);
CREATE INDEX IF NOT EXISTS idx_anps_region ON anps(region);

CREATE INDEX IF NOT EXISTS idx_anp_datasets_anp ON anp_datasets(anp_id);
CREATE INDEX IF NOT EXISTS idx_anp_datasets_type ON anp_datasets(dataset_type);
CREATE INDEX IF NOT EXISTS idx_anp_datasets_source ON anp_datasets(source);
CREATE INDEX IF NOT EXISTS idx_anp_datasets_data ON anp_datasets USING GIN(data);

CREATE INDEX IF NOT EXISTS idx_boundaries_anp ON anp_boundaries(anp_id);

CREATE INDEX IF NOT EXISTS idx_extraction_log_anp ON extraction_log(anp_id);
CREATE INDEX IF NOT EXISTS idx_extraction_log_status ON extraction_log(status);
CREATE INDEX IF NOT EXISTS idx_extraction_log_time ON extraction_log(started_at);

-- Helper function to update timestamps
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for auto-updating timestamps
DROP TRIGGER IF EXISTS anps_updated_at ON anps;
CREATE TRIGGER anps_updated_at
    BEFORE UPDATE ON anps
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- View for quick ANP overview with dataset counts
CREATE OR REPLACE VIEW anp_overview AS
SELECT
    a.id,
    a.name,
    a.designation_type,
    a.area_km2,
    a.estados,
    a.region,
    COUNT(d.id) as dataset_count,
    ARRAY_AGG(DISTINCT d.dataset_type) FILTER (WHERE d.dataset_type IS NOT NULL) as available_datasets,
    MAX(d.extracted_at) as last_extraction,
    a.updated_at
FROM anps a
LEFT JOIN anp_datasets d ON a.id = d.anp_id
GROUP BY a.id;

-- View for dataset coverage analysis
CREATE OR REPLACE VIEW dataset_coverage AS
SELECT
    d.dataset_type,
    COUNT(DISTINCT d.anp_id) as anp_count,
    COUNT(DISTINCT d.anp_id)::float / (SELECT COUNT(*) FROM anps) * 100 as coverage_percent,
    MIN(d.extracted_at) as oldest_extraction,
    MAX(d.extracted_at) as newest_extraction
FROM anp_datasets d
GROUP BY d.dataset_type
ORDER BY anp_count DESC;

COMMENT ON TABLE anps IS 'Core table for Mexico''s 227+ federal protected areas (ANPs)';
COMMENT ON TABLE anp_datasets IS 'Environmental datasets for each ANP (population, forest, climate, etc.)';
COMMENT ON TABLE anp_boundaries IS 'Full boundary geometries stored separately due to size';
COMMENT ON TABLE extraction_log IS 'Audit trail of data extraction operations';
