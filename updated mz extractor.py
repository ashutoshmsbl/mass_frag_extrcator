import streamlit as st
import pandas as pd
import io
import json
from datetime import datetime, timedelta

PROFILE_FILE = "range_profiles.json"

# ---------------- PROFILE FUNCTIONS ----------------
def load_profiles():
    try:
        with open(PROFILE_FILE, "r") as f:
            data = json.load(f)
    except:
        return {}

    now = datetime.now()
    cleaned = {}
    for name, info in data.items():
        last = datetime.fromisoformat(info.get("last_used", now.isoformat()))
        if now - last <= timedelta(days=90):
            cleaned[name] = info

    with open(PROFILE_FILE, "w") as f:
        json.dump(cleaned, f)

    return cleaned


def save_profiles(data):
    with open(PROFILE_FILE, "w") as f:
        json.dump(data, f)


def save_profile(name, ranges, profiles):
    profiles[name] = {
        "ranges": ranges,
        "last_used": datetime.now().isoformat()
    }
    save_profiles(profiles)


def delete_profile(name, profiles):
    if name in profiles:
        del profiles[name]
        save_profiles(profiles)


def clear_all_profiles():
    save_profiles({})


def update_last_used(name, profiles):
    if name in profiles:
        profiles[name]["last_used"] = datetime.now().isoformat()
        save_profiles(profiles)


# ---------------- CORE FUNCTION ----------------
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
    return None


# ---------------- UI ----------------
st.title("13C Mass Fragment Data Extraction Tool")

profiles = load_profiles()

uploaded_file = st.file_uploader("Upload Excel File", type=['xlsx'])

# -------- PROFILE EXPORT / IMPORT --------
st.write("### Profile Management")

# Export profiles
if profiles:
    profile_bytes = json.dumps(profiles, indent=2).encode("utf-8")
    st.download_button(
        "⬇️ Download Profiles",
        profile_bytes,
        file_name="range_profiles_backup.json",
        mime="application/json"
    )

# Import profiles
uploaded_profile_file = st.file_uploader("Upload Profile File (.json)", type=["json"], key="profile_upload")

if uploaded_profile_file:
    try:
        imported_profiles = json.load(uploaded_profile_file)
        profiles.update(imported_profiles)
        save_profiles(profiles)
        st.success("Profiles imported successfully!")
        st.rerun()
    except:
        st.error("Invalid profile file")

if uploaded_file:
    xl = pd.ExcelFile(uploaded_file)
    sheets = xl.sheet_names
    df_sample = xl.parse(sheets[0])

    compounds = [col for col in df_sample.columns if not (col.lower().startswith("m/z") or "unnamed" in col.lower())]

    compound = st.selectbox("Select Compound", compounds)

    # Sheet selection
    st.write("### Select Data Files")
    select_all = st.checkbox("Select All Sheets")
    selected_sheets = st.multiselect("Choose Sheets", sheets, default=sheets if select_all else [])

    # -------- PROFILE LOAD --------
    st.write("### Load Saved Profile")
    profile_names = list(profiles.keys())
    selected_profile = st.selectbox("Select Profile", ["None"] + profile_names)

    mz_ranges = []
    use_manual = True

    if selected_profile != "None":
        mz_ranges = profiles[selected_profile]["ranges"]
        update_last_used(selected_profile, profiles)
        use_manual = False

        st.write("#### Loaded Ranges (Editable)")
        for i, r in enumerate(mz_ranges):
            col1, col2 = st.columns([4,1])
            new_val = col1.text_input(f"Edit Range {i+1}", f"{r[0]}-{r[1]}", key=f"edit_{i}")
            if col2.button("❌", key=f"del_{i}"):
                mz_ranges.pop(i)
                st.rerun()
            else:
                try:
                    parts = new_val.replace("–","-").split("-")
                    mz_ranges[i] = (int(parts[0]), int(parts[1]))
                except:
                    pass

        if st.button("💾 Save Updated Profile"):
            save_profile(selected_profile, mz_ranges, profiles)
            st.success("Profile updated successfully")

        if st.button("Delete This Profile"):
            delete_profile(selected_profile, profiles)
            st.success("Profile deleted")
            st.rerun()

    if st.button("⚠️ Clear All Profiles"):
        clear_all_profiles()
        st.success("All profiles deleted")
        st.rerun()

    # -------- MANUAL INPUT --------
    if use_manual:
        st.write("### Define Number of m/z Ranges")
        num_ranges = st.number_input("Number of ranges", 1, 50, 1)

        for i in range(int(num_ranges)):
            val = st.text_input(f"Range {i+1}", key=f"range_{i}")
            if val:
                try:
                    p = val.replace("–","-").split("-")
                    mz_ranges.append((int(p[0]), int(p[1])))
                except:
                    st.warning(f"Invalid format in Range {i+1}")

    # Save new profile
    st.write("### Save Profile")
    pname = st.text_input("Profile Name")

    if st.button("Save Profile"):
        if pname and mz_ranges:
            save_profile(pname, mz_ranges, profiles)
            st.success("Profile saved")
        else:
            st.error("Provide name and ranges")

    # -------- PROCESS --------
    if st.button("Process Data"):
        if not selected_sheets or not mz_ranges:
            st.error("Select sheets and ranges")
        else:
            df_result = extract_mz_abundance(uploaded_file, compound, selected_sheets, mz_ranges)

            if df_result is not None:
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                    df_result.to_excel(writer, index=False)

                output.seek(0)

                st.download_button("⬇️ Download Excel", output, f"{compound}.xlsx")
            else:
                st.warning("No data found")
