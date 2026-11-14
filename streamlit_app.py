from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Screen Scale", page_icon="⚖️", layout="centered")

st.title("⚖️ Screen Scale")
st.caption("Uses your screen's touch-pressure sensor as a scale, displaying to 0.01 g.")

components.html(Path(__file__).with_name("scale.html").read_text(), height=760, scrolling=False)

with st.expander("How to use it", expanded=True):
    st.markdown(
        """
1. **Open on a supported device:** an iPhone with 3D Touch (6s, 7, 8, X, XS) in **Safari**,
   or a Mac with a Force Touch trackpad in **Safari** (press on the pad with the item resting on your finger).
2. **Use a conductive carrier.** Touchscreens only register conductive objects. Place a metal
   spoon or a coin on the pad and keep it there.
3. **Calibrate:** tap **CALIBRATE**, capture zero with only the carrier, then add a known
   weight (a US nickel is exactly 5.000 g) and capture it.
4. Remove the reference weight, tap **TARE**, and place your item on the carrier.
5. Wait for the **Stable** light before reading.

Calibration is saved in your browser. Re-calibrate if you move to a different spot on the screen.
"""
    )

with st.expander("Accuracy: please read"):
    st.markdown(
        """
- The display shows **0.01 g resolution**, but a phone screen is not a lab balance. Expect real-world
  error of roughly **±0.5–2 g**, more at the extremes of the range. Use a real scale for anything where
  precision matters (medication, chemistry, postage, trade).
- The pressure sensor is non-linear and sensitive to where the item sits, temperature, and phone tilt.
  Calibrate with a reference close to the weight you're measuring, and keep the phone flat on a table.
- The 3D Touch sensor saturates at a few hundred grams. Don't put heavy objects on your screen.
- Most phones since 2019 (iPhone XR/11 and newer, nearly all Android) **don't measure force at all**.
  On those, the app will say so; use *Simulation mode* to try the interface.
"""
    )
