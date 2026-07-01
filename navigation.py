import streamlit as st

PATIENTS_VISIBLE = 10


def patient_navigation(patient_ids):

    total_patients = len(patient_ids)

    if "selected_patient" not in st.session_state:
        st.session_state.selected_patient = patient_ids[0]

    if "current_start" not in st.session_state:
        st.session_state.current_start = patient_ids[0]

    start_index = patient_ids.index(st.session_state.current_start)

    visible_patients = patient_ids[
        start_index : start_index + PATIENTS_VISIBLE
    ]

    cols = st.columns(len(visible_patients) + 4)

    # <<
    with cols[0]:
        if st.button("<<", use_container_width=True):

            st.session_state.current_start = patient_ids[0]
            st.session_state.selected_patient = patient_ids[0]
            st.rerun()

    # <
    with cols[1]:
        if st.button("<", use_container_width=True):

            current_idx = patient_ids.index(st.session_state.current_start)

            if current_idx > 0:

                st.session_state.current_start = patient_ids[current_idx - 1]
                st.session_state.selected_patient = patient_ids[current_idx - 1]
                st.rerun()

    # Patient Buttons
    for i, patient in enumerate(visible_patients):

        label = patient

        if patient == st.session_state.selected_patient:
            label = f"🟦 {patient}"

        with cols[i + 2]:

            if st.button(
                label,
                key=f"patient_{patient}",
                use_container_width=True
            ):

                st.session_state.selected_patient = patient
                st.session_state.current_start = patient
                st.rerun()

    # >
    with cols[-2]:
        if st.button(">", use_container_width=True):

            current_idx = patient_ids.index(st.session_state.current_start)

            if current_idx < total_patients - 1:

                st.session_state.current_start = patient_ids[current_idx + 1]
                st.session_state.selected_patient = patient_ids[current_idx + 1]
                st.rerun()

    # >>
    with cols[-1]:
        if st.button(">>", use_container_width=True):

            last_start = max(0, total_patients - PATIENTS_VISIBLE)

            st.session_state.current_start = patient_ids[last_start]
            st.session_state.selected_patient = patient_ids[last_start]
            st.rerun()

    return st.session_state.selected_patient