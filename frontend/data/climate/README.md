# Climate indicator datasets

The four climate monitoring pages read one JSON file per theme from this folder:

| Theme | File | Page |
|---|---|---|
| Wetland Drought | `wetland-drought.json` | `/climate/drought` |
| Precipitation Extremes | `precipitation-extremes.json` | `/climate/precipitation` |
| Heat Waves | `heat-waves.json` | `/climate/heat-waves` |
| Cold Waves | `cold-waves.json` | `/climate/cold-waves` |

If a file is missing, its page shows a "dataset not loaded" notice. The portal never estimates or fills in values. Files are checked when the site is built (`npm run build`), and a file that breaks any rule below stops the build with a message naming the problem.

## File format

```jsonc
{
  "theme": "heat-waves",              // must match the file name
  "source": "IMD gridded Tmax/Tmin, 0.25°",   // shown on the page as the data source
  "baseline": "1991–2020",            // reference period for the percentiles
  "method": "Optional one-paragraph description of how the values were computed.",
  "updated": "2026-10-01",            // optional, date the file was produced
  "years": [1991, 1992, 1993],        // one entry per year, in order
  "metrics": [
    {
      "key": "hw_days",
      "label": "Heat-wave days",
      "unit": "days/year",
      "description": "Optional — shown under the metric selector.",
      "values": {
        "2441": [null, null, null],   // Ramsar Site no. → one value per entry in "years"
        "229":  [null, null, null]
      }
    }
  ]
}
```

(The `null`s above only show the shape. Put the computed numbers there.)

Rules:

- **Site keys** are official Ramsar Site numbers, as used in `data/ramsar-sites.json` (for example Lonar Lake is `2441`, Chilika Lake is `229`). An unknown number stops the build.
- **Each values array must have exactly as many entries as `years`.** Use `null` for a year with no valid value (for example missing input data). Don't use `0` for that, because `0` means "none occurred".
- A site that is missing from a metric simply shows as "no data" (grey) on the map.
- A file can hold any number of metrics. The page offers them in the order given.

## Agreed indicator definitions

All definitions are percentile-based, following the WMO/ETCCDI approach, and use each site's own **1991–2020** baseline. They are shown on each theme page.

| Theme | Definition | Recommended metrics (`key`, unit) |
|---|---|---|
| Heat waves | ≥ 3 consecutive days with daily **Tmax above the 90th percentile** for that calendar day (15-day centred window) | `hw_events` events/year · `hw_days` days/year · `hw_max_duration` days |
| Cold waves | ≥ 3 consecutive days with daily **Tmin below the 10th percentile** for that calendar day (15-day centred window) | `cw_events` events/year · `cw_days` days/year · `cw_max_duration` days |
| Precipitation extremes | Very wet day = rainfall above the **95th percentile of wet-day (≥ 1 mm) rainfall**; dry spell = run of days with < 1 mm | `r95p` mm/year · `rx1day` mm · `cdd` days |
| Wetland drought | 3-month standardised index (**SPEI-3**, or SPI-3 without evapotranspiration) fitted to the baseline; drought month = index ≤ −1.0 | `drought_months` months/year · `min_index` index |

Use these keys where possible so the pages stay consistent across themes. Other metrics are also accepted.
