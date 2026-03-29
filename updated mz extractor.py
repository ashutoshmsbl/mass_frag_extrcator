import streamlit as st
import pandas as pd
import io
import json
from datetime import datetime, timedelta

# ---------------- SAVE / LOAD RANGE PROFILES ----------------
def save_profile(name, ranges):
    try:
        with open("range_profiles.json", "r") as f:
            data = json.load(f)
    except:
        data = {}

    data[name] = {
        "ranges": ranges,
        "last_used": datetime.now().isoformat()
    }

    with open("range_profiles.json", "w") as f:
        json.dump(data, f)


def load_profiles():
    try:
        with open("range_profiles.json", "r") as f:
            data = json.load(f)
    except:
        return {}

    # 🔥 AUTO DELETE OLD PROFILES (>90 days)
    cleaned_data = {}
    now = datetime.now()

    for name, info in data.items():
        last_used = datetime.fromisoformat(info.get("last_used", now.isoformat()))
        if now - last_used <= timedelta(days=90):
            cleaned_data[name] = info

    # overwrite cleaned file
    with open("range_profiles.json", "w") as f:
        json.dump(cleaned_data, f)

    return cleaned_data


def update_last_used(profile_name, data):
    if profile_name in data:
        data[profile_name]["last_used"] = datetime.now().isoformat()
        with open("range_profiles.json", "w") as f:
            json.dump(data, f)


# Function to extract m/z data
def extract_mz_abundance(uploaded_file, compound, selected_sheets, mz_ranges):
    xl = pd.ExcelFile(uploaded_file)
    output_data = {}

    for sheet in selected_sheets:
        df = xl.parse(sheet)

        if 'm/z' not in df.columns or compound not in df.columns:
            st.warning(f"⚠️ Required columns not found in sheet: {sheet}")
            continue

        df_filtered = pd.DataFrame()

        for mz_min, mz_max in mz_ranges:
            df_temp = df[df['m/z'].between(mz_min, mz_max)][['m/z', compound]]
            df_temp = df_temp.rename(columns={compound: sheet})
            df_filtered = pd.concat([df_filtered, df_temp], ignore_index=True)

        if not df_filtered.empty:
            output_data[sheet] = df_filtered.set_index('m/z')

    if output_data:
        combined_df = pd.concat(output_data.values(), axis=1)
        combined_df.reset_index(inplace=True)
        return combined_df
    else:
        return None


# ---------------- UI ----------------
st.title("13C Mass Fragment Data Extraction Tool")

uploaded_file = st.file_uploader("Upload Excel File", type=['xlsx'])

profiles = load_profiles()

if uploaded_file:
    try:
        xl = pd.ExcelFile(uploaded_file)
        sheets = xl.sheet_names
        df_sample = xl.parse(sheets[0])

        compounds = [col for col in df_sample.columns if not (col.lower().startswith("m/z") or "unnamed" in col.lower())]

        compound = st.selectbox("Select Compound", compounds)

        # Sheet selection
        st.write("### Select Data Files")
        select_all = st.checkbox("Select All Sheets")
        selected_sheets = st.multiselect("Choose Sheets", sheets, default=sheets if select_all else [])

        # ---------------- PROFILE SELECTION ----------------
        st.write("### Load Saved Range Profile")
        profile_names = list(profiles.keys())
        selected_profile = st.selectbox("Select Profile", ["None"] + profile_names)

        mz_ranges = []

        if selected_profile != "None":
            mz_ranges = profiles[selected_profile]["ranges"]
            update_last_used(selected_profile, profiles)
            st.success(f"Loaded profile: {selected_profile}")

        # ---------------- MANUAL RANGE INPUT ----------------
        st.write("### Define Number of m/z Ranges")
        num_ranges = st.number_input("Number of ranges", min_value=1, max_value=50, value=1, step=1)

        manual_ranges = []

        st.write("### Enter m/z Ranges (format: 300-345)")
        for i in range(int(num_ranges)):
            range_input = st.text_input(f"Range {i+1}", key=f"range_{i}")
            if range_input:
                try:
                    parts = range_input.replace("–", "-").split("-")
                    mz_min, mz_max = int(parts[0]), int(parts[1])
                    if mz_min < mz_max:
                        manual_ranges.append((mz_min, mz_max))
                    else:
                        st.warning(f"Range {i+1}: Min should be less than Max")
                except:
                    st.warning(f"Range {i+1}: Invalid format")

        # Combine manual + profile ranges
        if manual_ranges:
            mz_ranges.extend(manual_ranges)

        # ---------------- SAVE PROFILE (MULTI-METABOLITE) ----------------
        st.write("### Save Range Profile (for multiple metabolites)")
        profile_name = st.text_input("Profile Name")

        if st.button("Save Profile"):
            if profile_name and mz_ranges:
                save_profile(profile_name, mz_ranges)
                st.success("Profile saved successfully!")
            else:
                st.error("Provide name and ranges")

        # ---------------- PROCESS ----------------
        if st.button("Process Data"):
            if not selected_sheets or not mz_ranges:
                st.error("⚠️ Please select sheets and enter valid ranges.")
            else:
                df_result = extract_mz_abundance(uploaded_file, compound, selected_sheets, mz_ranges)

                if df_result is not None:
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                        df_result.to_excel(writer, index=False)

                    output.seek(0)

                    st.download_button(
                        "⬇️ Download Excel",
                        output,
                        file_name=f"{compound}_data.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.warning("⚠️ No data found.")

    except Exception as e:
        st.error(f"⚠️ Error loading file: {e}")
