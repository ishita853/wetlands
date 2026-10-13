// Phase J — GEE reference exports for the Sentinel Hub migration.
//
// Run in the Earth Engine Code Editor with an account that can read
// projects/ee-ramsarwetlands5/assets/*. Every Export.* call appears in the
// Tasks tab; click RUN on each. Nothing here changes the GEE application.
//
// It reproduces the GEE application's own computations (Wetland App GEE Code):
//   collection : COPERNICUS/S2_SR_HARMONIZED
//   filters    : filterBounds(roi), filterDate('2022-11-01', '2026-05-30'),
//                CLOUDY_PIXEL_PERCENTAGE < 100, sort ascending by it
//   map image  : QA60 bits 10/11 masked, /10000, .first()
//   charts     : normalizedDifference, reduceRegion(mean, roi.geometry(), scale 1000)
//                per image (what ui.Chart.image.series computes), no cloud mask
//
// Outputs (Google Drive, folder "phase-j"):
//   roi_<asset>.geojson          — ROI polygons for ALL 74 assets (unsimplified)
//   scenes_<asset>.csv           — every candidate image with cloud/baseline metadata
//   map_selection_<asset>.csv    — the image .first() selects + QA60 availability
//   series_<asset>_<INDEX>.csv   — per-image ROI mean, as plotted by the GEE chart

var START = '2022-11-01';
var END = '2026-05-30';  // exclusive, as in the GEE app
var PROJECT = 'projects/ee-ramsarwetlands5/assets/';
var FOLDER = 'phase-j';

// Representative sample: small (< 1 km pixel), small-medium, large, multi-tile.
var SAMPLE = ['renuka', 'Sirpur_wetland', 'chilka', 'sundarban_wetland'];

// All 74 assets from backend/data/gee-roi-manifest.json.
var ALL_ASSETS = [
  'Ansupa_Lake', 'Asan_Conservation_Reserve', 'asthamudi', 'Bakhira_Wildlife_Sanctuary',
  'Beas_Conservation_reserve', 'Bhindawas_Wildlife_Sanctuary',
  'Bhitarkanika_Wildlife_Sanctuary_and_National_Park', 'Bhoj_wetland', 'chilka',
  'Chitrangudi_Bird_Sanctuary', 'Deepor_Beel_Bird_Sanctuary', 'east_kolkata',
  'Gulf_of_Mannar_Marine_Biosphere_Reserve', 'Haiderpur_Wetland', 'Harike_Lake_Bird_Sanctuary',
  'Hirakud_Reservoir', 'hokera', 'Hygam_Wetland_Conservation_Reserve', 'Kabartal_Wetland',
  'Kanjirankulam_Bird_Sanctuary', 'Kanjli_Lake', 'Karikili_Bird_Sanctuary',
  'Keoladeo_National_Park_and_Ajan_Bande', 'Keshopur-Miani_Community_Reserve',
  'Khijadia_Wildlife_Sanctuary', 'Kolleru_Lake_Wildlife_Sanctuary',
  'Koonthankulam_Bird_Sanctuary', 'Loktak_Lake', 'Lonar_Lake', 'Nalsarovar_Wildlife_Sanctuary',
  'Nanda_Lake', 'Nandur_Madhameshwar', 'Nangal_Wildlife_sanctuary', 'Nawabganj_Bird_Sanctuary',
  'Pala_Wetland', 'Pallikaranai_Marsh_Reserve_Forest', 'Parvati_Arga_Bird_Sanctuary',
  'Pichavaram_Mangrove', 'Point_Calimere_Wildlife_Sanctuary', 'Pong_Dam_Lake_Wildlife_Sanctuary',
  'Ranganathittu_Bird_Sanctuary', 'renuka', 'Ropar_Lake', 'Rudrasagar_Lake', 'Sakya_sagar',
  'Saman_Bird_Sanctuary', 'Samaspur_Bird_Sanctuary', 'Sambhar_Lake', 'sandi_Bird_sanctuary',
  'Sarsai_Nawar_Jheel', 'Sasthamkotta', 'Satkosia_Gorge', 'Shallbugh_Wetland_Conservation_Reserve',
  'Sirpur_wetland', 'Suchindram_Theroor_Wetland_Complex', 'Sultanpur_National_Park',
  'sundarban_wetland', 'Sur_Sarovar', 'Surinsar_Mansar', 'Tampara_Lake', 'Thane_Creek',
  'Thol_Lake_Wildlife_Sanctuary', 'Tso_Kar_Wetland_Complex', 'Tsomoriri_Lake_and_adjacent_marshes',
  'Udhayamarthandapuram_Bird_Sanctuary', 'Upper_Ganga_River', 'Vaduvur_Bird_Sanctuary',
  'Vedanthangal_Bird_Sanctuary', 'Vellode_Bird_Sanctuary', 'Vembanad_Lake',
  'Vembannur_Wetland_Complex', 'Wadhvana_Wetland', 'Wular_Lake_and_associated_marshes',
  'Yashwant_Sagar'
];

var INDICES = {
  NDCI: ['B5', 'B4'],
  NDTI: ['B3', 'B4'],
  NDWI: ['B3', 'B8'],
  NDMI: ['B8', 'B11']
};

// Identical to maskS2clouds in the GEE application.
function maskS2clouds(image) {
  var qa = image.select('QA60');
  var cloudBitMask = 1 << 10;
  var cirrusBitMask = 1 << 11;
  var mask = qa.bitwiseAnd(cloudBitMask).eq(0).and(qa.bitwiseAnd(cirrusBitMask).eq(0));
  return image.updateMask(mask).divide(10000);
}

function baseCollection(roi) {
  return ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    .filterBounds(roi)
    .filterDate(START, END)
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 100))
    .sort('CLOUDY_PIXEL_PERCENTAGE', true);
}

// 1. ROI polygons for all 74 assets.
ALL_ASSETS.forEach(function (name) {
  Export.table.toDrive({
    collection: ee.FeatureCollection(PROJECT + name),
    description: 'roi_' + name.replace(/[^A-Za-z0-9_]/g, '_'),
    folder: FOLDER,
    fileNamePrefix: name,  // -> <asset>.geojson, as backend/data/roi expects
    fileFormat: 'GeoJSON'
  });
});

SAMPLE.forEach(function (name) {
  var fc = ee.FeatureCollection(PROJECT + name);
  var roi = fc.geometry();
  var collection = baseCollection(fc);

  // 2. Candidate scenes (for cloud-cover semantics and processing baselines).
  var scenes = collection.map(function (img) {
    return ee.Feature(null, {
      image_id: img.get('system:index'),
      time_start: ee.Date(img.get('system:time_start')).format("YYYY-MM-dd'T'HH:mm:ss'Z'", 'UTC'),
      mgrs_tile: img.get('MGRS_TILE'),
      cloudy_pixel_percentage: img.get('CLOUDY_PIXEL_PERCENTAGE'),
      cloud_coverage_assessment: img.get('CLOUD_COVERAGE_ASSESSMENT'),
      processing_baseline: img.get('PROCESSING_BASELINE'),
      spacecraft: img.get('SPACECRAFT_NAME')
    });
  });
  Export.table.toDrive({
    collection: scenes, description: 'scenes_' + name, folder: FOLDER, fileFormat: 'CSV'
  });

  // 3. Map image selection (.first()) and whether QA60 masking leaves any pixels.
  var first = ee.Image(collection.first());
  var masked = maskS2clouds(first);
  var selections = ee.FeatureCollection(Object.keys(INDICES).map(function (key) {
    var bands = INDICES[key];
    var index = masked.normalizedDifference(bands).rename(key).clip(fc);
    var validPixels = index.reduceRegion({
      reducer: ee.Reducer.count(), geometry: roi, scale: 20, maxPixels: 1e10
    }).get(key);
    var qaPixels = first.select('QA60').reduceRegion({
      reducer: ee.Reducer.count(), geometry: roi, scale: 60, maxPixels: 1e10
    }).get('QA60');
    return ee.Feature(null, {
      index: key,
      image_id: first.get('system:index'),
      time_start: ee.Date(first.get('system:time_start')).format("YYYY-MM-dd'T'HH:mm:ss'Z'", 'UTC'),
      mgrs_tile: first.get('MGRS_TILE'),
      cloudy_pixel_percentage: first.get('CLOUDY_PIXEL_PERCENTAGE'),
      processing_baseline: first.get('PROCESSING_BASELINE'),
      qa60_unmasked_pixels_in_roi: qaPixels,        // 0 => QA60 masked for this image
      index_valid_pixels_in_roi_20m: validPixels    // 0 => the GEE map layer is blank
    });
  }));
  Export.table.toDrive({
    collection: selections, description: 'map_selection_' + name, folder: FOLDER,
    fileFormat: 'CSV'
  });

  // 4. Chart series: exactly the ui.Chart.image.series computation, per image.
  Object.keys(INDICES).forEach(function (key) {
    var bands = INDICES[key];
    var series = collection.map(function (img) {
      var index = img.normalizedDifference(bands).rename(key);
      var stats = index.reduceRegion({
        reducer: ee.Reducer.mean().combine(ee.Reducer.count(), '', true),
        geometry: roi, scale: 1000, maxPixels: 1e10
      });
      return ee.Feature(null, {
        image_id: img.get('system:index'),
        time_start: ee.Date(img.get('system:time_start')).format("YYYY-MM-dd'T'HH:mm:ss'Z'", 'UTC'),
        mgrs_tile: img.get('MGRS_TILE'),
        cloudy_pixel_percentage: img.get('CLOUDY_PIXEL_PERCENTAGE'),
        mean: stats.get(key + '_mean'),
        count: stats.get(key + '_count')
      });
    });
    Export.table.toDrive({
      collection: series, description: 'series_' + name + '_' + key, folder: FOLDER,
      fileFormat: 'CSV'
    });
  });
});
