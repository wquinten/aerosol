import streamlit as st
from datetime import datetime, timedelta
import cdsapi

# -------------------------------------------------------------------
# Cached function to download the forecast data once and reuse it
# -------------------------------------------------------------------
@st.cache_data(show_spinner=True)
def get_forecast_data():
    """
    Chooses the latest valid forecast (using either 00:00 or 12:00 UTC)
    and downloads the forecast file.
    Returns a tuple: (path to downloaded file, forecast_date, forecast_hour).
    """
    now = datetime.utcnow()

    # (base time + max lead time) is already in the past, we roll to the next day.
    # Get current time
    now = datetime.utcnow()

    # Determine which model run to use based on current time
    if now.hour < 12:
        # If current hour is before 12:00, use previous day's 12:00 run
        base_time = datetime(now.year, now.month, now.day, 12, 0) -timedelta(days=1)
    else:
        # If current hour is 12:00 or later, use current day's 00:00 run
        base_time = datetime(now.year, now.month, now.day, 0, 0)

    # Format the date and hour for the API request
    forecast_date = base_time.strftime("%Y-%m-%d")
    forecast_hour = base_time.strftime("%H:%M")
    
    # For debugging/information
    st.write(f"Current time (UTC): {now}")
    st.write(f"Using model run from: {base_time}")

    # Prepare the request
    request = {
        "variable": [
            "aerosol_extinction_coefficient_1064nm",
        ],
        "pressure_level": [
            "800", "850", "900", "925", "950", "1000"
        ],
        "date": [forecast_date],
        "time": [forecast_hour],
        "leadtime_hour": [
            "3",
            "6",
            "9",
            "12",
            "15",
            "18",
            "21",
            "24",
            "27",
            "30",
            "33",
            "36",
            "39",
            "42",
            "45",
            "48",
            "51"
        ],
        "type": ["forecast"],
        "data_format": "grib",
        "area": [30, 30, 9, 50]
    }

    # Create CDS API client and download data
    client = cdsapi.Client()
    output_file = "forecast.grib"
    client.retrieve("cams-global-atmospheric-composition-forecasts", request).download(output_file)

    return output_file, forecast_date, forecast_hour

# -------------------------------------------------------------------
# Main Streamlit app
# -------------------------------------------------------------------
st.title("Atmospheric Forecast Viewer")

# Download the data (or load from cache)
with st.spinner("Downloading forecast data..."):
    data_file, forecast_date, forecast_hour = get_forecast_data()

st.success(f"Loaded forecast for {forecast_date} {forecast_hour}")


import xarray as xr
import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

ds = xr.open_dataset('forecast.grib',
                     engine='cfgrib',
                     filter_by_keys={'typeOfLevel':'isobaricInhPa'})

aerosol = ds['aerext1064']

pressure_levels = sorted(aerosol.isobaricInhPa.values)
valid_time = sorted(aerosol.valid_time.values)

selected_level = st.sidebar.select_slider(
    "Pressure Level (hPa or mb)",
    options=pressure_levels
)

selected_valid_time = st.sidebar.select_slider(
    "Valid Time (UTC)",
    options=valid_time,
    format_func= lambda x: x.astype('datetime64[s]').astype(datetime).strftime('%m/%d %H:%M')
)

df = ds[['valid_time', 'step']].to_dataframe()
value = df.loc[df['valid_time'] == selected_valid_time]
step_value = value.index[0]

selected_valid_time_formatted = selected_valid_time.astype('datetime64[s]').astype(datetime).strftime('%m/%d %H:%M')

st.sidebar.write(f"Selected Pressure Level: {selected_level} hPa")
st.sidebar.write(f"Selected Time: {selected_valid_time_formatted}")


fig = plt.figure(figsize=(12,8))
ax = plt.axes(projection=ccrs.PlateCarree())

aerosol.sel(
    step = step_value
).sel(
    isobaricInhPa = selected_level, method='nearest'
).plot(
    ax=ax, transform=ccrs.PlateCarree(), cmap='viridis', vmin=0, vmax=.001
)

ax.add_feature(cfeature.COASTLINE)
ax.add_feature(cfeature.BORDERS, linestyle=':')
ax.gridlines(draw_labels=True)

ax.set_title(f'Aerosol extinction at 1064nm at {selected_valid_time_formatted} at {selected_level}mb')

st.pyplot(fig)