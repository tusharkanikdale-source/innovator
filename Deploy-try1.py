# app.py
import streamlit as st
from datetime import datetime
try:
    # Python 3.9+ (recommended)
    from zoneinfo import ZoneInfo
    have_zoneinfo = True
except ImportError:
    # Fallback if running on older Python; recommend upgrading
    have_zoneinfo = False

st.set_page_config(page_title="Hello & World Clocks", page_icon="🕒", layout="centered")

st.title("👋 Hello!")
st.write("Click the button to see the current date and time in the USA and India.")

# Configure timezones
if have_zoneinfo:
    us_tz = ZoneInfo("US/Eastern")     # Change to "US/Pacific", "US/Central", etc., if desired
    india_tz = ZoneInfo("Asia/Kolkata")
else:
    st.warning("Your Python version lacks `zoneinfo`. Times shown will be system local only.")
    us_tz = None
    india_tz = None

if st.button("Show Current Time"):
    now_utc = datetime.utcnow()

    if have_zoneinfo:
        now_us = now_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(us_tz)
        now_in = now_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(india_tz)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🇺🇸 USA (US/Eastern)")
            st.write(now_us.strftime("%A, %d %B %Y"))
            st.success(now_us.strftime("%I:%M:%S %p %Z"))
        with col2:
            st.subheader("🇮🇳 India (Asia/Kolkata)")
            st.write(now_in.strftime("%A, %d %B %Y"))
            st.success(now_in.strftime("%I:%M:%S %p %Z"))
    else:
        # Minimal fallback: show system local time
        local_now = datetime.now()
        st.info("Showing system local time (upgrade to Python 3.9+ for timezones).")
        st.write(local_now.strftime("%A, %d %B %Y • %I:%M:%S %p"))